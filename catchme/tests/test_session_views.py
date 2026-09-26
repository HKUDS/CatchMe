import json
import sqlite3
from pathlib import Path

import pytest

from catchme.sources.app_views import content_page, presentation
from catchme.sources.apps import definition, monitoring_settings, set_monitoring
from catchme.sources.catalog import scan
from catchme.sources.collect import jsonl_rows, read_source
from catchme.sources.conversations import list_sessions, transcript_page
from catchme.sources.locations import (
    chrome_files,
    configured,
    editor_files,
    save_locations,
    session_roots,
)
from catchme.sources.store import ActivityStore


def record(store, source="claude.sessions", ts=1, kind="conversation", title="hello", **payload):
    with store.connect() as db:
        ident = db.execute("SELECT COALESCE(MAX(id),0)+1 FROM activity").fetchone()[0]
        db.execute(
            "INSERT INTO activity(source,external_id,ts,observed,app,category,kind,title,payload) "
            "VALUES(?,?,?,?,?,?,?,?,?)",
            (source, str(ident), ts, ts, source, "other", kind, title, json.dumps(payload)),
        )


def test_session_pagination_search_and_app_isolation(tmp_path):
    store = ActivityStore(tmp_path / "activity.db")
    for i in range(35):
        record(store, session_id=f"s{i:02}", ts=1, role="user", text="first")
    record(store, session_id="s00", ts=2, role="assistant", text="uniquely searchable")
    record(store, source="codex.sessions", session_id="s00", ts=3, text="other app")
    page = list_sessions(store, "claude")
    tail = list_sessions(store, "claude", before=page["next"])
    assert len(page["sessions"]) == 30 and len(tail["sessions"]) == 5
    assert len({s["session_id"] for s in page["sessions"] + tail["sessions"]}) == 35
    assert tail["next"] is None
    found = list_sessions(store, "claude", query="uniquely searchable")["sessions"]
    assert len(found) == 1 and found[0]["messages"] == 2
    assert transcript_page(store, "claude", "s00")["total"] == 2
    assert transcript_page(store, "codex", "s00")["total"] == 1


def test_transcript_order_and_long_message_page_budget(tmp_path, monkeypatch):
    import catchme.sources.conversations as conversations

    store = ActivityStore(tmp_path / "activity.db")
    # Backfilled ingestion order differs from conversation chronology.
    for ts in [4, 2, 1, 3, 3]:
        record(store, session_id="s", ts=ts, role="user", title=f"message {ts}", text="x" * 20000)
    assert list_sessions(store, "claude")["sessions"][0]["title"] == "message 1"
    monkeypatch.setattr(conversations, "TRANSCRIPT_PAGE_BYTES", 25000)
    events, after = [], None
    for _ in range(6):
        page = transcript_page(store, "claude", "s", after=after)
        assert len(page["events"]) == 1
        events.extend(page["events"])
        after = page["next"]
        if not after:
            break
    assert [e["ts"] for e in events] == [1, 2, 3, 3, 4]
    assert len({e["id"] for e in events}) == 5
    assert all(len(e["payload"]["text"]) == 20000 for e in events)
    monkeypatch.setattr(conversations, "TRANSCRIPT_PAGE_BYTES", 100)
    assert len(transcript_page(store, "claude", "s")["events"]) == 1


def test_jsonl_long_message_explicit_file_and_overlapping_roots(tmp_path):
    path = tmp_path / "s.jsonl"
    path.write_text(
        json.dumps({"type": "user", "sessionId": "s", "message": {"content": "文" * 20000}}) + "\n"
    )
    rows = jsonl_rows({"reader": "claude", "paths": [str(tmp_path), str(path)]}, {})
    assert len(rows) == 1 and rows[0][5]["text"] == "文" * 20000
    assert not rows[0][5]["truncated"]


