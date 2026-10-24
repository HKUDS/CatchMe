"""OpenAI-compatible LLM client for catchme.

Wraps the ``openai`` Python package so any OpenAI-compatible endpoint works.
Configure four fields in ``services/config.json``::

    {
        "llm": {
            "provider": "openrouter",
            "api_key": "sk-or-...",
            "api_url": "https://openrouter.ai/api/v1",
            "model": "google/gemini-3-flash-preview"
        }
    }

If ``api_url`` is omitted, a default URL is looked up from the provider name.
See ``providers.py`` for the full list of supported providers.

Usage::

    from catchme.services.llm import LLM

    llm = LLM()                                  # reads config.json
    llm = LLM(model="gpt-4o", api_key="sk-...")  # explicit override

    answer = llm.complete([{"role": "user", "content": "Hi"}])
    answer = await llm.acomplete(messages)
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import tempfile
import threading
import time as _time
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # Keep OpenAI types import-time optional; runtime imports stay lazy in properties.
    from openai import AsyncOpenAI, OpenAI

log = logging.getLogger(__name__)

_MIME_MAP = {
    "jpg": "jpeg",
    "jpeg": "jpeg",
    "png": "png",
    "webp": "webp",
    "gif": "gif",
}


def _get_usage_path() -> Path:
    from ..config import get_default_config

    return get_default_config().usage_path


def _load_llm_config() -> dict[str, Any]:
    from catchme.services import load_config

    return load_config().get("llm", {})


class _CallBudget:
    """Process-global LLM call counter. Thread-safe.

    ``max_calls = 0`` means unlimited.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._count = 0
        self._max = 0
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            cfg = _load_llm_config()
            self._max = int(cfg.get("max_calls", 0))
            self._loaded = True

    def acquire(self) -> bool:
        """Return True if a call is allowed; False if budget exhausted."""
        with self._lock:
            self._ensure_loaded()
            if self._max <= 0:
                self._count += 1
                return True
            if self._count >= self._max:
                return False
            self._count += 1
            return True

    @property
    def count(self) -> int:
        return self._count

    @property
    def remaining(self) -> int:
        with self._lock:
            self._ensure_loaded()
            if self._max <= 0:
                return -1
            return max(0, self._max - self._count)


_budget = _CallBudget()


