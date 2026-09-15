"""Keyboard recorder for Windows — pynput key hooks + UI Automation text monitor.

Design mirrors the macOS keyboard recorder:
  pynput Listener  → shortcuts & special keys only (never printable chars)
  UIA text monitor → committed text diffs via Value pattern polling
"""

from __future__ import annotations

import logging
import threading
import time

from pynput import keyboard

from ..recorder import Emit
from .textdiff import diff_added, has_non_ascii

log = logging.getLogger(__name__)

_SPECIAL_KEYS = {
    keyboard.Key.enter: "enter",
    keyboard.Key.tab: "tab",
    keyboard.Key.space: "space",
    keyboard.Key.backspace: "backspace",
    keyboard.Key.esc: "escape",
    keyboard.Key.delete: "delete",
    keyboard.Key.left: "left",
    keyboard.Key.right: "right",
    keyboard.Key.down: "down",
    keyboard.Key.up: "up",
    keyboard.Key.home: "home",
    keyboard.Key.end: "end",
    keyboard.Key.page_up: "pageup",
    keyboard.Key.page_down: "pagedown",
    keyboard.Key.f1: "F1",
    keyboard.Key.f2: "F2",
    keyboard.Key.f3: "F3",
    keyboard.Key.f4: "F4",
    keyboard.Key.f5: "F5",
    keyboard.Key.f6: "F6",
    keyboard.Key.f7: "F7",
    keyboard.Key.f8: "F8",
    keyboard.Key.f9: "F9",
    keyboard.Key.f10: "F10",
    keyboard.Key.f11: "F11",
    keyboard.Key.f12: "F12",
}

_MOD_KEYS = frozenset(
    {
        keyboard.Key.ctrl_l,
        keyboard.Key.ctrl_r,
        keyboard.Key.alt_l,
        keyboard.Key.alt_r,
        keyboard.Key.shift_l,
        keyboard.Key.shift_r,
        keyboard.Key.cmd_l,
        keyboard.Key.cmd_r,
    }
)

_TEXT_WINDOW = 0.5
_ZWS = "\u200b"

# Adaptive UIA polling. Each poll pulls the focused field's entire value over
# COM, so polling fast while the user isn't typing taxes the foreground app
# for nothing.
_UIA_POLL_ACTIVE = 0.08
_UIA_POLL_IDLE = 0.4
_UIA_ACTIVE_WINDOW = 2.0

_UIA_ValuePatternId = 10002


def _init_uia():
    """Initialize Windows UI Automation COM interface.

    Returns (uia, IUIAutomationValuePattern_class) or (None, None).
    """
    try:
        import comtypes
        import comtypes.client

        comtypes.client.GetModule("UIAutomationCore.dll")
        from comtypes.gen.UIAutomationClient import (
            CUIAutomation,
            IUIAutomation,
            IUIAutomationValuePattern,
        )

        uia = comtypes.CoCreateInstance(
            CUIAutomation._reg_clsid_,
            interface=IUIAutomation,
        )
        return uia, IUIAutomationValuePattern
    except Exception:
        log.warning(
            "UI Automation init failed — text field monitoring disabled. "
            "Install comtypes: pip install comtypes",
            exc_info=True,
        )
        return None, None


