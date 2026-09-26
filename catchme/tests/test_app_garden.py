import time

from catchme.sources.apps import gallery, recent, set_monitoring
from catchme.sources.collect import collect
from catchme.sources.store import ActivityStore


def seed(tmp_path):
    store = ActivityStore(tmp_path / "activity.db")
    with store.connect() as db:
        db.execute(
            "INSERT INTO sources(id,name,category,reader,paths,enabled,status,detail) VALUES('system.foreground','Foreground','system','foreground','[]',1,'available','')"
        )
        for sid in ("app.com.microsoft.Excel", "editor.cursor", "cursor.conversations"):
            db.execute(
                "INSERT INTO sources(id,name,category,reader,paths,enabled,status,detail) VALUES(?,?,?,?,?,1,?,?)",
                (sid, sid, "office", "office", "[]", "available", ""),
            )
    return store


def test_app_toggle_only_changes_its_own_sources(tmp_path):
    store = seed(tmp_path)
    set_monitoring(store, "cursor", False)
    states = {s["id"]: s["enabled"] for s in store.sources()}
    assert not states["editor.cursor"] and not states["cursor.conversations"]
    assert states["app.com.microsoft.Excel"] and states["system.foreground"]
    assert not next(a for a in gallery(store) if a["id"] == "cursor")["enabled"]


def test_pause_excludes_foreground_but_other_app_can_collect(tmp_path, monkeypatch):
    from catchme.sources.collect import READERS

    store = seed(tmp_path)
    set_monitoring(store, "wechat", False)
    monkeypatch.setitem(
        READERS,
        "foreground",
        lambda s, c: [
            (
                "one",
                time.time(),
                "微信",
                "foreground_sample",
                "微信",
                {"bundle_id": "com.tencent.xinWeChat"},
            )
        ],
    )
    assert collect(store)["inserted"] == 0
    set_monitoring(store, "wechat", True)
    assert collect(store)["inserted"] == 1
    set_monitoring(store, "wechat", False)
    assert len(recent(store, "wechat")["events"]) == 1
    assert collect(store)["inserted"] == 0


def test_app_detail_groups_sources_without_other_app_records(tmp_path):
    store = seed(tmp_path)
    with store.connect() as db:
        for i, sid, app in [
            (1, "editor.cursor", "Cursor"),
            (2, "cursor.conversations", "Cursor conversations"),
            (3, "app.com.microsoft.Excel", "Microsoft Excel"),
        ]:
            db.execute(
                "INSERT INTO activity(source,external_id,ts,observed,app,category,kind,title,payload) VALUES(?,?,?,?,?,?,?,?,?)",
                (sid, str(i), i, i, app, "office", "document_recent", "doc", "{}"),
            )
    assert [e["source"] for e in recent(store, "cursor")["events"]] == [
        "cursor.conversations",
        "editor.cursor",
    ]
    assert len(recent(store, "excel")["events"]) == 1


def test_chronological_pagination_not_ingestion_order(tmp_path):
    store = seed(tmp_path)
    with store.connect() as db:
        for i in range(35):
            db.execute(
                "INSERT INTO activity(source,external_id,ts,observed,app,category,kind,title,payload) VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    "app.com.microsoft.Excel",
                    str(i),
                    100 - i,
                    100,
                    "Excel",
                    "office",
                    "document_recent",
                    str(i),
                    "{}",
                ),
            )
    page = recent(store, "excel")
    tail = recent(store, "excel", before=page["next"])
    assert len(page["events"]) == 30 and len(tail["events"]) == 5
    assert page["events"][0]["ts"] == 100
    assert page["events"][-1]["ts"] > tail["events"][0]["ts"]


def test_app_api_persists_preference(client, tmp_path):
    seed(tmp_path)
    assert len(client.get("/api/library/apps").json["apps"]) >= 6
    assert client.post("/api/library/apps/wechat/monitor", json={"enabled": True}).json["ok"]
    apps = client.get("/api/library/apps").json["apps"]
    assert next(a for a in apps if a["id"] == "wechat")["enabled"]
    assert (
        client.post("/api/library/apps/wechat/monitor", json={"enabled": "yes"}).status_code == 400
    )
    assert client.get("/api/library/apps/unknown/activity").status_code == 400
    assert client.get("/api/library/apps/excel/activity?before=bad").status_code == 400


def test_disabled_source_not_reenabled_by_refresh_scan(tmp_path, monkeypatch):
    from catchme.sources.catalog import scan

    store = seed(tmp_path)
    set_monitoring(store, "excel", False)
    monkeypatch.setattr("catchme.sources.catalog.applications", lambda h: [])
    scan(store, home=tmp_path)
    assert not next(a for a in gallery(store) if a["id"] == "excel")["enabled"]