def test_unreadable_jsonl_does_not_discard_other_checkpoints(tmp_path, monkeypatch):
    for name in ("good", "locked"):
        (tmp_path / f"{name}.jsonl").write_text(
            json.dumps({"type": "user", "message": {"content": name}}) + "\n"
        )
    original = Path.open

    def guarded(path, *args, **kwargs):
        if path.name == "locked.jsonl":
            raise PermissionError()
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded)
    source, cursor = {"reader": "claude", "paths": [str(tmp_path)]}, {}
    rows, failures = read_source(source, cursor)
    assert len(rows) == 1 and failures == 1
    assert str(tmp_path / "good.jsonl") in cursor
    assert str(tmp_path / "locked.jsonl") not in cursor
    assert read_source(source, cursor) == ([], 1)


def test_document_dedup_precedes_pagination_and_bookmarks_keep_profiles(tmp_path):
    store = ActivityStore(tmp_path / "activity.db")
    for ts, filename in [(1, "a"), (2, "b"), (3, "c"), (4, "a")]:
        record(
            store, source="app.com.microsoft.Excel", kind="document_recent", ts=ts, file=filename
        )
    page = content_page(store, "excel", "documents", limit=2)
    tail = content_page(store, "excel", "documents", before=page["next"], limit=2)
    assert [e["payload"]["file"] for e in page["events"] + tail["events"]] == ["a", "c", "b"]
    assert page["events"][0]["observations"] == 2 and tail["next"] is None
    for profile in ("Default", "Profile 1"):
        record(
            store,
            source="chrome.bookmarks",
            kind="bookmark",
            url="https://example.test",
            folder="Work",
            profile=profile,
        )
    assert content_page(store, "chrome", "bookmarks")["total"] == 2


@pytest.mark.parametrize(
    "app_id,tabs",
    [
        ("powerpoint", ["documents", "usage"]),
        ("wechat", ["attachments", "opened", "usage"]),
        ("chrome", ["history", "bookmarks", "downloads", "usage"]),
        ("cursor", ["workspaces", "topics", "usage"]),
        ("capcut", ["projects", "usage"]),
    ],
)
def test_app_specific_views(app_id, tabs):
    assert [t["id"] for t in presentation(definition(app_id))["tabs"]] == tabs
    assert presentation(definition("claude"))["type"] == "sessions"


def test_locations_portable_profiles_and_archives(tmp_path):
    assert session_roots(tmp_path, "codex", {"CODEX_HOME": "/fixture/codex"})[:2] == [
        "/fixture/codex/sessions",
        "/fixture/codex/archived_sessions",
    ]
    assert (
        session_roots(tmp_path, "claude", {"CLAUDE_CONFIG_DIR": "/fixture/cc"})[0]
        == "/fixture/cc/projects"
    )
    root = tmp_path / "browser"
    (root / "Profile 7").mkdir(parents=True)
    (root / "Local State").write_text(
        json.dumps({"profile": {"info_cache": {"Work": {}, "../escape": {}}}})
    )
    paths = chrome_files(tmp_path, environ={"CHROME_USER_DATA_DIR": str(root)})
    assert str(root / "Default/History") in paths
    assert str(root / "Profile 7/History") in paths
    assert str(root / "Work/History") in paths
    assert not any("escape" in p for p in paths)
    profile = tmp_path / "xdg/Code/User/profiles/work/globalStorage"
    profile.mkdir(parents=True)
    result = editor_files(
        tmp_path, "Code", platform="linux", environ={"XDG_CONFIG_HOME": str(tmp_path / "xdg")}
    )
    assert str(profile / "state.vscdb") in result["history"]
    assert any("Code - Insiders" in p for p in result["history"])
    win = chrome_files(tmp_path, platform="win32", environ={"LOCALAPPDATA": str(tmp_path / "win")})
    assert str(tmp_path / "win/Google/Chrome/User Data/Default/History") in win