class _TokenTracker:
    """Process-global token usage tracker. Thread-safe.

    Stores per-call records and persists to ``data/llm_usage.json`` so
    that the separate *web* process can read the statistics produced by
    the *awake* process.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: list[tuple[float, int, int]] = []
        self._prompt_total = 0
        self._completion_total = 0

    def record(self, prompt_tokens: int, completion_tokens: int) -> None:
        ts = _time.time()
        with self._lock:
            self._records.append((ts, prompt_tokens, completion_tokens))
            self._prompt_total += prompt_tokens
            self._completion_total += completion_tokens
        self._persist()

    @property
    def totals(self) -> dict[str, int]:
        return {
            "prompt": self._prompt_total,
            "completion": self._completion_total,
            "total": self._prompt_total + self._completion_total,
        }

    def history(self) -> list[tuple[float, int, int]]:
        """Return a copy of all (ts, prompt_tokens, completion_tokens) records."""
        with self._lock:
            return list(self._records)

    def _persist(self) -> None:
        """Atomically merge current session with all known data on disk."""
        try:
            path = _get_usage_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            with self._lock:
                my_history = [
                    {"ts": r[0], "prompt": r[1], "completion": r[2]} for r in self._records
                ]
            existing_history: list[dict] = []
            try:
                if path.is_file():
                    with open(path, encoding="utf-8") as f:
                        existing_history = json.load(f).get("history", [])
            except Exception:
                pass
            my_ts = {r["ts"] for r in my_history}
            merged = [r for r in existing_history if r["ts"] not in my_ts]
            merged.extend(my_history)
            merged.sort(key=lambda r: r["ts"])
            if len(merged) > 100000:
                merged = merged[-100000:]
            total_p = sum(r["prompt"] for r in merged)
            total_c = sum(r["completion"] for r in merged)
            data = {
                "call_count": len(merged),
                "tokens": {
                    "prompt": total_p,
                    "completion": total_c,
                    "total": total_p + total_c,
                },
                "history": merged,
            }
            fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp", prefix=".llm_usage_")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(data, f)
                os.replace(tmp, str(path))
            except BaseException:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
                raise
        except Exception:
            log.debug("failed to persist LLM usage", exc_info=True)


_token_tracker = _TokenTracker()


def load_usage_from_disk() -> dict[str, Any]:
    """Read persisted LLM usage (called by the web process).

    Returns a dict compatible with the ``/api/monitor`` response shape.
    Falls back to zeros if the file does not exist yet.
    """
    path = _get_usage_path()
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "call_count": 0,
            "tokens": {"prompt": 0, "completion": 0, "total": 0},
            "history": [],
        }


class LLMBudgetExhausted(Exception):
    """Raised when the process-wide LLM call budget is exhausted."""


class LLM:
    """Thin, lazy wrapper around the OpenAI-compatible LLM APIs.

    Reads ``provider``, ``api_key``, ``api_url``, ``model`` from
    ``config.json``.  Both sync and async clients are created on first use.

    Set ``wire_api = "responses"`` in the ``llm`` config block to use the
    OpenAI Responses API (``POST /v1/responses``) instead of Chat Completions.
    Messages are automatically converted from chat-completions format to
    the Responses API ``input_text`` / ``input_image`` format before being
    passed to the SDK.
    """

    _RETRYABLE_STATUS = {429, 502, 503, 504}
    _MAX_RETRIES = 3

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        api_url: str | None = None,
    ) -> None:
        cfg = _load_llm_config()

        self.model = model or cfg.get("model") or os.getenv("LLM_MODEL", "gpt-4o-mini")

        self._api_key = api_key or cfg.get("api_key") or os.getenv("OPENAI_API_KEY", "")

        url = api_url or cfg.get("api_url")
        if not url:
            from catchme.services.providers import get_default_api_url

            url = get_default_api_url(cfg.get("provider", "openai"))
        self._api_url = url or os.getenv("OPENAI_BASE_URL")
        self._extra_headers: dict[str, str] = cfg.get("extra_headers") or {}

        self._use_responses_api = cfg.get("wire_api") == "responses"

        self._client: OpenAI | None = None
        self._aclient: AsyncOpenAI | None = None

        log.info(
            "LLM: model=%s  provider=%s  api_url=%s  wire=%s",
            self.model,
            cfg.get("provider", "?"),
            self._api_url or "(default)",
            "responses" if self._use_responses_api else "completions",
        )

    # -- lazy clients ------------------------------------------------------

    @property
    def client(self) -> OpenAI:
        """Sync ``openai.OpenAI`` client (created on first access)."""
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(
                api_key=self._api_key,
                base_url=self._api_url,
                default_headers=self._extra_headers or None,
            )
        return self._client

    @property
    def aclient(self) -> AsyncOpenAI:
        """Async ``openai.AsyncOpenAI`` client (created on first access)."""
        if self._aclient is None:
            from openai import AsyncOpenAI

            self._aclient = AsyncOpenAI(
                api_key=self._api_key,
                base_url=self._api_url,
                default_headers=self._extra_headers or None,
            )
        return self._aclient

    # -- budget & usage ----------------------------------------------------

    @staticmethod
    def budget_remaining() -> int:
        """Number of LLM calls left (-1 = unlimited)."""
        return _budget.remaining

    @staticmethod
    def call_count() -> int:
        return _budget.count

    @staticmethod
    def token_totals() -> dict[str, int]:
        """Return ``{"prompt": N, "completion": N, "total": N}``."""
        return _token_tracker.totals

    @staticmethod
    def token_history() -> list[tuple[float, int, int]]:
        """Return list of ``(timestamp, prompt_tokens, completion_tokens)``."""
        return _token_tracker.history()

    def _check_budget(self) -> None:
        if not _budget.acquire():
            raise LLMBudgetExhausted(
                f"LLM call limit reached ({_budget.count} calls). "
                "Increase llm.max_calls in config.json or set to 0 for unlimited."
            )

    @staticmethod
    def _record_usage(usage: Any) -> None:
        """Record token counts from either API format.

        Chat Completions returns an object with ``prompt_tokens`` /
        ``completion_tokens``.  The Responses API returns an object with
        ``input_tokens`` / ``output_tokens``.

        We dispatch on ``completion_tokens`` because it is present *only*
        in Chat Completions objects.  (Recent SDK versions add
        ``input_tokens`` as an alias on both, so that field is unreliable
        for dispatch.)
        """
        if not usage:
            return
        ct = getattr(usage, "completion_tokens", None)
        if ct is not None:
            # Chat Completions
            _token_tracker.record(
                getattr(usage, "prompt_tokens", 0) or 0,
                ct or 0,
            )
        else:
            # Responses API
            _token_tracker.record(
                getattr(usage, "input_tokens", 0) or 0,
                getattr(usage, "output_tokens", 0) or 0,
            )

    # -- Responses API helpers ---------------------------------------------

    @staticmethod
    def _convert_content_for_responses(messages: list[dict]) -> list[dict]:
        """Convert chat-completions message format to Responses API input.

        Rules (empirically verified against the provider):

        - **String content** — kept as-is.
        - **Array content with images** — part types are converted:
          ``image_url`` → ``input_image`` (URL flattened to a string),
          ``text`` → ``input_text``.
        - **Array content, text-only** — flattened to a plain string
          (some providers reject text-only content arrays).
        """
        out: list[dict] = []
        for msg in messages:
            content = msg.get("content")
            if not isinstance(content, list):
                out.append(msg)
                continue

            has_images = any(p.get("type") == "image_url" for p in content)

            if not has_images:
                text = "\n".join(p.get("text", "") for p in content if p.get("type") == "text")
                out.append({**msg, "content": text})
            else:
                parts: list[dict] = []
                for p in content:
                    t = p.get("type")
                    if t == "image_url":
                        url = p.get("image_url", "")
                        if isinstance(url, dict):
                            url = url.get("url", "")
                        parts.append({"type": "input_image", "image_url": url})
                    elif t == "text":
                        parts.append({"type": "input_text", "text": p.get("text", "")})
                    else:
                        log.debug(
                            "_convert_content_for_responses: dropping unknown part type %r", t
                        )
                out.append({**msg, "content": parts})
        return out

    def _complete_via_responses(self, messages: list[dict], max_tokens: int | None) -> str:
        """Sync Responses API call with automatic retry on transient errors."""
        from openai import APIStatusError

        converted = self._convert_content_for_responses(messages)
        kwargs: dict[str, Any] = {"model": self.model, "input": converted}
        if max_tokens is not None:
            kwargs["max_output_tokens"] = max_tokens

        last_exc: Exception | None = None
        for attempt in range(self._MAX_RETRIES):
            try:
                resp = self.client.responses.create(**kwargs)
                self._record_usage(resp.usage)
                return resp.output_text or ""
            except APIStatusError as exc:
                status = exc.status_code
                if status not in self._RETRYABLE_STATUS:
                    raise
                last_exc = exc
                if attempt + 1 < self._MAX_RETRIES:
                    delay = 2**attempt
                    log.warning(
                        "responses API %d, retry %d/%d in %ds",
                        status,
                        attempt + 1,
                        self._MAX_RETRIES,
                        delay,
                    )
                    _time.sleep(delay)
        raise last_exc  # type: ignore[misc]

    async def _acomplete_via_responses(self, messages: list[dict], max_tokens: int | None) -> str:
        """Async Responses API call with automatic retry on transient errors."""
        from openai import APIStatusError

        converted = self._convert_content_for_responses(messages)
        kwargs: dict[str, Any] = {"model": self.model, "input": converted}
        if max_tokens is not None:
            kwargs["max_output_tokens"] = max_tokens

        last_exc: Exception | None = None
        for attempt in range(self._MAX_RETRIES):
            try:
                resp = await self.aclient.responses.create(**kwargs)
                self._record_usage(resp.usage)
                return resp.output_text or ""
            except APIStatusError as exc:
                status = exc.status_code
                if status not in self._RETRYABLE_STATUS:
                    raise
                last_exc = exc
                if attempt + 1 < self._MAX_RETRIES:
                    delay = 2**attempt
                    log.warning(
                        "responses API %d, retry %d/%d in %ds",
                        status,
                        attempt + 1,
                        self._MAX_RETRIES,
                        delay,
                    )
                    await asyncio.sleep(delay)
        raise last_exc  # type: ignore[misc]

    # -- sync completions --------------------------------------------------

    def complete(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs,
    ) -> str:
        """Blocking chat completion.  Returns the assistant's text."""
        self._check_budget()
        if self._use_responses_api:
            return self._complete_via_responses(messages, max_tokens)
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        self._record_usage(resp.usage)
        return resp.choices[0].message.content or ""

    def stream(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs,
    ) -> Iterator[str]:
        """Streaming chat completion.  Yields content-delta strings."""
        if self._use_responses_api:
            raise NotImplementedError("streaming is not supported with wire_api='responses'")
        self._check_budget()
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            **kwargs,
        )
        for chunk in resp:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    # -- async completions -------------------------------------------------

    async def acomplete(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs,
    ) -> str:
        """Async chat completion.  Returns the assistant's text."""
        self._check_budget()
        if self._use_responses_api:
            return await self._acomplete_via_responses(messages, max_tokens)
        resp = await self.aclient.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        self._record_usage(resp.usage)
        return resp.choices[0].message.content or ""

    async def astream(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Async streaming chat completion.  Yields content-delta strings."""
        if self._use_responses_api:
            raise NotImplementedError("streaming is not supported with wire_api='responses'")
        self._check_budget()
        resp = await self.aclient.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            **kwargs,
        )
        async for chunk in resp:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    # -- vision helpers ----------------------------------------------------

    def complete_with_vision(
        self,
        prompt: str,
        image_paths: list[str],
        detail: str = "auto",
        **kwargs,
    ) -> str:
        """Send images + text prompt through the vision API (sync).

        Budget is checked inside ``complete()``.
        """
        messages = [
            {
                "role": "user",
                "content": self._build_vision_content(prompt, image_paths, detail),
            }
        ]
        return self.complete(messages, **kwargs)

    async def acomplete_with_vision(
        self,
        prompt: str,
        image_paths: list[str],
        detail: str = "auto",
        **kwargs,
    ) -> str:
        """Send images + text prompt through the vision API (async)."""
        messages = [
            {
                "role": "user",
                "content": self._build_vision_content(prompt, image_paths, detail),
            }
        ]
        return await self.acomplete(messages, **kwargs)

    @staticmethod
    def _build_vision_content(
        prompt: str,
        image_paths: list[str],
        detail: str,
    ) -> list[dict]:
        content: list[dict] = []
        for p in image_paths:
            raw = Path(p).read_bytes()
            b64 = base64.b64encode(raw).decode()
            ext = Path(p).suffix.lstrip(".").lower()
            mime = _MIME_MAP.get(ext, "jpeg")
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/{mime};base64,{b64}",
                        "detail": detail,
                    },
                }
            )
        content.append({"type": "text", "text": prompt})
        return content
