import json
import plistlib
from datetime import datetime

from catchme.sources.apps import recent, sessions, set_mode, set_monitoring
from catchme.sources.catalog import scan
from catchme.sources.collect import collect, jsonl_rows
from catchme.sources.safari import plist_rows
from catchme.sources.store import ActivityStore


def write_records(path, records):
    path.write_text("".join(json.dumps(r) + "\n" for r in records))


def codex_records():
    return [
        {"type": "session_meta", "payload": {"id": "session-one", "cwd": "/fixture/project"}},
        {"type": "turn_context", "payload": {"model": "fixture-model"}},
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "fix the fixture"}],
            },
        },
        {
            "type": "response_item",
            "payload": {
                "type": "function_call",
                "name": "exec_command",
                "call_id": "c1",
                "arguments": '{"cmd":"echo fixture"}',
            },
        },
        {
            "type": "response_item",
            "payload": {"type": "function_call_output", "call_id": "c1", "output": "fixture"},
        },
        {"type": "response_item", "payload": {"type": "reasoning", "text": "excluded"}},
    ]


def test_session_context_survives_incremental_resume(tmp_path):
    path = tmp_path / "one.jsonl"
    write_records(path, codex_records()[:3])
    source = {"paths": [str(tmp_path)], "reader": "codex"}
    cursor = {}
    result = jsonl_rows(source, cursor)
    assert result[0][5]["session_id"] == "session-one"
    assert result[0][5]["project"] == "/fixture/project"
    assert result[0][5]["model"] == "fixture-model"
    with path.open("a") as f:
        f.write(
            json.dumps(
                {
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": "done"}],
                    },
                }
            )
            + "\n"
        )
    result = jsonl_rows(source, cursor)
    assert len(result) == 1 and result[0][5]["session_id"] == "session-one"


def test_full_session_backfill_keeps_conversation_ids_and_groups_tools(tmp_path):
    root = tmp_path / "sessions"
    root.mkdir()
    write_records(root / "one.jsonl", codex_records())
    store = ActivityStore(tmp_path / "activity.db")
    with store.connect() as db:
        db.execute(
            "INSERT INTO sources(id,name,category,reader,paths,enabled,status,detail) VALUES('codex.sessions','Codex','ai','codex',?,1,'available','')",
            (json.dumps([str(root)]),),
        )
    assert collect(store)["inserted"] == 1
    first_id = recent(store, "codex")["events"][0]["id"]
    set_mode(store, "codex", "full", True)
    assert collect(store)["inserted"] == 2
    history = recent(store, "codex", session="session-one")["events"]
    assert len(history) == 3
    assert next(e for e in history if e["kind"] == "conversation")["id"] == first_id
    summary = sessions(store, "codex")[0]
    assert summary["messages"] == 1 and summary["tools"] == 2
    assert summary["title"] == "fix the fixture"
    assert recent(store, "codex", session="other")["events"] == []
    set_mode(store, "codex", "basic")
    assert collect(store)["inserted"] == 0


def test_claude_tools_exclude_images_and_reasoning(tmp_path):
    write_records(
        tmp_path / "one.jsonl",
        [
            {
                "type": "assistant",
                "sessionId": "cc-one",
                "cwd": "/fixture/cc",
                "message": {
                    "model": "fixture-model",
                    "content": [
                        {"type": "thinking", "thinking": "excluded"},
                        {
                            "type": "tool_use",
                            "name": "Read",
                            "id": "c1",
                            "input": {"file_path": "fixture.txt"},
                        },
                    ],
                },
            },
            {
                "type": "user",
                "message": {
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "c1",
                            "content": [
                                {"type": "text", "text": "test output"},
                                {"type": "image", "source": {"data": "excluded image"}},
                            ],
                        }
                    ]
                },
            },
        ],
    )
    basic = jsonl_rows({"paths": [str(tmp_path)], "reader": "claude"}, {})
    assert basic == []
    full = jsonl_rows({"paths": [str(tmp_path)], "reader": "claude", "full": True}, {})
    assert [r[3] for r in full] == ["tool_call", "tool_result"]
    assert full[1][5]["text"] == "test output"
    assert full[1][5]["project"] == "/fixture/cc"


def test_safari_bookmark_folders_and_download_evidence(tmp_path):
    path = tmp_path / "Bookmarks.plist"
    path.write_bytes(
        plistlib.dumps(
            {
                "Title": "Favorites",
                "Children": [
                    {
                        "Title": "Research",
                        "Children": [
                            {
                                "URLString": "https://example.test/article",
                                "URIDictionary": {"title": "fixture article"},
                                "WebBookmarkUUID": "b1",
                            }
                        ],
                    }
                ],
            }
        )
    )
    source = {"reader": "safari_bookmarks", "paths": [str(path)]}
    cursor = {}
    result = plist_rows(source, cursor)
    assert result[0][5]["folder"] == "Favorites / Research"
    assert result[0][3] == "bookmark"
    assert plist_rows(source, cursor) == []
    download = tmp_path / "Downloads.plist"
    download.write_bytes(
        plistlib.dumps(
            {
                "DownloadHistory": [
                    {
                        "DownloadEntryURL": "https://example.test/a.pdf",
                        "DownloadEntryPath": "/fixture/a.pdf",
                        "DownloadEntryDateAdded": datetime(2026, 1, 2),
                    }
                ]
            }
        )
    )
    result = plist_rows({"reader": "safari_downloads", "paths": [str(download)]}, {})
    assert result[0][3] == "download" and result[0][4] == "a.pdf"
    assert "不保证下载完成" in result[0][5]["meaning"]


def test_new_sources_follow_explicit_app_choice_without_overriding_existing_source(
    tmp_path, monkeypatch
):
    store = ActivityStore(tmp_path / "activity.db")
    set_monitoring(store, "safari", True)
    monkeypatch.setattr("catchme.sources.catalog.applications", lambda home: [])
    scan(store, home=tmp_path)
    states = {s["id"]: s["enabled"] for s in store.sources()}
    assert states["safari.bookmarks"] and states["safari.downloads"]
    with store.connect() as db:
        db.execute("UPDATE sources SET enabled=0 WHERE id='safari.bookmarks'")
    scan(store, home=tmp_path)
    assert not next(s for s in store.sources() if s["id"] == "safari.bookmarks")["enabled"]


def test_oversized_session_record_does_not_block_other_messages(tmp_path, monkeypatch):
    import importlib

    module = importlib.import_module("catchme.sources.collect")
    monkeypatch.setattr(module, "MAX_LINE", 400)
    path = tmp_path / "one.jsonl"
    write_records(path, codex_records()[:3])
    with path.open("a") as f:
        f.write(json.dumps({"type": "attachment", "blob": "x" * 2000}) + "\n")
        f.write(json.dumps(codex_records()[2]) + "\n")
    result = jsonl_rows({"paths": [str(tmp_path)], "reader": "codex"}, {})
    assert [r[3] for r in result] == ["conversation", "capture_gap", "conversation"]
    assert all("blob" not in r[5] for r in result)


def test_codex_does_not_claim_chatgpt_with_reused_bundle(tmp_path):
    store = ActivityStore(tmp_path / "activity.db")
    with store.connect() as db:
        db.execute(
            "INSERT INTO activity(source,external_id,ts,observed,app,category,kind,title,payload) VALUES('system.foreground','1',1,1,'ChatGPT','ai','foreground_sample','ChatGPT',?)",
            (json.dumps({"bundle_id": "com.openai.codex"}),),
        )
    assert len(recent(store, "chatgpt")["events"]) == 1
    assert recent(store, "codex")["events"] == []
