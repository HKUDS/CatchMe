"""Recorder protocol and threaded wrapper."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Protocol, runtime_checkable

log = logging.getLogger(__name__)

Emit = Callable[[dict, str], None]


@runtime_checkable
class Recorder(Protocol):
    kind: str

    def start(self, emit: Emit) -> None: ...
    def stop(self) -> None: ...


class PollingRecorder:
    """Base for recorders that poll on a fixed interval."""

    kind: str = ""
    interval: float = 1.0
    needs_config: bool = False

    def __init__(self) -> None:
        self._stop = threading.Event()
        self._poll_error_logged = False
        self._thread: threading.Thread | None = None

    def start(self, emit: Emit) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, args=(emit,), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        if (
            thread is not None
            and thread is not threading.current_thread()
            and thread.ident is not None
        ):
            thread.join()

    def _loop(self, emit: Emit) -> None:
        while not self._stop.wait(self.interval):
            try:
                self.poll(emit)
            except Exception:
                if not self._poll_error_logged:
                    log.warning(
                        "%s poll error (further errors suppressed)", self.kind, exc_info=True
                    )
                    self._poll_error_logged = True

    def poll(self, emit: Emit) -> None:
        raise NotImplementedError
