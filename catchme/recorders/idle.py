"""Idle and screen-lock detection — cross-platform (macOS / Windows)."""

from __future__ import annotations

import logging
import sys
import time

from ..config import Config
from ..recorder import Emit, PollingRecorder

log = logging.getLogger(__name__)

_IS_WIN = sys.platform == "win32"
_IS_MAC = sys.platform == "darwin"


# ── Platform helpers ──


def _elapsed_milliseconds(current_tick: int, last_input_tick: int) -> int:
    """Return a wrap-safe difference between DWORD tick values."""
    return (current_tick - last_input_tick) & 0xFFFFFFFF


def _seconds_since_last_input() -> float:
    if _IS_MAC:
        from Quartz.CoreGraphics import (
            CGEventSourceSecondsSinceLastEventType,
            kCGEventSourceStateCombinedSessionState,
        )

        return CGEventSourceSecondsSinceLastEventType(
            kCGEventSourceStateCombinedSessionState, 0xFFFFFFFF
        )

    if _IS_WIN:
        import ctypes
        import ctypes.wintypes

        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.wintypes.UINT),
                ("dwTime", ctypes.wintypes.DWORD),
            ]

        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
            millis = _elapsed_milliseconds(ctypes.windll.kernel32.GetTickCount(), lii.dwTime)
            return millis / 1000.0
        return 0.0

    return 0.0


def _is_screen_locked() -> bool:
    if _IS_MAC:
        try:
            from Quartz import CGSessionCopyCurrentDictionary

            d = CGSessionCopyCurrentDictionary()
            if d and d.get("CGSSessionScreenIsLocked", 0):
                return True
        except Exception:
            pass
        return False

    if _IS_WIN:
        import ctypes

        try:
            hdesk = ctypes.windll.user32.OpenInputDesktop(0, False, 0x0100)
            if hdesk:
                ctypes.windll.user32.CloseDesktop(hdesk)
                return False
            return True
        except Exception:
            pass
        return False

    return False


def _is_display_asleep() -> bool:
    if _IS_MAC:
        import subprocess

        try:
            r = subprocess.run(
                ["ioreg", "-r", "-d", "1", "-n", "IODisplayWrangler"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            out = r.stdout
            if not out:
                return False
            for line in out.splitlines():
                if '"CurrentPowerState"' in line:
                    return "= 4" not in line
            return False
        except Exception:
            return False

    if _IS_WIN:
        # Windows does not expose a simple "display off" query without
        # registering for WM_POWERBROADCAST; treat as not asleep and
        # rely on idle timeout + screen-lock detection instead.
        return False

    return False


def _is_loginwindow_active() -> bool:
    if _IS_MAC:
        try:
            from AppKit import NSWorkspace

            app = NSWorkspace.sharedWorkspace().activeApplication()
            if app:
                name = (app.get("NSApplicationName") or "").lower()
                return name in ("loginwindow", "screensaverengine", "screensaverenginex")
        except Exception:
            pass
        return False

    # On Windows, lock-screen state is already captured by _is_screen_locked.
    return False


# ── Recorder ──


class IdleRecorder(PollingRecorder):
    kind = "idle"
    needs_config = True

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.interval = config.idle_interval
        self._timeout = config.idle_timeout
        self._prev_status: str = ""
        self._status_since: float = 0.0
        self._platform_ok = False
        try:
            if _IS_MAC:
                from Quartz.CoreGraphics import CGEventSourceSecondsSinceLastEventType  # noqa: F401
            elif _IS_WIN:
                import ctypes.wintypes  # noqa: F401
            self._platform_ok = True
        except ImportError:
            log.warning("Platform idle APIs not available — idle detection will be limited.")

    def poll(self, emit: Emit) -> None:
        if _is_screen_locked() or _is_display_asleep() or _is_loginwindow_active():
            status = "locked"
        else:
            idle = _seconds_since_last_input()
            status = "idle" if idle >= self._timeout else "active"

        now = time.time()

        if status != self._prev_status:
            if self._prev_status and self._status_since > 0:
                emit(
                    {
                        "status": self._prev_status,
                        "start": round(self._status_since, 3),
                        "end": round(now, 3),
                        "duration": round(now - self._status_since, 1),
                    }
                )
            self._prev_status = status
            self._status_since = now
