from __future__ import annotations

import ctypes
from types import SimpleNamespace

import pytest

from catchme.recorders import idle


@pytest.mark.parametrize(
    ("last_input_tick", "current_tick", "elapsed_ms"),
    [
        (3_000_000_000, 3_000_001_234 - (1 << 32), 1234),
        (0xFFFFFF00, 500, 756),
    ],
)
def test_windows_idle_time_handles_signed_tick_and_wrap(
    monkeypatch, last_input_tick, current_tick, elapsed_ms
):
    def get_last_input_info(info_pointer):
        info = ctypes.cast(info_pointer, ctypes.POINTER(ctypes.c_uint32 * 2)).contents
        info[1] = last_input_tick
        return 1

    fake_windll = SimpleNamespace(
        user32=SimpleNamespace(GetLastInputInfo=get_last_input_info),
        kernel32=SimpleNamespace(GetTickCount=lambda: current_tick),
    )
    monkeypatch.setattr(ctypes, "windll", fake_windll, raising=False)
    monkeypatch.setattr(idle, "_IS_WIN", True)
    monkeypatch.setattr(idle, "_IS_MAC", False)

    assert idle._seconds_since_last_input() == pytest.approx(elapsed_ms / 1000)
