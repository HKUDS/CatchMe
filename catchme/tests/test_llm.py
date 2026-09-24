"""Tests for catchme.services.llm — CallBudget, TokenTracker, LLM wrapper, vision helpers."""

from __future__ import annotations

import base64
import json
import threading
from types import SimpleNamespace
from unittest import mock

import pytest

from catchme.services.llm import (
    _MIME_MAP,
    LLM,
    LLMBudgetExhausted,
    _CallBudget,
    _TokenTracker,
    load_usage_from_disk,
)
from catchme.services.providers import PROVIDERS, get_default_api_url

# ── _CallBudget ──


class TestCallBudget:
    def _make(self, max_calls: int) -> _CallBudget:
        b = _CallBudget()
        b._max = max_calls
        b._loaded = True
        return b

    def test_unlimited_always_allows(self):
        b = self._make(0)
        for _ in range(100):
            assert b.acquire() is True
        assert b.count == 100
        assert b.remaining == -1

    def test_limited_exhausts(self):
        b = self._make(3)
        assert b.acquire() is True
        assert b.acquire() is True
        assert b.acquire() is True
        assert b.acquire() is False
        assert b.count == 3

    def test_remaining_decreases(self):
        b = self._make(5)
        assert b.remaining == 5
        b.acquire()
        assert b.remaining == 4
        b.acquire()
        assert b.remaining == 3

    def test_count_increments(self):
        b = self._make(0)
        assert b.count == 0
        b.acquire()
        b.acquire()
        assert b.count == 2

    def test_thread_safety(self):
        b = self._make(1000)
        errors = []

        def worker():
            try:
                for _ in range(100):
                    b.acquire()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []
        assert b.count == 1000
        assert b.remaining == 0
        assert b.acquire() is False


# ── _TokenTracker ──


class TestTokenTracker:
    def test_record_and_totals(self):
        t = _TokenTracker()
        with mock.patch.object(t, "_persist"):
            t.record(100, 50)
            t.record(200, 80)
        totals = t.totals
        assert totals["prompt"] == 300
        assert totals["completion"] == 130
        assert totals["total"] == 430

    def test_history_returns_copy(self):
        t = _TokenTracker()
        with mock.patch.object(t, "_persist"):
            t.record(10, 5)
            t.record(20, 10)
        h = t.history()
        assert len(h) == 2
        assert h[0][1] == 10  # prompt_tokens
        assert h[1][2] == 10  # completion_tokens
        h.clear()
        assert len(t.history()) == 2  # original unaffected

    def test_empty_totals(self):
        t = _TokenTracker()
        assert t.totals == {"prompt": 0, "completion": 0, "total": 0}

    def test_persist_writes_file(self, cfg):
        t = _TokenTracker()
        with mock.patch("catchme.services.llm._get_usage_path", return_value=cfg.usage_path):
            t.record(50, 25)
        assert cfg.usage_path.is_file()
        data = json.loads(cfg.usage_path.read_text(encoding="utf-8"))
        assert data["call_count"] == 1
        assert data["tokens"]["total"] == 75
        assert len(data["history"]) == 1

    def test_persist_merges_existing(self, cfg):
        existing = {
            "call_count": 1,
            "tokens": {"prompt": 10, "completion": 5, "total": 15},
            "history": [{"ts": 1000.0, "prompt": 10, "completion": 5}],
        }
        cfg.usage_path.write_text(json.dumps(existing), encoding="utf-8")

        t = _TokenTracker()
        with mock.patch("catchme.services.llm._get_usage_path", return_value=cfg.usage_path):
            t.record(20, 10)

        data = json.loads(cfg.usage_path.read_text(encoding="utf-8"))
        assert data["call_count"] == 2
        assert data["tokens"]["prompt"] == 30
        assert data["tokens"]["total"] == 45

    def test_thread_safe_recording(self):
        t = _TokenTracker()
        with mock.patch.object(t, "_persist"):
            threads = []
            for _ in range(10):
                th = threading.Thread(target=lambda: t.record(10, 5))
                threads.append(th)
                th.start()
            for th in threads:
                th.join()
        assert t.totals["prompt"] == 100
        assert t.totals["completion"] == 50


# ── load_usage_from_disk ──


