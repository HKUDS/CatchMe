"""Activity reader restart, data provenance, routing, and API behavior."""

import json
import sqlite3
import time

import pytest

from catchme.sources.catalog import scan
from catchme.sources.collect import browser_rows, collect, jsonl_rows, redact
from catchme.sources.store import ActivityStore


@pytest.fixture
def activity(tmp_path):
    return ActivityStore(tmp_path / "activity.db")


def add_source(activity, path, reader="claude", sid="test"):
    with activity.connect() as db:
        db.execute(
            "INSERT INTO sources(id,name,category,reader,paths,enabled,status,detail) VALUES(?,?,?,?,?,1,?,?)",
            (sid, "Test app", "development", reader, json.dumps([str(path)]), "available", "test"),
        )


def message(text="hello"):
    return (
        json.dumps(
            {"type": "user", "timestamp": "2026-09-17T00:00:00Z", "message": {"content": text}}
        ).encode()
        + b"\n"
    )


def test_incremental_restart_partial_tail_and_dedupe(activity, tmp_path):
    root = tmp_path / "sessions"
    root.mkdir()
    path = root / "session.jsonl"
    path.write_bytes(message() + message("later")[:-3])
    add_source(activity, root)
    assert collect(activity)["inserted"] == 1
    assert collect(ActivityStore(activity.path))["inserted"] == 0
    with path.open("ab") as f:
        f.write(message("later")[-3:])
    assert collect(activity)["inserted"] == 1
    assert activity.facts(0, time.time())["total"] == 2
    with activity.connect() as db:
        db.execute("UPDATE sources SET cursor='{}'")
    assert collect(activity)["inserted"] == 0


def test_rotation_and_truncation(activity, tmp_path):
    root = tmp_path / "sessions"
    root.mkdir()
    path = root / "s.jsonl"
    path.write_bytes(message("old message"))
    add_source(activity, root)
    assert collect(activity)["inserted"] == 1
    path.write_bytes(message("new"))
    assert collect(activity)["inserted"] == 1
    path.unlink()
    path.write_bytes(message("rotated"))
    assert collect(activity)["inserted"] == 1


def test_disabled_and_failed_sources_are_isolated(activity, tmp_path):
    add_source(activity, tmp_path / "missing", reader="safari", sid="bad")
    root = tmp_path / "good"
    root.mkdir()
    (root / "s.jsonl").write_bytes(message())
    add_source(activity, root, sid="good")
    result = collect(activity)
    assert result["inserted"] == 1
    assert "bad" in result["errors"]
    with activity.connect() as db:
        db.execute("UPDATE sources SET enabled=0 WHERE id='good'")
    (root / "s.jsonl").write_bytes(message() + message("second"))
    assert collect(activity)["inserted"] == 0


def test_redaction_before_persistence(activity, tmp_path):
    (tmp_path / "s.jsonl").write_bytes(message("api_key=private-value sk-abcdefghijklmnopqr"))
    add_source(activity, tmp_path)
    collect(activity)
    result = activity.events(0, time.time())["events"][0]
    assert "private-value" not in json.dumps(result)
    assert "abcdefghijklmnopqr" not in json.dumps(result)
    assert redact({"access_token": "sensitive"}) == {"access_token": "[REDACTED]"}


def test_codex_excludes_reasoning_and_tools(tmp_path):
    path = tmp_path / "s.jsonl"
    records = [
        {
            "type": "response_item",
            "payload": {
                "type": "reasoning",
                "content": [{"type": "text", "text": "private reasoning"}],
            },
        },
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": "answer"}],
            },
        },
    ]
    path.write_text("".join(json.dumps(r) + "\n" for r in records))
    rows = jsonl_rows({"paths": [str(tmp_path)], "reader": "codex"}, {})
    assert len(rows) == 1 and rows[0][-1]["text"] == "answer"


