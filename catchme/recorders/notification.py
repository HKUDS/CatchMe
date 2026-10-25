"""macOS system notification recorder via NSDistributedNotificationCenter."""

from __future__ import annotations

import threading

from ..recorder import Emit

_BLOCKLIST = frozenset(
    [
        "com.apple.carbon.core.DirectoryNotification",
        "AppleSystemUISoundSettingsChanged",
        "NSWorkspaceCompletedURLMountNotification",
    ]
)


class NotificationRecorder:
    kind = "notification"

    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._emit: Emit | None = None
        self._loop_ref = None
        self._stop_requested = threading.Event()

    def start(self, emit: Emit) -> None:
        self._stop_requested.clear()
        self._emit = emit
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_requested.set()
        try:
            from CoreFoundation import CFRunLoopStop

            if self._loop_ref:
                CFRunLoopStop(self._loop_ref)
        except Exception:
            pass
        thread = self._thread
        if (
            thread is not None
            and thread is not threading.current_thread()
            and thread.ident is not None
        ):
            thread.join()

    def _run(self) -> None:
        from CoreFoundation import (
            CFRunLoopGetCurrent,
            CFRunLoopRunInMode,
            kCFRunLoopDefaultMode,
            kCFRunLoopRunFinished,
        )
        from Foundation import NSDistributedNotificationCenter, NSObject

        recorder = self

        class Observer(NSObject):
            def handle_(self, note):
                name = str(note.name())
                if name in _BLOCKLIST:
                    return
                info = note.userInfo()
                data = {"name": name}
                if info:
                    try:
                        data["info"] = {str(k): str(v) for k, v in info.items()}
                    except Exception:
                        pass
                if recorder._emit:
                    recorder._emit(data)

        center = NSDistributedNotificationCenter.defaultCenter()
        obs = Observer.alloc().init()
        center.addObserver_selector_name_object_(obs, "handle:", None, None)
        self._loop_ref = CFRunLoopGetCurrent()
        try:
            while not self._stop_requested.is_set():
                result = CFRunLoopRunInMode(kCFRunLoopDefaultMode, 0.1, False)
                if result == kCFRunLoopRunFinished:
                    break
        finally:
            center.removeObserver_(obs)
