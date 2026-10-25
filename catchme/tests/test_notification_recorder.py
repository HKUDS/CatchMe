from __future__ import annotations

import sys
import threading
import types
from unittest import mock

from catchme.recorders.notification import NotificationRecorder


class _FakeNotification:
    def name(self):
        return "synthetic.test.notification"

    def userInfo(self):
        return {"value": "synthetic"}


class _FakeNSObject:
    @classmethod
    def alloc(cls):
        return cls()

    def init(self):
        return self


def test_stop_waits_for_inflight_notification_callback():
    callback_entered = threading.Event()
    release_callback = threading.Event()
    loop_stop_requested = threading.Event()
    center = types.SimpleNamespace(observer=None)

    def add_observer(observer, *_args):
        center.observer = observer

    foundation = types.ModuleType("Foundation")
    foundation.NSDistributedNotificationCenter = types.SimpleNamespace(
        defaultCenter=lambda: types.SimpleNamespace(
            addObserver_selector_name_object_=add_observer,
            removeObserver_=lambda observer: None,
        )
    )
    foundation.NSObject = _FakeNSObject

    core_foundation = types.ModuleType("CoreFoundation")
    core_foundation.CFRunLoopGetCurrent = lambda: object()
    core_foundation.CFRunLoopStop = lambda _loop: loop_stop_requested.set()

    def run_loop(_mode, _seconds, _return_after_source):
        center.observer.handle_(_FakeNotification())
        loop_stop_requested.wait(timeout=2)

    core_foundation.CFRunLoopRunInMode = run_loop
    core_foundation.kCFRunLoopDefaultMode = "default"
    core_foundation.kCFRunLoopRunFinished = 1

    recorder = NotificationRecorder()

    def blocked_emit(_data):
        callback_entered.set()
        release_callback.wait()

    stopper_started = threading.Event()
    stopper_returned = threading.Event()
    with mock.patch.dict(
        sys.modules,
        {"Foundation": foundation, "CoreFoundation": core_foundation},
    ):
        recorder.start(blocked_emit)
        assert callback_entered.wait(timeout=2)
        worker = recorder._thread

        def stop_recorder():
            stopper_started.set()
            recorder.stop()
            stopper_returned.set()

        stopper = threading.Thread(target=stop_recorder, daemon=True)
        stopper.start()
        try:
            assert stopper_started.wait(timeout=1)
            assert not stopper_returned.wait(timeout=0.05)
        finally:
            release_callback.set()
            stopper.join(timeout=2)
            if worker is not None:
                worker.join(timeout=2)

    assert stopper_returned.is_set()
    assert worker is not None and not worker.is_alive()


def test_stop_between_run_loop_check_and_entry_still_drains():
    entered = threading.Event()
    release_entry = threading.Event()
    stop_requested = threading.Event()
    release_legacy_loop = threading.Event()
    observer_removed = threading.Event()
    foundation = types.ModuleType("Foundation")
    center = types.SimpleNamespace(
        addObserver_selector_name_object_=lambda *args: None,
        removeObserver_=lambda observer: observer_removed.set(),
    )
    foundation.NSDistributedNotificationCenter = types.SimpleNamespace(defaultCenter=lambda: center)
    foundation.NSObject = _FakeNSObject
    core_foundation = types.ModuleType("CoreFoundation")
    core_foundation.CFRunLoopGetCurrent = lambda: object()
    core_foundation.CFRunLoopStop = lambda loop: stop_requested.set()
    core_foundation.kCFRunLoopDefaultMode = "default"
    core_foundation.kCFRunLoopRunFinished = 1

    def run_loop(*args):
        entered.set()
        release_entry.wait()
        # A stop before native run-loop entry is not queued for a future run.
        timeout = args[1] if args else 2
        release_legacy_loop.wait(timeout=timeout)

    core_foundation.CFRunLoopRun = run_loop
    core_foundation.CFRunLoopRunInMode = run_loop
    recorder = NotificationRecorder()
    stopped = threading.Event()

    def stop_recorder():
        recorder.stop()
        stopped.set()

    with mock.patch.dict(
        sys.modules, {"Foundation": foundation, "CoreFoundation": core_foundation}
    ):
        recorder.start(lambda event: None)
        assert entered.wait(timeout=1)
        stopper = threading.Thread(target=stop_recorder, daemon=True)
        stopper.start()
        try:
            assert stop_requested.wait(timeout=1)
            release_entry.set()
            assert stopped.wait(timeout=0.5)
        finally:
            release_entry.set()
            release_legacy_loop.set()
            stopper.join(timeout=2)
    assert observer_removed.is_set()
