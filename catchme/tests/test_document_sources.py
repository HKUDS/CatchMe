import json
import plistlib
import sqlite3
from datetime import UTC, datetime

from catchme.sources.documents import (
    capcut_rows,
    cursor_conversations,
    editor_rows,
    office_rows,
    recent_document_rows,
)


def source(path, name="Excel"):
    return {"paths": [str(path)], "name": name}


def test_office_usage_dates_and_deduplication(tmp_path):
    path = tmp_path / "bookmarks.plist"
    when = datetime(2026, 9, 17, 1, 0)
    data = {
        "file:///tmp/report%20one.xlsx": {
            "kLastUsedDateKey": when,
            "kBookmarkDataKey": b"opaque credential bytes",
        }
    }
    path.write_bytes(plistlib.dumps(data))
    cursor = {}
    rows = office_rows(source(path), cursor)
    assert rows[0][1] == when.replace(tzinfo=UTC).timestamp()
    assert rows[0][4] == "report one.xlsx"
    assert "opaque" not in str(rows)
    assert office_rows(source(path), cursor) == []
    data["file:///tmp/report%20one.xlsx"]["kLastUsedDateKey"] = datetime(2026, 9, 18)
    path.write_bytes(plistlib.dumps(data))
    assert len(office_rows(source(path), cursor)) == 1


def test_unknown_office_time_uses_observation_time_without_replaying(tmp_path):
    path = tmp_path / "bookmarks.plist"
    path.write_bytes(plistlib.dumps({"file:///tmp/report.xlsx": {}}))
    cursor = {}
    assert office_rows(source(path), cursor)[0][-1]["last_used"] is None
    assert office_rows(source(path), cursor) == []


def test_editor_only_reads_workspace_index_in_wal(tmp_path):
    path = tmp_path / "state.vscdb"
    db = sqlite3.connect(path)
    db.executescript("PRAGMA journal_mode=WAL; CREATE TABLE ItemTable(key TEXT,value TEXT);")
    db.execute(
        "INSERT INTO ItemTable VALUES(?,?)",
        (
            "history.recentlyOpenedPathsList",
            json.dumps(
                {
                    "entries": [
                        {"folderUri": "file:///tmp/project"},
                        {"workspace": {"configPath": "file:///tmp/app.code-workspace"}},
                        {"fileUri": "file:///tmp/readme.md"},
                    ]
                }
            ),
        ),
    )
    db.execute(
        "INSERT INTO ItemTable VALUES(?,?)",
        ("terminal.history.entries.commands", "SECRET COMMANDS"),
    )
    db.commit()
    cursor = {}
    rows = editor_rows(source(path, "Cursor"), cursor)
    assert len(rows) == 3
    assert [row[5]["entry_type"] for row in rows] == ["folder", "workspace", "file"]
    assert "SECRET" not in str(rows)
    assert editor_rows(source(path), cursor) == []
    db.close()


def test_capcut_project_updates(tmp_path):
    path = tmp_path / "root_meta_info.json"
    entry = {
        "draft_id": "a",
        "draft_name": "Film",
        "tm_draft_modified": 1770000000000000,
        "tm_duration": 1000000,
    }
    path.write_text(json.dumps({"all_draft_store": [entry]}))
    cursor = {}
    rows = capcut_rows(source(path, "CapCut"), cursor)
    assert rows[0][1] == 1770000000
    assert rows[0][3] == "project_recent"
    assert capcut_rows(source(path), cursor) == []
    entry["draft_name"] = "Renamed"
    path.write_text(json.dumps({"all_draft_store": [entry]}))
    assert capcut_rows(source(path), cursor)[0][4] == "Renamed"


def test_cursor_index_same_timestamp_edits(tmp_path):
    path = tmp_path / "index.db"
    db = sqlite3.connect(path)
    db.executescript(
        "CREATE TABLE conversations(source TEXT,scope TEXT,id TEXT,title TEXT,updated_at INTEGER);"
    )
    db.executemany(
        "INSERT INTO conversations VALUES(?,?,?,?,?)",
        [("local", "project", str(i), "Title", 1770000000000) for i in range(2)],
    )
    db.commit()
    cursor = {}
    assert len(cursor_conversations(source(path), cursor)) == 2
    assert cursor_conversations(source(path), cursor) == []
    db.execute("UPDATE conversations SET title='Changed' WHERE id='1'")
    db.commit()
    assert len(cursor_conversations(source(path), cursor)) == 1
    db.close()


def test_recent_document_archive(tmp_path, monkeypatch):
    import catchme.sources.documents as docs

    path = tmp_path / "app.sfl3"
    path.write_bytes(
        plistlib.dumps(
            {
                "$objects": [
                    "$null",
                    "Bookmark",
                    b"opaque-bookmark",
                    {"NS.keys": [plistlib.UID(1)], "NS.objects": [plistlib.UID(2)]},
                ]
            },
            fmt=plistlib.FMT_BINARY,
        )
    )
    monkeypatch.setattr(docs, "resolve_bookmark", lambda b: "file:///tmp/deck.key")
    cursor = {}
    rows = recent_document_rows(source(path, "Keynote"), cursor)
    assert rows[0][4] == "deck.key"
    assert recent_document_rows(source(path), cursor) == []
