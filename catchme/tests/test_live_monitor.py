import queue
import time

import pytest

from catchme.sources.apps import gallery, monitoring_settings, recent, set_mode, set_monitoring
from catchme.sources.live import LiveMonitor, document_path, save_events, snapshot_events
from catchme.sources.store import ActivityStore
from catchme.sources.wechat import attachment_roots, file_rows


def configured(tmp_path, app_id="wechat"):
    store = ActivityStore(tmp_path / "activity.db")
    set_monitoring(store, app_id, True)
    set_mode(store, app_id, "full", True)
    with store.connect() as db:
        settings = monitoring_settings(db)
    return store, settings


def snap(**extra):
    return {
        "ts": time.time(),
        "app": "微信",
        "bundle_id": "com.tencent.xinWeChat",
        "pid": 42,
        "window": "测试会话",
        "text": "收到的测试内容",
        "field": "input-1",
        "draft": "",
        **extra,
    }


def test_schema_upgrade_preserves_choices(tmp_path):
    import sqlite3

    path = tmp_path / "activity.db"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE app_preferences(id TEXT PRIMARY KEY, enabled INTEGER NOT NULL)")
        db.execute("INSERT INTO app_preferences VALUES('wechat',1)")
        db.execute("PRAGMA user_version=2")
    store = ActivityStore(path)
    with store.connect() as db:
        settings = monitoring_settings(db)
        assert db.execute("PRAGMA user_version").fetchone()[0] == 4
        assert db.execute("SELECT COUNT(*) FROM source_locations").fetchone()[0] == 0
    assert settings["wechat"] == {"enabled": True, "mode": "basic", "consented": None}


def test_full_mode_requires_consent_and_supported_app(tmp_path):
    store = ActivityStore(tmp_path / "activity.db")
    for mode, app in [("full", "wechat"), ("invalid", "wechat")]:
        with pytest.raises(ValueError):
            set_mode(store, app, mode)
    with pytest.raises(ValueError):
        set_mode(store, "chrome", "full", True)
    set_mode(store, "wechat", "full", True)
    app = next(a for a in gallery(store) if a["id"] == "wechat")
    assert app["mode"] == "full" and not app["enabled"]


def test_window_content_and_drafts_are_not_labelled_sent(tmp_path):
    _, settings = configured(tmp_path)
    previous = {}
    first = snapshot_events(snap(), previous, settings, [])
    assert [e[1] for e in first] == ["window_context", "visible_content"]
    assert snapshot_events(snap(), previous, settings, []) == []
    changed = snapshot_events(snap(draft="还未发送的草稿"), previous, settings, [])
    assert changed[0][1] == "input_changed"
    assert "不代表已经发送" in changed[0][3]["meaning"]
    assert all(e[1] != "message_sent" for e in changed)


def test_secure_field_and_unselected_apps_do_not_emit_content(tmp_path):
    _, settings = configured(tmp_path)
    assert snapshot_events(snap(secure=True, draft="private"), {}, settings, []) == []
    assert snapshot_events(snap(app="Safari", bundle_id="com.apple.Safari"), {}, settings, []) == []
    settings["wechat"]["enabled"] = False
    assert snapshot_events(snap(), {}, settings, []) == []


def test_wechat_file_open_requires_exact_document_path(tmp_path):
    _, settings = configured(tmp_path)
    settings["wechat"]["mode"] = "basic"
    root = tmp_path / "wechat-files"
    root.mkdir()
    file = root / "季度报表.xlsx"
    file.write_text("fixture")
    evidence = snap(app="Microsoft Excel", bundle_id="com.microsoft.Excel", document=file.as_uri())
    previous = {}
    events = snapshot_events(evidence, previous, settings, [str(root)])
    assert events[0][1] == "document_opened"
    assert events[0][3]["viewing_app"] == "Microsoft Excel"
    assert snapshot_events(evidence, previous, settings, [str(root)]) == []
    assert (
        snapshot_events(
            {**evidence, "document": str(tmp_path / "季度报表.xlsx")}, {}, settings, [str(root)]
        )
        == []
    )
    assert document_path("file://remotehost/share/file.xlsx") == ""


def test_recheck_drops_content_after_pause_or_downgrade(tmp_path):
    store, settings = configured(tmp_path)
    events = snapshot_events(snap(), {}, settings, [])
    set_monitoring(store, "wechat", False)
    assert save_events(store, events, time.time(), settings) == 0
    set_monitoring(store, "wechat", True)
    set_mode(store, "wechat", "basic")
    assert save_events(store, events, time.time(), settings) == 0
    set_mode(store, "wechat", "full", True)
    assert save_events(store, events, time.time(), settings) == 0  # older consent generation


def test_live_events_are_redacted_searchable_and_isolated(tmp_path):
    store, settings = configured(tmp_path)
    events = snapshot_events(snap(text="文件预算 password=secret-value"), {}, settings, [])
    assert save_events(store, events, time.time(), settings) == 2
    found = recent(store, "wechat", kind="content", query="预算")["events"]
    assert len(found) == 1 and "secret-value" not in found[0]["payload"]["text"]
    assert recent(store, "wechat", kind="files")["events"] == []
    assert recent(store, "excel")["events"] == []
    assert recent(store, "wechat", query="%")["events"] == []


