"""Provider diagnostics and model discovery using caller-configured OpenAI-compatible services."""

from __future__ import annotations

import os
import time

from .models import validate_services
from .providers import get_default_api_url


def draft_service(config, data):
    name, settings = data.get("name"), data.get("service", {})
    if not isinstance(name, str) or not name.strip() or not isinstance(settings, dict):
        raise ValueError("Provider name and settings required")
    previous = config.get("services", {}).get(name, {})
    allowed = ("provider", "api_url", "api_key", "api_key_env", "wire_api", "models")
    route = {**previous, **{k: v for k, v in settings.items() if k in allowed}}
    old_url = previous.get("api_url") or get_default_api_url(previous.get("provider", ""))
    new_url = route.get("api_url") or get_default_api_url(route.get("provider", ""))
    if (
        previous
        and new_url != old_url
        and not settings.get("api_key")
        and not settings.get("api_key_env")
        and (
            previous.get("api_key") or previous.get("api_key_env") or previous.get("extra_headers")
        )
    ):
        raise ValueError(
            "The endpoint changed. Enter a credential or explicit environment reference for the new endpoint."
        )
    if old_url != new_url:
        route.pop("extra_headers", None)
        route.pop("api_key", None)
        route.pop("api_key_env", None)
        for key in ("api_key", "api_key_env"):
            if settings.get(key):
                route[key] = settings[key]
    elif not settings.get("api_key"):
        route["api_key"] = previous.get("api_key", "")
    validate_services({name: route}, require_models=False)
    return route


def provider_error(exc):
    status = getattr(exc, "status_code", None)
    messages = {
        401: "Authentication failed. Check the API key or environment variable.",
        403: "Access denied by this provider. Check account and model permissions.",
        404: "Endpoint not found. Check the API base URL; some providers do not expose a model catalog.",
        429: "Provider rate limit or quota reached.",
    }
    if status:
        return {
            "ok": False,
            "status": status,
            "error": messages.get(
                status, f"Provider returned HTTP {status}. Check protocol and model compatibility."
            ),
        }
    return {
        "ok": False,
        "error": "Could not connect to the provider. Check URL, network, TLS, and timeout.",
    }


def probe(route, model=None):
    import httpx
    from openai import OpenAI

    key = (
        os.getenv(route["api_key_env"], "")
        if route.get("api_key_env")
        else route.get("api_key", "")
    )
    if not key and route.get("provider") not in ("ollama", "vllm", "lmstudio"):
        raise ValueError("An API key or a populated credential environment variable is required")
    if model is not None and (not isinstance(model, str) or not model.strip()):
        raise ValueError("Model ID required")
    url = route.get("api_url") or get_default_api_url(route.get("provider", ""))
    start = time.monotonic()
    # Do not forward credentials to redirects or inherit unbounded SDK retries.
    with OpenAI(
        api_key=key or "local",
        base_url=url,
        default_headers=route.get("extra_headers") or None,
        max_retries=0,
        timeout=20,
        http_client=httpx.Client(timeout=20, follow_redirects=False),
    ) as client:
        try:
            if model is None:
                page = client.models.list()
                models = sorted({m.id for m in page.data if isinstance(m.id, str) and m.id})
                return {
                    "ok": True,
                    "models": models,
                    "latency_ms": round((time.monotonic() - start) * 1000),
                    "message": "Provider model catalog is reachable. Test a model to verify generation.",
                }
            if route.get("wire_api") == "responses":
                response = client.responses.create(
                    model=model, input="Reply with OK.", max_output_tokens=64
                )
                answer = response.output_text
            else:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": "Reply with OK."}],
                    max_tokens=64,
                )
                answer = response.choices[0].message.content or ""
            return {
                "ok": bool(answer.strip()),
                "model": model,
                "response": answer[:2000],
                "latency_ms": round((time.monotonic() - start) * 1000),
                "message": "Model returned text."
                if answer.strip()
                else "Request succeeded but produced no text. Reasoning models may need a larger output budget.",
            }
        except Exception as exc:
            return provider_error(exc)
