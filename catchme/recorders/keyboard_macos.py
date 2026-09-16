"""Keyboard recorder for macOS — CGEventTap + AX text monitor, IME-aware.

Design principle (universal approach):
  Don't capture text at the keystroke level.
  Capture at the text-field level via accessibility APIs,
  and only emit *committed* text (after IME processing).

CGEventTap  → shortcuts & special keys only (never printable chars)
AX monitor  → committed text diffs (composing state detected via
              AXMarkedTextRange + zero-width-space heuristic)
"""

from __future__ import annotations

import threading
import time

import Quartz
from AppKit import NSEvent
from ApplicationServices import (
    AXUIElementCopyAttributeValue,
    AXUIElementCreateSystemWide,
)

from ..recorder import Emit
from .textdiff import diff_added, has_non_ascii

_KEYCODE_NAMES = {
    36: "enter",
    48: "tab",
    49: "space",
    51: "backspace",
    53: "escape",
    117: "delete",
    123: "left",
    124: "right",
    125: "down",
    126: "up",
    115: "home",
    119: "end",
    116: "pageup",
    121: "pagedown",
    122: "F1",
    120: "F2",
    99: "F3",
    118: "F4",
    96: "F5",
    97: "F6",
    98: "F7",
    100: "F8",
    101: "F9",
    109: "F10",
    103: "F11",
    111: "F12",
}

_MOD_MASK = (
    Quartz.kCGEventFlagMaskCommand
    | Quartz.kCGEventFlagMaskControl
    | Quartz.kCGEventFlagMaskAlternate
)

_AX_TEXT_WINDOW = 0.5
_ZWS = "\u200b"

# Adaptive AX polling. Each poll pulls the focused field's entire value across
# a process boundary, so polling fast while the user isn't typing taxes the
# foreground app for nothing.
_AX_POLL_ACTIVE = 0.08
_AX_POLL_IDLE = 0.4
_AX_ACTIVE_WINDOW = 2.0


class KeyboardRecorder:
    kind = "keyboard"

    def __init__(self) -> None:
        self._loop = None
        self._running = False
        self._prev_text: str | None = None
        self._prev_element = None
        self._ax_active = False
        self._last_keydown: float = 0.0
        self._composing = False

    def start(self, emit: Emit) -> None:
        self._running = True
        rec = self

        def _on_key(proxy, etype, event, refcon):
            # macOS holds up key delivery until this callback returns, so it has
            # to stay cheap. Read the event with plain CGEvent calls and bail out
            # before the costly NSEvent bridge for ordinary printable keys —
            # those are reported by the AX monitor, not from here.
            try:
                rec._last_keydown = time.monotonic()

                flags = Quartz.CGEventGetFlags(event)
                has_mod = bool(flags & _MOD_MASK)
                keycode = int(
                    Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
                )
                if not has_mod and keycode not in _KEYCODE_NAMES:
                    return event

                ns = NSEvent.eventWithCGEvent_(event)
                if ns is None:
                    return event
                chars = ns.characters() or ""

                if has_mod:
                    name = _KEYCODE_NAMES.get(keycode, chars) if not chars.isprintable() else chars
                    emit({"key": name, "modifiers": _mods(flags, chars), "type": "shortcut"})
                else:
                    emit(
                        {
                            "key": _KEYCODE_NAMES[keycode],
                            "modifiers": _mods(flags, chars),
                            "type": "special",
                        }
                    )
            except Exception:
                pass
            return event

        def _run_tap():
            tap = Quartz.CGEventTapCreate(
                Quartz.kCGSessionEventTap,
                Quartz.kCGHeadInsertEventTap,
                Quartz.kCGEventTapOptionListenOnly,
                1 << Quartz.kCGEventKeyDown,
                _on_key,
                None,
            )
            if tap is None:
                return
            src = Quartz.CFMachPortCreateRunLoopSource(None, tap, 0)
            self._loop = Quartz.CFRunLoopGetCurrent()
            Quartz.CFRunLoopAddSource(self._loop, src, Quartz.kCFRunLoopDefaultMode)
            Quartz.CGEventTapEnable(tap, True)
            Quartz.CFRunLoopRun()

        def _run_ax():
            system = AXUIElementCreateSystemWide()
            while self._running:
                try:
                    self._poll_ax(system, emit)
                except Exception:
                    pass
                typing = (time.monotonic() - self._last_keydown) < _AX_ACTIVE_WINDOW
                time.sleep(_AX_POLL_ACTIVE if typing else _AX_POLL_IDLE)

        threading.Thread(target=_run_tap, daemon=True).start()
        threading.Thread(target=_run_ax, daemon=True).start()

    def _poll_ax(self, system, emit: Emit) -> None:
        err, focused = AXUIElementCopyAttributeValue(system, "AXFocusedUIElement", None)
        if err or focused is None:
            self._ax_active = False
            self._prev_text = None
            self._prev_element = None
            self._composing = False
            return

        err, val = AXUIElementCopyAttributeValue(focused, "AXValue", None)
        if err or not isinstance(val, str):
            self._ax_active = False
            self._prev_text = None
            self._prev_element = None
            self._composing = False
            return

        self._ax_active = True

        if self._prev_element is None or not _same_element(focused, self._prev_element):
            self._prev_text = val
            self._prev_element = focused
            self._composing = False
            return

        err, marked = AXUIElementCopyAttributeValue(focused, "AXMarkedTextRange", None)
        if not err and marked is not None:
            self._composing = True
            return

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
            recently_typed = (time.monotonic() - self._last_keydown) < _AX_TEXT_WINDOW
            if recently_typed:
                added = diff_added(self._prev_text, val)
                if added and 0 < len(added) <= 200:
                    emit({"key": added, "modifiers": [], "type": "text"})
        self._prev_text = val

    def stop(self) -> None:
        self._running = False
        if self._loop:
            Quartz.CFRunLoopStop(self._loop)
            self._loop = None


def _mods(flags: int, chars: str) -> list[str]:
    m: list[str] = []
    if flags & Quartz.kCGEventFlagMaskCommand:
        m.append("cmd")
    if flags & Quartz.kCGEventFlagMaskAlternate:
        m.append("alt")
    if flags & Quartz.kCGEventFlagMaskControl:
        m.append("ctrl")
    if (flags & Quartz.kCGEventFlagMaskShift) and (m or not chars.isprintable()):
        m.append("shift")
    return m


def _same_element(a, b) -> bool:
    try:
        return a == b
    except Exception:
        return False