def test_browser_reads_committed_wal_and_checkpoints(tmp_path):
    path = tmp_path / "History"
    writer = sqlite3.connect(path)
    writer.executescript(
        "PRAGMA journal_mode=WAL; CREATE TABLE urls(id INTEGER PRIMARY KEY,url TEXT,title TEXT); CREATE TABLE visits(id INTEGER PRIMARY KEY,url INTEGER,visit_time INTEGER);"
    )
    writer.execute("INSERT INTO urls VALUES(1,'https://example.com','Example')")
    writer.execute("INSERT INTO visits VALUES(1,1,13300000000000000)")
    writer.commit()
    cursor = {}
    source = {"paths": [str(path)], "reader": "chrome", "name": "Chrome history"}
    assert len(browser_rows(source, cursor)) == 1
    assert browser_rows(source, cursor) == []
    writer.close()


def test_scan_preserves_enablement_and_cursor(activity, tmp_path):
    sessions = tmp_path / ".claude/projects"
    sessions.mkdir(parents=True)
    scan(activity, home=tmp_path)
    with activity.connect() as db:
        db.execute(
            "UPDATE sources SET enabled=1,cursor=? WHERE id='claude.sessions'", ('{"test":12}',)
        )
    scan(activity, home=tmp_path)
    item = next(s for s in activity.sources() if s["id"] == "claude.sessions")
    assert item["enabled"] and item["cursor"] == {"test": 12}


def test_pagination_and_aggregate_not_limited(activity, tmp_path):
    (tmp_path / "s.jsonl").write_bytes(b"".join(message(str(i)) for i in range(125)))
    add_source(activity, tmp_path)
    collect(activity)
    page = activity.events(0, time.time(), limit=60)
    page2 = activity.events(0, time.time(), limit=60, before=page["next"])
    assert len(page["events"]) == len(page2["events"]) == 60
    assert not {e["id"] for e in page["events"]} & {e["id"] for e in page2["events"]}
    assert activity.facts(0, time.time())["total"] == 125
    assert activity.facts(0, time.time(), source="unknown")["total"] == 0



def test_api_validation_and_origin(client):
    assert client.post("/api/activity/scan").status_code == 415
    assert (
        client.post(
            "/api/activity/scan", json={}, headers={"Origin": "https://evil.example"}
        ).status_code
        == 403
    )
    assert client.get("/api/activity/events?since=NaN").status_code == 400
    assert client.get("/api/activity/facts?since=50&until=10").status_code == 400
    assert client.post("/api/activity/sources/unknown", json={"enabled": True}).status_code == 404
    assert client.get("/api/activity/sources").json == {"sources": [], "applications": []}


def test_models_save_select_and_secret_not_exposed(client):
    data = {
        "name": "custom",
        "service": {
            "provider": "openai",
            "api_url": "https://example.com/v1",
            "api_key": "test-secret",
            "models": ["one", "two"],
        },
        "model": "one",
    }
    result = client.post("/api/activity/models", json=data)
    assert result.status_code == 200
    assert "test-secret" not in result.text
    assert client.get("/api/activity/models").json["services"]["custom"]["has_api_key"]
    assert (
        client.post(
            "/api/activity/models/select", json={"service": "custom", "model": "three"}
        ).status_code
        == 400
    )
    assert (
        client.post("/api/activity/models/select", json={"service": "custom", "model": "two"}).json[
            "selection"
        ]["model"]
        == "two"
    )
    data["service"]["api_key"] = ""
    client.post("/api/activity/models", json=data)
    from catchme.services import load_config

    assert load_config()["services"]["custom"]["api_key"] == "test-secret"


def test_service_route_does_not_inherit_legacy_credentials(monkeypatch):
    from catchme.services.models import resolve_llm

    cfg = {
        "llm": {
            "service": "local",
            "model": "test",
            "api_key": "old-key",
            "extra_headers": {"Authorization": "old"},
        },
        "services": {"local": {"provider": "ollama", "models": ["test"]}},
    }
    resolved = resolve_llm(cfg)
    assert "api_key" not in resolved and "extra_headers" not in resolved
    cfg["services"]["local"]["api_key_env"] = "TEST_ACTIVITY_LLM_KEY"
    monkeypatch.setenv("TEST_ACTIVITY_LLM_KEY", "env-key")
    assert resolve_llm(cfg)["api_key"] == "env-key"
    with pytest.raises(ValueError):
        resolve_llm(cfg, model="missing")