class TestLoadUsageFromDisk:
    def test_file_not_found_returns_zeros(self, cfg):
        with mock.patch(
            "catchme.services.llm._get_usage_path", return_value=cfg.root / "nonexistent.json"
        ):
            result = load_usage_from_disk()
        assert result["call_count"] == 0
        assert result["tokens"]["total"] == 0
        assert result["history"] == []

    def test_valid_file(self, cfg):
        data = {
            "call_count": 5,
            "tokens": {"prompt": 500, "completion": 200, "total": 700},
            "history": [{"ts": 1.0, "prompt": 100, "completion": 40}],
        }
        cfg.usage_path.write_text(json.dumps(data), encoding="utf-8")
        with mock.patch("catchme.services.llm._get_usage_path", return_value=cfg.usage_path):
            result = load_usage_from_disk()
        assert result["call_count"] == 5
        assert result["tokens"]["total"] == 700

    def test_corrupt_json_returns_zeros(self, cfg):
        cfg.usage_path.write_text("{{not valid json", encoding="utf-8")
        with mock.patch("catchme.services.llm._get_usage_path", return_value=cfg.usage_path):
            result = load_usage_from_disk()
        assert result["call_count"] == 0


# ── LLM initialization ──


class TestLLMInit:
    def test_explicit_overrides(self):
        with mock.patch(
            "catchme.services.llm._load_llm_config", return_value={"provider": "openai"}
        ):
            llm = LLM(model="gpt-4o", api_key="sk-test", api_url="https://custom/v1")
        assert llm.model == "gpt-4o"
        assert llm._api_key == "sk-test"
        assert llm._api_url == "https://custom/v1"

    def test_reads_from_config(self):
        fake_cfg = {
            "provider": "deepseek",
            "model": "deepseek-chat",
            "api_key": "sk-ds",
            "api_url": "https://api.deepseek.com/v1",
        }
        with mock.patch("catchme.services.llm._load_llm_config", return_value=fake_cfg):
            llm = LLM()
        assert llm.model == "deepseek-chat"
        assert llm._api_key == "sk-ds"

    def test_lazy_client_not_created_at_init(self):
        with mock.patch(
            "catchme.services.llm._load_llm_config", return_value={"provider": "openai"}
        ):
            llm = LLM(model="test", api_key="k", api_url="http://x")
        assert llm._client is None
        assert llm._aclient is None


# ── LLM.complete (mocked client) ──


def _mock_response(content: str, prompt_tokens: int = 10, completion_tokens: int = 5):
    """Build a fake openai ChatCompletion response."""
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens),
    )


class TestLLMComplete:
    def _make_llm(self):
        with mock.patch(
            "catchme.services.llm._load_llm_config", return_value={"provider": "openai"}
        ):
            llm = LLM(model="test-model", api_key="sk-fake", api_url="http://test")
        return llm

    def test_complete_returns_text(self):
        llm = self._make_llm()
        fake_client = mock.MagicMock()
        fake_client.chat.completions.create.return_value = _mock_response("Hello!")
        llm._client = fake_client

        with mock.patch("catchme.services.llm._budget") as mock_budget:
            mock_budget.acquire.return_value = True
            with mock.patch("catchme.services.llm._token_tracker"):
                result = llm.complete([{"role": "user", "content": "Hi"}])

        assert result == "Hello!"
        fake_client.chat.completions.create.assert_called_once()

    def test_complete_tracks_tokens(self):
        llm = self._make_llm()
        fake_client = mock.MagicMock()
        fake_client.chat.completions.create.return_value = _mock_response(
            "result", prompt_tokens=100, completion_tokens=50
        )
        llm._client = fake_client

        tracker = _TokenTracker()
        with (
            mock.patch("catchme.services.llm._budget") as mock_budget,
            mock.patch("catchme.services.llm._token_tracker", tracker),
            mock.patch.object(tracker, "_persist"),
        ):
            mock_budget.acquire.return_value = True
            llm.complete([{"role": "user", "content": "test"}])

        assert tracker.totals["prompt"] == 100
        assert tracker.totals["completion"] == 50

    def test_complete_raises_on_exhausted_budget(self):
        llm = self._make_llm()
        budget = _CallBudget()
        budget._max = 0
        budget._loaded = True
        budget._max = 1
        budget.acquire()  # exhaust

        with mock.patch("catchme.services.llm._budget", budget), pytest.raises(LLMBudgetExhausted):
            llm.complete([{"role": "user", "content": "test"}])

    def test_complete_passes_kwargs(self):
        llm = self._make_llm()
        fake_client = mock.MagicMock()
        fake_client.chat.completions.create.return_value = _mock_response("ok")
        llm._client = fake_client

        with (
            mock.patch("catchme.services.llm._budget") as mb,
            mock.patch("catchme.services.llm._token_tracker"),
        ):
            mb.acquire.return_value = True
            llm.complete(
                [{"role": "user", "content": "hi"}],
                temperature=0.2,
                max_tokens=100,
            )

        call_kwargs = fake_client.chat.completions.create.call_args
        assert call_kwargs.kwargs["temperature"] == 0.2
        assert call_kwargs.kwargs["max_tokens"] == 100

    def test_complete_handles_none_content(self):
        llm = self._make_llm()
        resp = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=None))],
            usage=SimpleNamespace(prompt_tokens=5, completion_tokens=0),
        )
        fake_client = mock.MagicMock()
        fake_client.chat.completions.create.return_value = resp
        llm._client = fake_client

        with (
            mock.patch("catchme.services.llm._budget") as mb,
            mock.patch("catchme.services.llm._token_tracker"),
        ):
            mb.acquire.return_value = True
            result = llm.complete([{"role": "user", "content": "hi"}])

        assert result == ""

    def test_complete_handles_no_usage(self):
        llm = self._make_llm()
        resp = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
            usage=None,
        )
        fake_client = mock.MagicMock()
        fake_client.chat.completions.create.return_value = resp
        llm._client = fake_client

        tracker = _TokenTracker()
        with (
            mock.patch("catchme.services.llm._budget") as mb,
            mock.patch("catchme.services.llm._token_tracker", tracker),
            mock.patch.object(tracker, "_persist"),
        ):
            mb.acquire.return_value = True
            result = llm.complete([{"role": "user", "content": "hi"}])

        assert result == "ok"
        assert tracker.totals["total"] == 0


