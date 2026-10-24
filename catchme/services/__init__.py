"""Service layer: LLM clients and provider configuration.

Configuration lives at the path returned by ``Config.config_path`` (by
default, ``~/.catchme/config.json``). Load it once with :func:`load_config` and
pass sections to the service constructors, or let them read the file
automatically when no explicit arguments are given.
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_LEGACY_CONFIG_PATH = Path(__file__).resolve().parent / "config.json"


def _get_config_path() -> Path:
    from ..config import get_default_config

    return get_default_config().config_path


_DEFAULTS: dict[str, Any] = {
    "web": {
        "host": "127.0.0.1",
        "port": 8765,
    },
    "llm": {
        "provider": "openai",
        "api_key": "",
        "api_url": None,
        "model": "gpt-4o-mini",
        "max_calls": 0,
        "max_images_per_cluster": 4,
    },
    "filter": {
        "window_min_dwell": 3.0,
        "keyboard_cluster_gap": 3.0,
        "mouse_cluster_gap": 3.0,
    },
    "summarize": {
        "language": "en",
        "max_tokens_l0": 256,
        "max_tokens_l1": 400,
        "max_tokens_l2": 600,
        "max_tokens_l3": 1000,
        "temperature": 0.3,
    },
    "retrieve": {
        "max_prompt_chars": 42000,
        "max_iterations": 15,
        "max_file_chars": 8000,
        "max_select_nodes": 5,
        "max_tokens_step": 800,
        "max_tokens_answer": 2000,
        "temperature_select": 0.3,
        "temperature_answer": 0.7,
    },
}

_cached_config: dict[str, Any] | None = None


def _migrate_legacy_llm(cfg: dict[str, Any]) -> None:
    """Migrate old ``llm.base_url`` to ``llm.api_url``."""
    llm = cfg.get("llm", {})
    if "base_url" in llm and "api_url" not in llm:
        llm["api_url"] = llm.pop("base_url")
    elif "base_url" in llm:
        llm.pop("base_url")


def load_config(path: str | Path | None = None, *, reload: bool = False) -> dict[str, Any]:
    """Read ``config.json`` and return a merged dict (file values + defaults).

    Results are cached; pass *reload=True* to force a re-read.

    On first run, if the config file does not exist at the default path
    (``~/.catchme/config.json``) but the legacy package-local path
    (``services/config.json``) exists, it is automatically migrated.
    """
    global _cached_config
    if _cached_config is not None and not reload:
        return _cached_config

    target = Path(path) if path else _get_config_path()

    if not target.exists() and path is None and _LEGACY_CONFIG_PATH.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(_LEGACY_CONFIG_PATH), str(target))
        log.info("migrated config from %s → %s", _LEGACY_CONFIG_PATH, target)

    cfg: dict[str, Any] = {}
    if target.exists():
        try:
            cfg = json.loads(target.read_text("utf-8"))
        except Exception:
            log.warning("failed to parse %s, using defaults", target)

    _migrate_legacy_llm(cfg)

    merged: dict[str, Any] = {}
    for section, defaults in _DEFAULTS.items():
        if isinstance(defaults, dict):
            file_section = cfg.get(section, {})
            merged[section] = {**defaults, **file_section}
        else:
            merged[section] = cfg.get(section, defaults)

    _cached_config = merged
    return merged


def save_config(cfg: dict[str, Any], path: str | Path | None = None) -> None:
    """Write *cfg* back to ``config.json``."""
    global _cached_config
    target = Path(path) if path else _get_config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(cfg, indent=4, ensure_ascii=False) + "\n", "utf-8")
    _cached_config = cfg
    log.info("config saved to %s", target)