class KeyboardRecorder:
    kind = "keyboard"

    def __init__(self) -> None:
        self._listener: keyboard.Listener | None = None
        self._running = False
        self._pressed_mods: set = set()
        self._last_keydown: float = 0.0
        self._prev_text: str | None = None
        self._prev_runtime_id: tuple | None = None
        self._composing = False

    def start(self, emit: Emit) -> None:
        self._running = True
        rec = self

        def on_press(key):
            try:
                rec._last_keydown = time.monotonic()
                if key in _MOD_KEYS:
                    rec._pressed_mods.add(key)
                    return

                # Ordinary printable keys are reported by the UIA monitor, so
                # return before doing any modifier bookkeeping for them.
                if not rec._pressed_mods and key not in _SPECIAL_KEYS:
                    return

                mods = _current_mods(rec._pressed_mods)
                has_mod = bool({"ctrl", "alt", "cmd"} & set(mods))

                if has_mod:
                    name = _SPECIAL_KEYS.get(key) or getattr(key, "char", None) or str(key)
                    emit({"key": name, "modifiers": mods, "type": "shortcut"})
                elif key in _SPECIAL_KEYS:
                    emit({"key": _SPECIAL_KEYS[key], "modifiers": mods, "type": "special"})
            except Exception:
                pass

        def on_release(key):
            if key in _MOD_KEYS:
                rec._pressed_mods.discard(key)

        self._listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self._listener.start()

        threading.Thread(target=self._run_uia, args=(emit,), daemon=True).start()

    def _run_uia(self, emit: Emit) -> None:
        """Poll the focused text field for value changes via UI Automation."""
        uia, vp_cls = _init_uia()
        if uia is None:
            return
        while self._running:
            try:
                self._poll_uia(uia, vp_cls, emit)
            except Exception:
                pass
            typing = (time.monotonic() - self._last_keydown) < _UIA_ACTIVE_WINDOW
            time.sleep(_UIA_POLL_ACTIVE if typing else _UIA_POLL_IDLE)

    def _poll_uia(self, uia, vp_cls, emit: Emit) -> None:
        try:
            focused = uia.GetFocusedElement()
        except Exception:
            self._reset_text_state()
            return

        if focused is None:
            self._reset_text_state()
            return

        try:
            pattern = focused.GetCurrentPattern(_UIA_ValuePatternId)
            if pattern is None:
                self._reset_text_state()
                return
            vp = pattern.QueryInterface(vp_cls)
            val = vp.CurrentValue or ""
        except Exception:
            self._reset_text_state()
            return

        try:
            rid = tuple(focused.GetRuntimeId())
        except Exception:
            rid = None

        if self._prev_runtime_id is None or rid != self._prev_runtime_id:
            self._prev_text = val
            self._prev_runtime_id = rid
            self._composing = False
            return

        # Detect IME composing via zero-width-space heuristic
        if self._prev_text is not None and val != self._prev_text:
            added = diff_added(self._prev_text, val)
            if _ZWS in added:
                self._composing = True
                return

        if self._composing:
            if self._prev_text is not None and val != self._prev_text:
                added = diff_added(self._prev_text, val)
                if added and has_non_ascii(added) and _ZWS not in added:
                    emit({"key": added, "modifiers": [], "type": "text"})
                    self._prev_text = val
                    self._composing = False
            else:
                self._composing = False
                self._prev_text = val
            return

        if self._prev_text is not None and val != self._prev_text:
            recently_typed = (time.monotonic() - self._last_keydown) < _TEXT_WINDOW
            if recently_typed:
                added = diff_added(self._prev_text, val)
                if added and 0 < len(added) <= 200:
                    emit({"key": added, "modifiers": [], "type": "text"})
        self._prev_text = val

    def _reset_text_state(self) -> None:
        self._prev_text = None
        self._prev_runtime_id = None
        self._composing = False

    def stop(self) -> None:
        self._running = False
        if self._listener:
            self._listener.stop()


def _current_mods(pressed: set) -> list[str]:
    m: list[str] = []
    if keyboard.Key.cmd_l in pressed or keyboard.Key.cmd_r in pressed:
        m.append("cmd")
    if keyboard.Key.alt_l in pressed or keyboard.Key.alt_r in pressed:
        m.append("alt")
    if keyboard.Key.ctrl_l in pressed or keyboard.Key.ctrl_r in pressed:
        m.append("ctrl")
    if keyboard.Key.shift_l in pressed or keyboard.Key.shift_r in pressed:
        m.append("shift")
    return m
