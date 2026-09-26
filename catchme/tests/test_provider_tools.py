import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from catchme.services.provider_tools import draft_service, probe


@pytest.fixture
def provider():
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append((self.path, self.headers.get("Authorization")))
            if self.headers.get("Authorization") == "Bearer redirect":
                self.send_response(302)
                self.send_header("Location", "/v1/redirect-target")
                self.end_headers()
                return
            if self.headers.get("Authorization") == "Bearer bad":
                self.send_response(401)
                self.end_headers()
                return
            data = {
                "object": "list",
                "data": [{"id": "alpha", "object": "model"}, {"id": "beta", "object": "model"}],
            }
            self.reply(data)

        def do_POST(self):
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append((self.path, data))
            if self.path == "/v1/responses":
                self.reply(
                    {
                        "id": "r",
                        "object": "response",
                        "output": [
                            {
                                "type": "message",
                                "id": "m",
                                "role": "assistant",
                                "content": [
                                    {"type": "output_text", "text": "OK", "annotations": []}
                                ],
                            }
                        ],
                    }
                )
            else:
                self.reply(
                    {
                        "id": "c",
                        "object": "chat.completion",
                        "choices": [
                            {
                                "index": 0,
                                "message": {"role": "assistant", "content": "OK"},
                                "finish_reason": "stop",
                            }
                        ],
                    }
                )

        def reply(self, data):
            raw = json.dumps(data).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield (
        {
            "provider": "custom",
            "api_url": f"http://127.0.0.1:{server.server_port}/v1",
            "api_key": "test-key",
            "models": [],
        },
        requests,
    )
    server.shutdown()
    server.server_close()
    thread.join()


def test_provider_and_models_without_saved_config(client, provider):
    route, requests = provider
    data = {"name": "draft", "service": route}
    r = client.post("/api/activity/providers/test", json=data)
    assert r.json["ok"] and r.json["model_count"] == 2
    assert client.post("/api/activity/providers/models", json=data).json["models"] == [
        "alpha",
        "beta",
    ]
    assert not client.get("/api/activity/models").json["services"]
    assert requests[0] == ("/v1/models", "Bearer test-key")


@pytest.mark.parametrize("wire", ["completions", "responses"])
def test_generation_uses_draft_model_and_protocol(client, provider, wire):
    route, requests = provider
    route["wire_api"] = wire
    r = client.post(
        "/api/activity/models/test", json={"name": "draft", "service": route, "model": "alpha"}
    )
    assert r.status_code == 200 and r.json["ok"] and r.json["response"] == "OK"
    assert requests[-1][1]["model"] == "alpha"
    assert "Reply with OK." in json.dumps(requests[-1][1])


def test_save_provider_then_activate_model(client, provider):
    route, _ = provider
    r = client.post("/api/activity/models", json={"name": "draft", "service": route})
    assert r.status_code == 200 and not r.json["selection"]["service"]
    assert r.json["services"]["draft"]["models"] == []
    route["models"] = ["alpha"]
    assert client.post(
        "/api/activity/models", json={"name": "draft", "service": route, "model": "alpha"}
    ).json["selection"] == {"service": "draft", "model": "alpha"}
    # Saved credential works without echoing it through the client.
    route["api_key"] = ""
    assert client.post(
        "/api/activity/providers/test", json={"name": "draft", "service": route}
    ).json["ok"]


def test_diagnostics_do_not_leak_error_body(provider):
    route, _ = provider
    route["api_key"] = "bad"
    result = probe(route)
    assert not result["ok"] and result["status"] == 401 and "bad" not in result["error"]


def test_saved_credentials_not_silently_sent_to_new_endpoint():
    cfg = {
        "services": {
            "saved": {
                "provider": "openai",
                "api_url": "https://a.example/v1",
                "api_key": "secret",
                "models": ["one"],
            }
        }
    }
    with pytest.raises(ValueError, match="endpoint changed"):
        draft_service(cfg, {"name": "saved", "service": {"api_url": "https://b.example/v1"}})


def test_provider_probe_does_not_follow_redirects(provider):
    route, requests = provider
    route["api_key"] = "redirect"
    result = probe(route)
    assert not result["ok"] and result["status"] == 302
    assert len(requests) == 1


def test_endpoint_change_only_uses_explicit_new_credentials():
    config = {"services": {"saved": {
        "provider": "openai", "api_url": "https://old.example/v1", "api_key": "old",
        "api_key_env": "OLD_KEY", "extra_headers": {"Authorization": "old-token"}, "models": []
    }}}
    route = draft_service(config, {"name": "saved", "service": {
        "api_url": "https://new.example/v1", "api_key": "new"
    }})
    assert route["api_key"] == "new"
    assert "api_key_env" not in route and "extra_headers" not in route
