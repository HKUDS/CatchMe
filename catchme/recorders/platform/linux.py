"""Linux window APIs via xprop/xdotool with psutil fallback helpers."""

from __future__ import annotations

import ast
import os
import shutil
import subprocess


def _run(cmd: list[str], timeout: float = 1.0) -> str:
    """Run a command and return stdout, or empty string on failure."""
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        ).stdout.strip()
    except Exception:
        return ""


def _parse_pid(raw: str) -> int:
    # Example: "_NET_WM_PID(CARDINAL) = 12345"
    if "=" not in raw:
        return 0
    try:
        return int(raw.split("=", 1)[1].strip())
    except Exception:
        return 0


def _parse_name_or_title(raw: str) -> str:
    # Example: "WM_NAME(STRING) = \"Terminal\""
    if "=" not in raw:
        return ""
    val = raw.split("=", 1)[1].strip()
    if val.startswith('"') and val.endswith('"'):
        try:
            return ast.literal_eval(val)
        except (SyntaxError, ValueError):
            return val[1:-1]
    return val


def _window_bounds_xdotool(win_id: str) -> tuple[int, int, int, int]:
    out = _run(["xdotool", "getwindowgeometry", "--shell", win_id], timeout=1.0)
    if not out:
        return 0, 0, 0, 0
    vals: dict[str, int] = {}
    for line in out.splitlines():
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        try:
            vals[k.strip()] = int(v.strip())
        except ValueError:
            continue
    return vals.get("X", 0), vals.get("Y", 0), vals.get("WIDTH", 0), vals.get("HEIGHT", 0)


def _window_name_xdotool(win_id: str) -> str:
    return _run(["xdotool", "getwindowname", win_id], timeout=1.0)


def get_active_window() -> dict:
    """Return active window metadata for X11 sessions.

    Supported path:
    - xdotool available: use getactivewindow + getwindowname + geometry
    - xprop fallback: use _NET_ACTIVE_WINDOW and WM_NAME
    """
    # On most Wayland setups these tools are unavailable or restricted.
    # We fail gracefully and let caller skip emitting events.
    if shutil.which("xdotool"):
        win_id = _run(["xdotool", "getactivewindow"], timeout=1.0)
        if win_id:
            title = _window_name_xdotool(win_id)
            pid_raw = _run(["xprop", "-id", win_id, "_NET_WM_PID"], timeout=1.0)
            pid = _parse_pid(pid_raw)
            app = ""
            if pid:
                try:
                    import psutil

                    app = psutil.Process(pid).name()
                except Exception:
                    app = ""
            x, y, w, h = _window_bounds_xdotool(win_id)
            return {
                "app": app,
                "title": title,
                "pid": pid,
                "x": x,
                "y": y,
                "w": w,
                "h": h,
            }

    if shutil.which("xprop"):
        active = _run(["xprop", "-root", "_NET_ACTIVE_WINDOW"], timeout=1.0)
        # Example: _NET_ACTIVE_WINDOW(WINDOW): window id # 0x4a00007
        if "#" not in active:
            return {}
        win_id = active.split("#", 1)[1].strip()
        if not win_id or win_id == "0x0":
            return {}

        title_raw = _run(["xprop", "-id", win_id, "WM_NAME"], timeout=1.0)
        if not title_raw:
            title_raw = _run(["xprop", "-id", win_id, "_NET_WM_NAME"], timeout=1.0)
        title = _parse_name_or_title(title_raw)

        pid_raw = _run(["xprop", "-id", win_id, "_NET_WM_PID"], timeout=1.0)
        pid = _parse_pid(pid_raw)

        app = ""
        if pid:
            try:
                import psutil

                app = psutil.Process(pid).name()
            except Exception:
                app = ""

        return {
            "app": app,
            "title": title,
            "pid": pid,
            "x": 0,
            "y": 0,
            "w": 0,
            "h": 0,
        }

    return {}


def get_browser_url(app_name: str, pid: int) -> str:
    # Linux browser URL capture is intentionally conservative here.
    # Robust URL extraction generally needs browser extensions / accessibility APIs.
    return ""


def get_document_path(pid: int, title_hint: str) -> str:
    """Best-effort: infer open document path from process open files."""
    if not pid:
        return ""
    hint = title_hint.split(" — ")[0].split(" - ")[0].strip()
    if not hint:
        return ""
    try:
        import psutil

        proc = psutil.Process(pid)
        for f in proc.open_files():
            name = os.path.basename(f.path)
            if hint in name or name in hint:
                return f.path
    except Exception:
        pass
    return ""