def test_wechat_attachments_incremental_and_not_open_events(tmp_path):
    root = (
        tmp_path
        / "Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/account/msg/file"
    )
    folder = root / "2026-09"
    folder.mkdir(parents=True)
    file = folder / "budget.xlsx"
    file.write_bytes(b"fixture")
    assert attachment_roots(tmp_path) == [root]
    source, cursor = {"paths": [str(root)]}, {}
    result = file_rows(source, cursor)
    assert len(result) == 1 and result[0][3] == "attachment_available"
    assert "text" not in result[0][5]
    assert file_rows(source, cursor) == []
    file.write_bytes(b"changed fixture")
    assert len(file_rows(source, cursor)) == 1
    (folder / "alias").symlink_to(file)
    assert file_rows(source, cursor) == []


def test_mode_api_and_filters(client):
    assert client.post("/api/library/apps/wechat/mode", json={"mode": "full"}).status_code == 400
    assert client.post(
        "/api/library/apps/wechat/mode", json={"mode": "full", "consent": True}
    ).json["ok"]
    assert client.get("/api/library/apps").json["apps"][3]["mode"] == "full"
    assert client.get("/api/library/apps/wechat/activity?kind=bad").status_code == 400
    assert client.post("/api/library/apps/wechat/mode", json={"mode": "basic"}).json["ok"]


def test_tick_actions_only_for_selected_pid_and_current_consent(tmp_path):
    store, settings = configured(tmp_path)

    class Observer:
        actions = queue.Queue()
        input_status = "listening"

        def permissions(self):
            return {"platform": "macos", "accessibility": True}

        def start_actions(self):
            pass

        def stop_actions(self):
            pass

        def poll(self, settings):
            return snap()

    observer = Observer()
    observer.actions.put({"pid": 42, "ts": time.time(), "action": "Enter"})
    observer.actions.put({"pid": 99, "ts": time.time(), "action": "other app"})
    observer.actions.put({"pid": 42, "ts": 1, "action": "stale"})
    monitor = LiveMonitor(store, observer)
    monitor.tick()
    actions = [e for e in recent(store, "wechat")["events"] if e["kind"] == "app_action"]
    assert len(actions) == 1 and actions[0]["title"] == "Enter"
    assert "不等于消息发送成功" in actions[0]["payload"]["meaning"]


def test_native_adapter_skips_secure_fields_and_unselected_apps(tmp_path, monkeypatch):
    import sys
    import types

    from catchme.sources.live import MacObserver

    _, settings = configured(tmp_path)
    focused = {"AXRole": "AXTextField", "AXValue": "draft", "AXSubrole": "AXTextField"}
    message = {"AXRole": "AXStaticText", "AXValue": "fixture message"}
    secret = {"AXRole": "AXTextField", "AXSubrole": "AXSecureTextField", "AXValue": "must not read"}
    window = {"AXTitle": "fixture window", "AXChildren": [message, focused, secret]}
    root = {"AXFocusedWindow": window, "AXFocusedUIElement": focused}
    reads = []

    class Front:
        def processIdentifier(self):
            return 42

        def localizedName(self):
            return "微信"

        def bundleIdentifier(self):
            return "com.tencent.xinWeChat"

    workspace = types.SimpleNamespace(frontmostApplication=lambda: Front())
    monkeypatch.setitem(
        sys.modules,
        "AppKit",
        types.SimpleNamespace(NSWorkspace=types.SimpleNamespace(sharedWorkspace=lambda: workspace)),
    )
    monkeypatch.setitem(sys.modules, "CoreFoundation", types.SimpleNamespace(CFHash=id))

    def read(node, key, unused):
        reads.append((id(node), key))
        return 0, node.get(key)

    monkeypatch.setitem(
        sys.modules,
        "ApplicationServices",
        types.SimpleNamespace(
            AXUIElementCopyAttributeValue=read,
            AXUIElementCreateApplication=lambda pid: root,
            AXUIElementSetMessagingTimeout=lambda node, timeout: None,
        ),
    )
    observer = MacObserver()
    monkeypatch.setattr(
        observer, "permissions", lambda: {"accessibility": True, "platform": "macos"}
    )
    result = observer.poll(settings)
    assert result["text"] == "fixture window\nfixture message"
    assert result["draft"] == "draft"
    assert (id(secret), "AXValue") not in reads
    reads.clear()
    settings["wechat"]["enabled"] = False
    assert "text" not in observer.poll(settings)
    assert reads == [] and observer.allowed_pid is None
    settings["wechat"]["enabled"] = True
    focused["AXSubrole"] = "AXSecureTextField"
    result = observer.poll(settings)
    assert result["secure"] and "text" not in result and "draft" not in result
