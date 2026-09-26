"""Named connection services and explicit model selection, with legacy config support."""

from __future__ import annotations

import copy
import os
from urllib.parse import urlparse

from .providers import get_default_api_url


def validate_services(services, *, require_models=True):
    if not isinstance(services, dict):
        raise ValueError("services must be an object")
    for name, service in services.items():
        if not isinstance(name, str) or not name.strip() or not isinstance(service, dict):
            raise ValueError("Each service needs a name and settings")
        for field in ("provider", "api_url", "api_key", "api_key_env", "wire_api"):
            if field in service and not isinstance(service[field], str):
                raise ValueError(f"{name}.{field} must be text")
        url = service.get("api_url") or get_default_api_url(service.get("provider", ""))
        if not url or urlparse(url).scheme not in ("http", "https") or not urlparse(url).hostname:
            raise ValueError(f"{name} needs a valid HTTP(S) API URL")
        if service.get("wire_api", "completions") not in ("completions", "responses"):
            raise ValueError("Supported protocols: completions, responses (OpenAI-compatible)")
        models = service.get("models", [])
        if (
            not isinstance(models, list)
            or (require_models and not models)
            or any(not isinstance(m, str) or not m.strip() for m in models)
        ):
            raise ValueError(f"{name} needs at least one model ID")
        headers = service.get("extra_headers", {})
        if not isinstance(headers, dict) or any(
            not isinstance(k, str) or not isinstance(v, str) for k, v in headers.items()
        ):
            raise ValueError("extra_headers must map strings to strings")


def resolve_llm(config, service=None, model=None):
    legacy = dict(config.get("llm", {}))
    selected = service or legacy.get("service")
    if not selected:
        return {**legacy, **({"model": model} if model else {})}
    services = config.get("services", {})
    if not isinstance(selected, str):
        raise ValueError("Service name must be text")
    if selected not in services:
        raise ValueError(f"Unknown LLM service: {selected}")
    validate_services({selected: services[selected]})
    route = services[selected]
    chosen = model or legacy.get("model")
    if chosen not in route["models"]:
        raise ValueError(f"Model {chosen!r} is not configured for service {selected}")
    # Never inherit a credential or endpoint from the legacy connection.
    result = {
        k: v
        for k, v in legacy.items()
        if k not in ("provider", "api_key", "api_url", "extra_headers", "wire_api", "api_key_env")
    }
    result.update(route, service=selected, model=chosen)
    if route.get("api_key_env"):
        result["api_key"] = os.environ.get(route["api_key_env"], "")
    return result


def public_config(config):
    services = copy.deepcopy(config.get("services", {}))
    for route in services.values():
        key = route.pop("api_key", "")
        route["has_api_key"] = bool(
            os.getenv(route["api_key_env"], "") if route.get("api_key_env") else key
        )
        # Headers can carry credentials; never echo their values into the browser.
        route.pop("extra_headers", None)
    return {
        "services": services,
        "selection": {k: config.get("llm", {}).get(k, "") for k in ("service", "model")},
        "legacy": not bool(config.get("llm", {}).get("service")),
    }