def test_custom_missing_source_location_persists_without_enabling(tmp_path, monkeypatch):
    monkeypatch.setattr("catchme.sources.catalog.applications", lambda home: [])
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    monkeypatch.delenv("CODEX_HOME", raising=False)
    monkeypatch.delenv("CHROME_USER_DATA_DIR", raising=False)
    store = ActivityStore(tmp_path / "activity.db")
    scan(store, home=tmp_path)
    set_monitoring(store, "claude", False)
    path = tmp_path / "relocated.jsonl"
    path.write_text("{}\n")
    save_locations(store, "claude", {"claude.sessions": [str(path)]})
    scan(store, home=tmp_path)
    source = next(s for s in store.sources() if s["id"] == "claude.sessions")
    assert source["status"] == "available" and not source["enabled"]
    assert str(path) in source["paths"]
    reopened = ActivityStore(store.path)
    assert configured(reopened, "claude")[0]["custom"] == [str(path)]
    with reopened.connect() as db:
        assert not monitoring_settings(db)["claude"]["enabled"]
    for invalid in [
        {"codex.sessions": [str(path)]},
        {"claude.sessions": ["relative"]},
        {"claude.sessions": ["/x"] * 21},
    ]:
        with pytest.raises(ValueError):
            save_locations(store, "claude", invalid)


def test_chrome_multiple_profiles_partial_read_and_download_updates(tmp_path):
    good, bad = tmp_path / "Default", tmp_path / "Profile 1"
    good.mkdir()
    bad.mkdir()
    bookmark = good / "Bookmarks"
    bookmark.write_text(
        json.dumps(
            {
                "roots": {
                    "bar": {
                        "type": "folder",
                        "name": "Work",
                        "children": [
                            {
                                "type": "url",
                                "id": "1",
                                "name": "Docs",
                                "url": "https://example.test",
                            }
                        ],
                    }
                }
            }
        )
    )
    (bad / "Bookmarks").write_text("corrupt")
    cursor = {}
    rows, failures = read_source(
        {"reader": "chrome_bookmarks", "paths": [str(bad / "Bookmarks"), str(bookmark)]}, cursor
    )
    assert failures == 1 and rows[0][5]["profile"] == "Default"
    assert rows[0][5]["folder"] == "Work" and str(bookmark) in cursor
    history = good / "History"
    with sqlite3.connect(history) as db:
        db.executescript(
            "CREATE TABLE downloads(id INTEGER,start_time REAL,target_path TEXT,state INTEGER,received_bytes INTEGER); CREATE TABLE downloads_url_chains(id INTEGER,chain_index INTEGER,url TEXT);"
        )
        db.execute("INSERT INTO downloads VALUES(1,11644473601000000,'/fixture/a.pdf',0,12)")
        db.execute("INSERT INTO downloads_url_chains VALUES(1,0,'https://example.test/a.pdf')")
    source, cursor = {"reader": "chrome_downloads", "paths": [str(history)]}, {}
    first, failures = read_source(source, cursor)
    assert not failures and first[0][1] == 1 and first[0][5]["size"] == 12
    assert read_source(source, cursor)[0] == []
    with sqlite3.connect(history) as db:
        db.execute("UPDATE downloads SET state=1,received_bytes=24")
    updated, _ = read_source(source, cursor)
    assert updated[0][5]["state"] == 1 and updated[0][0] != first[0][0]


def test_session_and_catalog_http_contract(client, tmp_path):
    store = ActivityStore(tmp_path / "activity.db")
    record(store, session_id="http", role="user", text="hello")
    sessions = client.get("/api/library/apps/claude/sessions").json
    assert sessions["sessions"][0]["session_id"] == "http"
    assert client.get("/api/library/apps/claude/transcript?session=http").json["total"] == 1
    assert client.get("/api/library/apps/codex/transcript?session=http").status_code == 400
    assert (
        client.get("/api/library/apps/claude/transcript?session=http&after=invalid").status_code
        == 400
    )
    catalog = client.get("/api/library/catalog").json
    assert len(catalog["apps"]) == 13 and "discovered" in catalog
