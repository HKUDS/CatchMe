from __future__ import annotations

import importlib
import sys
import threading
import types
from unittest import mock


def _keyboard_macos_module():
    module_name = "catchme.recorders.keyboard_macos"
    if module_name in sys.modules:
        return sys.modules[module_name]

    quartz = types.ModuleType("Quartz")
    quartz.kCGEventFlagMaskCommand = 1
    quartz.kCGEventFlagMaskControl = 2
    quartz.kCGEventFlagMaskAlternate = 4
    quartz.kCGSessionEventTap = 1
    quartz.kCGHeadInsertEventTap = 2
    quartz.kCGEventTapOptionListenOnly = 4
    quartz.kCGEventKeyDown = 8
    appkit = types.ModuleType("AppKit")
    appkit.NSEvent = mock.Mock()
    application_services = types.ModuleType("ApplicationServices")
    application_services.AXUIElementCopyAttributeValue = mock.Mock()
    application_services.AXUIElementCreateSystemWide = mock.Mock(return_value=object())

    with mock.patch.dict(
        sys.modules,
        {
            "Quartz": quartz,
            "AppKit": appkit,
            "ApplicationServices": application_services,
        },
    ):
        return importlib.import_module(module_name)


def test_stop_waits_for_inflight_accessibility_poll(monkeypatch):
    keyboard_macos = _keyboard_macos_module()
    entered_poll = threading.Event()
    release_poll = threading.Event()
    stop_started = threading.Event()
    stop_returned = threading.Event()
    workers = []
    real_thread = threading.Thread

    monkeypatch.setattr(
        keyboard_macos.Quartz, "CGEventTapCreate", lambda *args: None, raising=False
    )
    monkeypatch.setattr(keyboard_macos, "AXUIElementCreateSystemWide", lambda: object())

    recorder = keyboard_macos.KeyboardRecorder()

    def blocked_poll(_system, _emit):
        entered_poll.set()
        release_poll.wait()

    monkeypatch.setattr(recorder, "_poll_ax", blocked_poll)

    def capture_thread(*args, **kwargs):
        worker = real_thread(*args, **kwargs)
        workers.append((kwargs.get("target").__name__, worker))
        return worker

    monkeypatch.setattr(keyboard_macos.threading, "Thread", capture_thread)
    recorder.start(lambda _event: None)
    assert entered_poll.wait(timeout=2)
    ax_worker = next(worker for target_name, worker in workers if target_name == "_run_ax")

    def stop_recorder():
        stop_started.set()
        recorder.stop()
        stop_returned.set()

    stopper = real_thread(target=stop_recorder, daemon=True)
    stopper.start()
    try:
        assert stop_started.wait(timeout=1)
        assert not stop_returned.wait(timeout=0.05)
    finally:
        release_poll.set()
        stopper.join(timeout=2)

    assert stop_returned.is_set()
    assert not ax_worker.is_alive()


def test_stop_during_event_tap_startup_does_not_enter_an_unstoppable_loop(monkeypatch):
    keyboard_macos = _keyboard_macos_module()
    enabled = threading.Event()
    release_enable = threading.Event()
    stop_signal = threading.Event()
    release_legacy_loop = threading.Event()
    quartz = keyboard_macos.Quartz
    monkeypatch.setattr(quartz, "CGEventTapCreate", lambda *args: object(), raising=False)
    monkeypatch.setattr(
        quartz, "CFMachPortCreateRunLoopSource", lambda *args: object(), raising=False
    )
    monkeypatch.setattr(quartz, "CFRunLoopGetCurrent", lambda: object(), raising=False)
    monkeypatch.setattr(quartz, "CFRunLoopAddSource", lambda *args: None, raising=False)
    monkeypatch.setattr(quartz, "kCFRunLoopDefaultMode", "default", raising=False)
    monkeypatch.setattr(quartz, "kCFRunLoopRunFinished", 1, raising=False)
    monkeypatch.setattr(quartz, "CFRunLoopStop", lambda loop: stop_signal.set(), raising=False)
    monkeypatch.setattr(
        quartz, "CFRunLoopRun", lambda: release_legacy_loop.wait(timeout=2), raising=False
    )
    monkeypatch.setattr(
        quartz,
        "CFRunLoopRunInMode",
        lambda mode, seconds, once: release_legacy_loop.wait(timeout=seconds),
        raising=False,
    )

    def enable_tap(*args):
        enabled.set()
        release_enable.wait()

    monkeypatch.setattr(quartz, "CGEventTapEnable", enable_tap, raising=False)
    monkeypatch.setattr(keyboard_macos, "AXUIElementCreateSystemWide", lambda: object())
    monkeypatch.setattr(keyboard_macos, "_AX_POLL_IDLE", 0.01)
    recorder = keyboard_macos.KeyboardRecorder()
    monkeypatch.setattr(recorder, "_poll_ax", lambda *args: None)
    recorder.start(lambda event: None)
    assert enabled.wait(timeout=1)
    stopped = threading.Event()

    def stop_recorder():
        recorder.stop()
        stopped.set()

    stopper = threading.Thread(target=stop_recorder, daemon=True)
    stopper.start()
    try:
        assert stop_signal.wait(timeout=1)
        release_enable.set()
        assert stopped.wait(timeout=0.5)
    finally:
        release_enable.set()
        release_legacy_loop.set()
        stopper.join(timeout=2)
    assert all(not worker.is_alive() for worker in recorder._threads)
