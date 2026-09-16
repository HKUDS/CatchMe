"""CatchMe — unified activity recording with memory pipelines.

from catchme import CatchMe

mem = CatchMe()
mem.start()
events = mem.query(kind="window", since=3600)
mem.stop()
"""

from __future__ import annotations

__version__ = "0.2.0"

import time

from .config import Config
from .engine import Engine
from .recorders import ALL
from .store import Event, Store


class CatchMe:
    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config()
        self.config.ensure_dirs()
        self.store = Store(self.config.db_path)
        recorders = [
            cls(self.config) if getattr(cls, "needs_config", False) else cls() for cls in ALL
        ]
        self._engine = Engine(self.config, self.store, recorders)

    @property
    def on_event(self):
        return self._engine.on_event

    @on_event.setter
    def on_event(self, cb):
        self._engine.on_event = cb

    @property
    def paused(self) -> bool:
        return self._engine.paused

    def start(self) -> None:
        self._engine.start()

    def pause(self) -> None:
        self._engine.pause()

    def resume(self) -> None:
        self._engine.resume()

    def stop(self) -> None:
        self._engine.stop()
        self.store.close()

    def query(
        self,
        kind: str | None = None,
        since: float | None = None,
        until: float | None = None,
        limit: int = 500,
    ) -> list[Event]:
        if since is not None and since < 1e9:
            since = time.time() - since
        if until is not None and until < 1e9:
            until = time.time() - until
        return self.store.query_raw(kind=kind, since=since, until=until, limit=limit)

    def search(self, text: str, **kwargs) -> list[Event]:
        return self.store.search(text, **kwargs)

    def timeline(
        self,
        since: float | None = None,
        until: float | None = None,
        limit: int = 1000,
    ) -> list[Event]:
        if since is not None and since < 1e9:
            since = time.time() - since
        return self.store.query_raw(since=since, until=until, limit=limit)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *_):
        self.stop()
