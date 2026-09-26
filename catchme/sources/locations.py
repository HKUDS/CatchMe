"""Portable, bounded discovery of app-owned data locations and explicit user additions."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def unique(paths):
    return list(dict.fromkeys(str(Path(p).expanduser()) for p in paths))


def environment_path(name, fallback, environ=None):
    value = (os.environ if environ is None else environ).get(name)
    return Path(value).expanduser() if value else Path(fallback)


def session_roots(home, agent, environ=None):
    if agent == "claude":
        bases = [environment_path("CLAUDE_CONFIG_DIR", home / ".claude", environ), home / ".claude"]
        return unique(base / "projects" for base in bases)
    bases = [environment_path("CODEX_HOME", home / ".codex", environ), home / ".codex"]
    return unique(base / name for base in bases for name in ("sessions", "archived_sessions"))


def user_data_bases(home, platform=None, environ=None):
    platform = platform or sys.platform
    if platform == "darwin":
        return [home / "Library/Application Support"]
    if platform == "win32":
        return [environment_path("APPDATA", home / "AppData/Roaming", environ)]
    return [environment_path("XDG_CONFIG_HOME", home / ".config", environ)]


def editor_files(home, editor, platform=None, environ=None):
    names = [editor, "Code - Insiders"] if editor == "Code" else [editor]
    roots = [
        base / name / "User" for base in user_data_bases(home, platform, environ) for name in names
    ]
    # Portable installations can be supplied as explicit paths in the UI.
    stores = []
    for root in roots:
        stores.append(root / "globalStorage")
        try:
            stores.extend(sorted((root / "profiles").glob("*/globalStorage"))[:100])
        except OSError:
            pass
    return {
        "history": unique(
            p / filename for p in stores for filename in ("state.vscdb", "storage.json")
        ),
        "conversations": unique(p / "conversation-search.db" for p in stores),
    }


def chrome_files(home, filename="History", platform=None, environ=None):
    platform = platform or sys.platform
    if platform == "darwin":
        base = home / "Library/Application Support/Google/Chrome"
    elif platform == "win32":
        base = (
            environment_path("LOCALAPPDATA", home / "AppData/Local", environ)
            / "Google/Chrome/User Data"
        )
    else:
        base = environment_path("XDG_CONFIG_HOME", home / ".config", environ) / "google-chrome"
    bases = [environment_path("CHROME_USER_DATA_DIR", base, environ), base]
    result = []
    for root in dict.fromkeys(bases):
        directories = [root / "Default"]
        try:
            directories.extend(sorted(root.glob("Profile *"))[:100])
            state = root / "Local State"
            if state.is_file() and state.stat().st_size < 8 * 1024 * 1024:
                info = json.loads(state.read_text()).get("profile", {}).get("info_cache", {})
                for name in info:
                    if (
                        isinstance(name, str)
                        and name not in (".", "..")
                        and "/" not in name
                        and "\\" not in name
                    ):
                        directories.append(root / name)
        except (OSError, ValueError, AttributeError):
            pass
        result.extend(p / filename for p in directories)
    return unique(result)


def configured(store, app_id):
    from .apps import definition

    app = definition(app_id)
    with store.connect() as db:
        custom = {
            r["source"]: json.loads(r["paths"])
            for r in db.execute("SELECT * FROM source_locations")
        }
        sources = {r["id"]: dict(r) for r in db.execute("SELECT * FROM sources")}
    return [
        {
            "id": sid,
            "name": sources.get(sid, {}).get("name", sid),
            "reader": sources.get(sid, {}).get("reader"),
            "status": sources.get(sid, {}).get("status", "missing"),
            "detected": [
                p
                for p in json.loads(sources.get(sid, {}).get("paths", "[]"))
                if p not in custom.get(sid, [])
            ],
            "custom": custom.get(sid, []),
        }
        for sid in app["sources"]
        if sid in sources and sources[sid]["reader"] not in ("inventory", "foreground")
    ]


def save_locations(store, app_id, items):
    allowed = {item["id"] for item in configured(store, app_id)}
    if not isinstance(items, dict) or any(sid not in allowed for sid in items):
        raise ValueError("请选择此应用的数据位置")
    normalized = {}
    for sid, paths in items.items():
        if not isinstance(paths, list) or len(paths) > 20:
            raise ValueError("每项最多设置 20 个本地位置")
        result = []
        for value in paths:
            if (
                not isinstance(value, str)
                or not value.strip()
                or len(value) > 4096
                or "\x00" in value
            ):
                raise ValueError("请输入有效的本地路径")
            path = Path(value.strip()).expanduser()
            if not path.is_absolute():
                raise ValueError("请输入绝对路径，或使用 ~/ 开头")
            result.append(str(path))
        normalized[sid] = unique(result)
    with store.connect() as db:
        for sid, paths in normalized.items():
            db.execute(
                "INSERT INTO source_locations(source,paths) VALUES(?,?) ON CONFLICT(source) DO UPDATE SET paths=excluded.paths",
                (sid, json.dumps(paths)),
            )
