"""Windows window APIs via pywin32 / psutil."""

from __future__ import annotations

import os


def get_active_window() -> dict:
    try:
        import win32gui
        import win32process

        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)
        _, pid = win32process.GetWindowThreadProcessId(hwnd)

        import psutil

        app = psutil.Process(pid).name()

        rect = win32gui.GetWindowRect(hwnd)
        return {
            "app": app,
            "title": title,
            "pid": pid,
            "x": rect[0],
            "y": rect[1],
            "w": rect[2] - rect[0],
            "h": rect[3] - rect[1],
        }
    except Exception:
        return {}


def get_browser_url(app_name: str, pid: int) -> str:
    # On Windows, browser URL is obtained via the extension bridge
    return ""


def get_document_path(pid: int, title_hint: str) -> str:
    try:
        import psutil

        proc = psutil.Process(pid)
        hint = title_hint.split(" — ")[0].split(" - ")[0].strip()
        if not hint:
            return ""
        open_files = proc.open_files()
        for f in open_files:
            if os.path.basename(f.path) == hint:
                return f.path
        for f in open_files:
            if hint in os.path.basename(f.path):
                return f.path
    except Exception:
        pass
    return ""