def test_analysis_only_sends_aggregates_and_saves_provenance(client, monkeypatch, tmp_path):
    from catchme.services.llm import LLM

    activity = ActivityStore(tmp_path / "activity.db")
    (tmp_path / "s.jsonl").write_bytes(message("PRIVATE MESSAGE BODY"))
    add_source(activity, tmp_path)
    collect(activity)
    client.post(
        "/api/activity/models",
        json={
            "name": "test",
            "service": {"provider": "openai", "api_key": "test-key", "models": ["test-model"]},
            "model": "test-model",
        },
    )
    sent = []
    monkeypatch.setattr(
        LLM, "complete", lambda self, messages, **kw: sent.append(messages) or "Test analysis"
    )
    result = client.post("/api/activity/analyze", json={"since": time.time() - 86400 * 365})
    assert result.status_code == 200
    assert "PRIVATE MESSAGE BODY" not in json.dumps(sent)
    assert client.get("/api/activity/analyses").json[0]["model"] == "test-model"
    assert client.get("/api/activity/analyses").json[0]["facts"]["total"] == 1


def test_category_does_not_match_substrings_in_unrelated_apps():
    from catchme.sources.catalog import category

    assert category("com.apple.Passwords Passwords") == "other"
    assert category("PhotosSearch.aapbz") == "other"
    assert category("com.microsoft.Word Microsoft Word") == "office"
    assert category("company.thebrowser.Browser Arc") == "browser"
    assert category("com.tencent.xinWeChat 微信") == "communication"


def test_llm_service_routes_real_http_request(client, monkeypatch):
    """Exercise the real SDK against a local provider, without external LLM calls."""
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    from catchme.services.llm import LLM

    received = []

    class Provider(BaseHTTPRequestHandler):
        def do_POST(self):
            received.append(
                (
                    self.path,
                    self.headers["Authorization"],
                    json.loads(self.rfile.read(int(self.headers["Content-Length"]))),
                )
            )
            result = {
                "id": "test",
                "object": "chat.completion",
                "created": 1,
                "model": "route-model",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "routed"},
                        "finish_reason": "stop",
                    }
                ],
            }
            data = json.dumps(result).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        monkeypatch.setenv("ACTIVITY_TEST_KEY", "local-test-key")
        response = client.post(
            "/api/activity/models",
            json={
                "name": "test-route",
                "service": {
                    "provider": "openai",
                    "api_url": f"http://127.0.0.1:{server.server_port}/v1",
                    "api_key_env": "ACTIVITY_TEST_KEY",
                    "models": ["route-model"],
                },
                "model": "route-model",
            },
        )
        assert response.status_code == 200
        llm = LLM()
        assert llm.complete([{"role": "user", "content": "test"}]) == "routed"
        assert received[0][0] == "/v1/chat/completions"
        assert received[0][1] == "Bearer local-test-key"
        assert received[0][2]["model"] == "route-model"
        llm.client.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_busy_collector_does_not_advance_checkpoint(activity, tmp_path):
    import fcntl

    (tmp_path / "s.jsonl").write_bytes(message())
    add_source(activity, tmp_path)
    with activity.path.with_suffix(".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert collect(activity)["busy"]
        assert activity.sources()[0]["cursor"] == {}
    assert collect(activity)["inserted"] == 1


def test_storage_failure_rolls_back_events_and_cursor(activity, tmp_path):
    (tmp_path / "s.jsonl").write_bytes(message("first") + message("second"))
    add_source(activity, tmp_path)
    with activity.connect() as db:
        db.execute(
            "CREATE TRIGGER reject_second BEFORE INSERT ON activity WHEN NEW.title='second' BEGIN SELECT RAISE(ABORT,'test failure'); END"
        )
    result = collect(activity)
    assert result["errors"] and result["inserted"] == 0
    assert activity.facts(0, time.time())["total"] == 0
    assert activity.sources()[0]["cursor"] == {}
