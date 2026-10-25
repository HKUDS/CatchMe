"""Orchestrates recorders → working memory, plus the Organizer daemon."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from queue import Empty, Queue

from .config import Config
from .organizer import Organizer
from .recorder import Recorder
from .store import Event, Store

log = logging.getLogger(__name__)


class Engine:
    def __init__(
        self,
        config: Config,
        store: Store,
        recorders: list[Recorder],
    ) -> None:
        self._config = config
        self._store = store
        self._recorders = recorders
        self._queue: Queue[Event] = Queue()
        self._stop = threading.Event()
        self._paused = False
        self.on_event: Callable[[Event], None] | None = None
        self._organizer = Organizer(store, config)

    @property
    def paused(self) -> bool:
        return self._paused

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    # ── Lifecycle ──

    def start(self) -> None:
        self._stop.clear()
        self._writer = threading.Thread(target=self._write_loop, daemon=True)
        self._writer.start()

        self._organizer_thread = threading.Thread(target=self._organizer.run, daemon=True)
        self._organizer_thread.start()

        for rec in self._recorders:
            emitter = self._make_emitter(rec.kind)
            try:
                rec.start(emitter)
                log.info("started recorder: %s", rec.kind)
            except Exception:
                log.exception("failed to start recorder: %s", rec.kind)

    def stop(self) -> None:
        for rec in self._recorders:
            try:
                rec.stop()
            except Exception:
                log.exception("failed to stop recorder: %s", rec.kind)
        self._stop.set()
        self._organizer.stop()
        self._writer.join()
        if hasattr(self, "_organizer_thread"):
            self._organizer_thread.join()
        self._flush()

    # ── Recorder → Working Memory ──

    def _make_emitter(self, kind: str):
        def emit(data: dict, blob: str = "") -> None:
            if self._paused:
                return
            event = Event(timestamp=time.time(), kind=kind, data=data, blob=blob)
            self._queue.put(event)
            self._organizer.on_event(event)
            if self.on_event:
                try:
                    self.on_event(event)
                except Exception:
                    pass

        return emit

    def _write_loop(self) -> None:
        cfg = self._config
        while not self._stop.is_set():
            batch: list[Event] = []
            deadline = time.monotonic() + cfg.batch_timeout
            while len(batch) < cfg.batch_size:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                try:
                    batch.append(self._queue.get(timeout=remaining))
                except Empty:
                    break
            if batch:
                try:
                    self._store.insert_raw(batch)
                except Exception:
                    log.exception("batch write failed (%d events)", len(batch))

    def _flush(self) -> None:
        batch: list[Event] = []
        while not self._queue.empty():
            try:
                batch.append(self._queue.get_nowait())
            except Empty:
                break
        if batch:
            try:
                self._store.insert_raw(batch)
            except Exception:
                log.exception("final flush failed (%d events)", len(batch))
