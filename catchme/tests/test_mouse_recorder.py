from __future__ import annotations

from unittest import mock

from catchme.recorders.mouse import MouseRecorder


class _FakeListener:
    ident = 123

    def __init__(self, calls: list[str]) -> None:
        self._calls = calls

    def stop(self) -> None:
        self._calls.append("listener-stop")

    def join(self) -> None:
        self._calls.append("listener-join")


def test_stop_closes_active_scroll_session_after_listener_stops(cfg):
    calls: list[str] = []
    recorder = MouseRecorder(cfg)
    recorder._listener = _FakeListener(calls)
    recorder._scroll_timer = mock.Mock()
    recorder._scroll_timer.cancel.side_effect = lambda: calls.append("timer-cancel")
    recorder._scroll_session_active = True
    recorder._last_scroll_data = {"display": 1, "x": 10, "y": 20, "dy": -1}
    recorder._capture_and_save = mock.Mock(return_value=("", ""))
    emitted: list[dict] = []
    recorder._emit = lambda data, _blob: (calls.append("emit"), emitted.append(data))

    recorder.stop()

    assert calls == ["listener-stop", "listener-join", "timer-cancel", "emit"]
    assert len(emitted) == 1
    assert emitted[0]["action"] == "scroll_end"
    assert recorder._scroll_session_active is False
    recorder._capture_and_save.assert_called_once_with(
        1, 10, 20, "scroll end", {"display": 1, "x": 10, "y": 20, "dy": -1, "action": "scroll_end"}
    )
