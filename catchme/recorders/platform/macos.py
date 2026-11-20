"""macOS window APIs via AppKit / Quartz / AppleScript."""

from __future__ import annotations

import os
import subprocess

_URL_SCRIPTS = {
    "safari": 'tell application "Safari" to get URL of front document',
    "google chrome": 'tell application "Google Chrome" to get URL of active tab of front window',
    "microsoft edge": 'tell application "Microsoft Edge" to get URL of active tab of front window',
    "firefox": (
        'tell application "System Events" to tell process "Firefox" '
        'to get value of attribute "AXDocument" of window 1'
    ),
}


def get_active_window() -> dict:
    from AppKit import NSWorkspace
    from Quartz import (
        CGWindowListCopyWindowInfo,
        kCGNullWindowID,
        kCGWindowListOptionOnScreenOnly,
    )

    ws = NSWorkspace.sharedWorkspace()
    app = ws.activeApplication()
    if not app:
        return {}
    app_name = app["NSApplicationName"]
    pid = int(app["NSApplicationProcessIdentifier"])

    wins = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID)
    for w in wins or []:
        if w.get("kCGWindowOwnerPID") == pid and w.get("kCGWindowName"):
            bounds = w.get("kCGWindowBounds", {})
            return {
                "app": app_name,
                "title": w.get("kCGWindowName", ""),
                "pid": pid,
                "x": int(bounds.get("X", 0)),
                "y": int(bounds.get("Y", 0)),
                "w": int(bounds.get("Width", 0)),
                "h": int(bounds.get("Height", 0)),
            }
    return {"app": app_name, "title": "", "pid": pid, "x": 0, "y": 0, "w": 0, "h": 0}


def get_browser_url(app_name: str, pid: int) -> str:
    key = app_name.lower()
    for browser, script in _URL_SCRIPTS.items():
        if browser in key:
            try:
                return subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    text=True,
                    timeout=2,
                ).stdout.strip()
            except Exception:
                return ""
    return ""


def get_document_path(pid: int, title_hint: str) -> str:
    """Resolve absolute file path from window title via Spotlight (mdfind)."""
    filename = title_hint.split(" — ")[0].split(" - ")[0].strip()
    if not filename or "/" in filename or len(filename) > 120:
        return ""
    if "." not in filename:
        return ""

    try:
        result = subprocess.run(
            ["mdfind", "-name", filename, "-count", "-onlyin", os.path.expanduser("~")],
            capture_output=True,
            text=True,
            timeout=2,
        )
        count = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
        if count == 0:
            return ""

        result = subprocess.run(
            ["mdfind", "-name", filename, "-onlyin", os.path.expanduser("~")],
            capture_output=True,
            text=True,
            timeout=3,
        )
        candidates = [p.strip() for p in result.stdout.strip().split("\n") if p.strip()]
        if not candidates:
            return ""

        workspace = ""
        parts = title_hint.split(" — ")
        if len(parts) >= 2:
            workspace = parts[-1].strip()

        exact_matches = [c for c in candidates if os.path.basename(c) == filename]
        for c in exact_matches:
            if workspace and workspace in c:
                return c

        if len(exact_matches) == 1:
            return exact_matches[0]
        if len(exact_matches) > 1:
            return ""
        return candidates[0]
    except Exception:
        return ""
