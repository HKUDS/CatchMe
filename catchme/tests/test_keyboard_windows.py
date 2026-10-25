from __future__ import annotations

import sys
import threading

import pytest

if sys.platform != "win32":
    pytest.skip("Windows keyboard recorder", allow_module_level=True)

from catchme.recorders import keyboard_windows


class _FakeListener:
    ident = 123

    def __init__(self) -> None:
        self.stopped = False
        self.joined = False
        self.join_completed = threading.Event()

    def start(self) -> None:
        pass

    def stop(self) -> None:
        self.stopped = True

    def join(self) -> None:
        self.joined = True
        self.join_completed.set()


def test_stop_waits_for_in_flight_uia_poll(monkeypatch):
    listener = _FakeListener()
    monkeypatch.setattr(keyboard_windows.keyboard, "Listener", lambda **_kwargs: listener)
    recorder = keyboard_windows.KeyboardRecorder()
    uia_started = threading.Event()
    release_uia = threading.Event()
    uia_finished = threading.Event()
    stop_started = threading.Event()
    stop_returned = threading.Event()
    emitted: list[dict] = []

    def blocked_uia(emit):
        uia_started.set()
        try:
            release_uia.wait(timeout=5)
            emit({"key": "synthetic", "modifiers": [], "type": "text"})
        finally:
            uia_finished.set()

    monkeypatch.setattr(recorder, "_run_uia", blocked_uia)
    recorder.start(emitted.append)
    assert uia_started.wait(timeout=2)

    def stop_recorder():
        stop_started.set()
        recorder.stop()
        stop_returned.set()

    stop_thread = threading.Thread(target=stop_recorder)
    stop_thread.start()
    assert stop_started.wait(timeout=2)
    listener_joined_before_uia_exit = listener.join_completed.wait(timeout=2)
    stop_returned_before_uia_exit = stop_returned.is_set()

    release_uia.set()
    stop_thread.join(timeout=2)

    assert not stop_thread.is_alive()
    assert listener_joined_before_uia_exit
    assert not stop_returned_before_uia_exit
    assert uia_finished.is_set()
    assert stop_returned.is_set()
    assert listener.stopped
    assert listener.joined
    assert emitted == [{"key": "synthetic", "modifiers": [], "type": "text"}]