# ── LLM.stream (mocked client) ──


class TestLLMStream:
    def _make_llm(self):
        with mock.patch(
            "catchme.services.llm._load_llm_config", return_value={"provider": "openai"}
        ):
            llm = LLM(model="test", api_key="k", api_url="http://x")
        return llm

    def test_stream_yields_deltas(self):
        llm = self._make_llm()
        chunks = [
            SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="Hello"))]),
            SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=" world"))]),
            SimpleNamespace(choices=[]),  # empty choices chunk
        ]
        fake_client = mock.MagicMock()
        fake_client.chat.completions.create.return_value = iter(chunks)
        llm._client = fake_client

        with mock.patch("catchme.services.llm._budget") as mb:
            mb.acquire.return_value = True
            result = list(llm.stream([{"role": "user", "content": "hi"}]))

        assert result == ["Hello", " world"]


# ── Vision helpers ──


class TestVisionHelpers:
    def test_build_vision_content_single_image(self, tmp_path):
        img = tmp_path / "test.png"
        img.write_bytes(b"\x89PNG_fake_content")

        content = LLM._build_vision_content("Describe this", [str(img)], "auto")
        assert len(content) == 2  # 1 image + 1 text
        assert content[0]["type"] == "image_url"
        assert content[0]["image_url"]["detail"] == "auto"
        assert content[0]["image_url"]["url"].startswith("data:image/png;base64,")
        assert content[1] == {"type": "text", "text": "Describe this"}

        b64_data = content[0]["image_url"]["url"].split(",")[1]
        decoded = base64.b64decode(b64_data)
        assert decoded == b"\x89PNG_fake_content"

    def test_build_vision_content_multiple_images(self, tmp_path):
        imgs = []
        for name in ["a.jpg", "b.webp"]:
            f = tmp_path / name
            f.write_bytes(b"fake")
            imgs.append(str(f))

        content = LLM._build_vision_content("Compare", imgs, "low")
        assert len(content) == 3  # 2 images + 1 text
        assert content[0]["image_url"]["url"].startswith("data:image/jpeg;base64,")
        assert content[1]["image_url"]["url"].startswith("data:image/webp;base64,")
        assert all(c["image_url"]["detail"] == "low" for c in content[:2])

    def test_build_vision_unknown_ext_defaults_to_jpeg(self, tmp_path):
        img = tmp_path / "photo.bmp"
        img.write_bytes(b"BM_fake")
        content = LLM._build_vision_content("What?", [str(img)], "auto")
        assert "image/jpeg" in content[0]["image_url"]["url"]

    def test_mime_map_coverage(self):
        assert _MIME_MAP["jpg"] == "jpeg"
        assert _MIME_MAP["jpeg"] == "jpeg"
        assert _MIME_MAP["png"] == "png"
        assert _MIME_MAP["webp"] == "webp"
        assert _MIME_MAP["gif"] == "gif"


# ── Providers ──


class TestProviders:
    def test_get_default_api_url_known(self):
        url = get_default_api_url("openai")
        assert url == "https://api.openai.com/v1"

    def test_get_default_api_url_openrouter(self):
        url = get_default_api_url("openrouter")
        assert url == "https://openrouter.ai/api/v1"

    def test_get_default_api_url_requesty(self):
        url = get_default_api_url("requesty")
        assert url == "https://router.requesty.ai/v1"

    def test_get_default_api_url_unknown(self):
        assert get_default_api_url("nonexistent_provider_xyz") is None

    def test_all_providers_have_four_fields(self):
        for entry in PROVIDERS:
            assert len(entry) == 4
            name, display, url, key_url = entry
            assert name
            assert display
            assert url
