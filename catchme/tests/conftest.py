"""Shared fixtures for catchme test suite."""

from __future__ import annotations

import pytest

from catchme.config import Config
from catchme.store import Event, Store


@pytest.fixture()
def tmp_root(tmp_path):
    """Return a temporary directory suitable as Config.root."""
    return tmp_path / "catchme_data"


@pytest.fixture()
def cfg(tmp_root):
    """A Config instance backed by a temporary directory."""
    c = Config(root=tmp_root)
    c.ensure_dirs()
    return c


@pytest.fixture()
def store(cfg):
    """A Store with an empty SQLite database in a temp directory."""
    s = Store(cfg.db_path)
    yield s
    s.close()


@pytest.fixture()
def sample_events() -> list[Event]:
    """A handful of diverse events for testing queries and filtering."""
    base = 1_700_000_000.0
    return [
        Event(
            timestamp=base,
            kind="window",
            data={
                "app": "Safari",
                "title": "Google",
                "url": "https://google.com",
            },
        ),
        Event(
            timestamp=base + 5,
            kind="window",
            data={
                "app": "Safari",
                "title": "GitHub",
                "url": "https://github.com",
            },
        ),
        Event(
            timestamp=base + 10,
            kind="keyboard",
            data={
                "key": "h",
                "type": "text",
            },
        ),
        Event(
            timestamp=base + 10.1,
            kind="keyboard",
            data={
                "key": "i",
                "type": "text",
            },
        ),
        Event(
            timestamp=base + 12,
            kind="mouse",
            data={
                "action": "click",
                "x": 100,
                "y": 200,
                "button": "left",
            },
        ),
        Event(
            timestamp=base + 20,
            kind="clipboard",
            data={
                "content": "hello world",
                "type": "text",
            },
        ),
        Event(
            timestamp=base + 30,
            kind="window",
            data={
                "app": "Terminal",
                "title": "zsh",
                "url": "",
                "filepath": "",
            },
        ),
        Event(
            timestamp=base + 60,
            kind="idle",
            data={
                "status": "idle",
                "start": base + 50,
                "end": base + 60,
            },
        ),
    ]


def make_window_event(ts: float, app: str, title: str, **extra) -> Event:
    """Helper to quickly build a window event."""
    data = {"app": app, "title": title, "url": "", "filepath": "", **extra}
    return Event(timestamp=ts, kind="window", data=data)


def make_kb_event(ts: float, key: str, typ: str = "text") -> Event:
    return Event(timestamp=ts, kind="keyboard", data={"key": key, "type": typ})


def make_mouse_event(ts: float, action: str = "click", **extra) -> Event:
    return Event(timestamp=ts, kind="mouse", data={"action": action, "x": 0, "y": 0, **extra})


def make_clipboard_event(ts: float, content: str = "copied") -> Event:
    return Event(timestamp=ts, kind="clipboard", data={"content": content, "type": "text"})


@pytest.fixture
def client(tmp_path, monkeypatch):
    import catchme.services as svc
    import catchme.web as web
    from catchme.config import Config

    cfg = Config(root=tmp_path)
    cfg.ensure_dirs()
    monkeypatch.setattr(web, "_config", cfg)
    monkeypatch.setattr(svc, "_get_config_path", lambda: cfg.config_path)
    monkeypatch.setattr(svc, "_LEGACY_CONFIG_PATH", tmp_path / "no-legacy.json")
    monkeypatch.setattr(svc, "_cached_config", None)
    return web.app.test_client()
