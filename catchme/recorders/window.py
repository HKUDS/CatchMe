"""Active window context: app, title, URL, file path, geometry."""

from __future__ import annotations

from ..config import Config
from ..recorder import Emit, PollingRecorder
from .platform import get_active_window, get_browser_url, get_document_path

_BROWSERS = {
    "safari",
    "google chrome",
    "chrome",
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    "microsoft edge",
    "microsoft-edge",
    "microsoft-edge-stable",
    "msedge",
    "firefox",
    "arc",
    "brave",
    "brave browser",
    "opera",
}
_SYSTEM_IDLE_APPS = {"loginwindow", "screensaverengine", "screensaverenginex"}


def _is_browser(app_name: str) -> bool:
    return app_name.lower().removesuffix(".exe") in _BROWSERS


class WindowRecorder(PollingRecorder):
    kind = "window"
    needs_config = True

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.interval = config.window_interval
        self._prev: dict | None = None

    def poll(self, emit: Emit) -> None:
        info = get_active_window()
        if not info:
            return

        app = info.get("app", "")
        title = info.get("title", "")
        pid = info.get("pid", 0)

        if app.lower() in _SYSTEM_IDLE_APPS:
            return

        data = {
            "app": app,
            "title": title,
            "pid": pid,
            "x": info.get("x", 0),
            "y": info.get("y", 0),
            "w": info.get("w", 0),
            "h": info.get("h", 0),
        }

        if _is_browser(app):
            data["url"] = get_browser_url(app, pid)
        elif title and pid:
            path = get_document_path(pid, title)
            if path:
                data["filepath"] = path

        if data == self._prev:
            return
        self._prev = data
        emit(data)
