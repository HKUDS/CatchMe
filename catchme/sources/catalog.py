"""macOS app inventory and explicit, inspectable source capabilities."""

from __future__ import annotations

import plistlib
import re
import sys
import time
from pathlib import Path

from .locations import chrome_files, editor_files, session_roots, unique

# Match both bundle identifiers and display names. Unknown apps remain discoverable.
CATEGORIES = {
    "communication": (
        "wechat",
        "weixin",
        "xinwechat",
        "微信",
        "slack",
        "lark",
        "feishu",
        "飞书",
        "dingtalk",
        "zoom",
        "teams",
    ),
    "development": (
        "cursor",
        "code",
        "vscode",
        "codex",
        "claude",
        "xcode",
        "jetbrains",
        "terminal",
        "iterm",
        "pycharm",
        "intellij",
        "zed",
    ),
    "creative": (
        "adobe",
        "photoshop",
        "premiere",
        "aftereffects",
        "finalcut",
        "final cut",
        "davinci",
        "resolve",
        "capcut",
        "剪映",
        "jianying",
        "figma",
        "blender",
        "affinity",
        "logic",
        "garageband",
    ),
    "office": (
        "word",
        "excel",
        "powerpoint",
        "office",
        "wps",
        "kingsoft",
        "pages",
        "numbers",
        "keynote",
        "notion",
        "obsidian",
        "acrobat",
    ),
    "browser": ("safari", "chrome", "firefox", "edge", "arc", "brave"),
}


def category(name):
    value = name.lower()

    def matches(word):
        if word in {"word", "code", "arc", "edge", "logic", "zed"}:
            return bool(re.search(r"(?:^|[.\s_-])" + word + r"(?:$|[.\s_-])", value))
        return word in value

    return next((k for k, words in CATEGORIES.items() if any(matches(w) for w in words)), "other")


def applications(home: Path):
    result = {}
    roots = [Path("/Applications"), home / "Applications", Path("/System/Applications")]
    for root in roots:
        # Top-level apps and one grouping directory (Utilities, Adobe, etc.).
        for path in sorted([*root.glob("*.app"), *root.glob("*/*.app"), *root.glob("*/*/*.app")]):
            try:
                info = plistlib.loads((path / "Contents/Info.plist").read_bytes())
                name = info.get("CFBundleDisplayName") or info.get("CFBundleName") or path.stem
                key = info.get("CFBundleIdentifier") or str(path)
                result[key] = {
                    "id": key,
                    "name": name,
                    "path": str(path),
                    "category": category(key + " " + name),
                    "version": str(info.get("CFBundleShortVersionString", "")),
                }
            except (OSError, ValueError, plistlib.InvalidFileException):
                continue
    return list(result.values())


def profiles(home: Path):
    return [
        (
            "system.foreground",
            "Foreground applications",
            "system",
            "foreground",
            [],
            "App name, bundle ID and idle state sampled on macOS; no screen or keyboard capture.",
        ),
        (
            "claude.sessions",
            "Claude Code sessions",
            "development",
            "claude",
            session_roots(home, "claude"),
            "Incremental user/assistant text from local JSONL transcripts; may contain private content.",
        ),
        (
            "codex.sessions",
            "Codex sessions",
            "development",
            "codex",
            session_roots(home, "codex"),
            "Incremental user/assistant text from local JSONL transcripts; may contain private content.",
        ),
        (
            "safari.history",
            "Safari history",
            "browser",
            "safari",
            [str(home / "Library/Safari/History.db")],
            "Visited URLs and titles. Full Disk Access may be required.",
        ),
        (
            "chrome.history",
            "Chrome history",
            "browser",
            "chrome",
            chrome_files(home),
            "Visited URLs and titles from all discovered Chrome profiles.",
        ),
    ]


def scan(store, home=None):
    import json

    home = home or Path.home()
    apps = applications(home) if sys.platform == "darwin" else []
    entries = profiles(home)
    entries.extend(
        [
            (
                "chrome.bookmarks",
                "Chrome bookmarks",
                "browser",
                "chrome_bookmarks",
                chrome_files(home, "Bookmarks"),
                "Bookmarks from discovered profiles.",
            ),
            (
                "chrome.downloads",
                "Chrome downloads",
                "browser",
                "chrome_downloads",
                chrome_files(home),
                "Download index and state from discovered profiles.",
            ),
        ]
    )
    for name in ("bookmarks", "downloads"):
        entries.append(
            (
                "safari." + name,
                "Safari " + name,
                "browser",
                "safari_" + name,
                [str(home / "Library/Safari" / (name.title() + ".plist"))],
                "Safari local "
                + name
                + " index; not a guarantee of visits or successful downloads.",
            )
        )
    from .wechat import attachment_roots

    entries.append(
        (
            "wechat.files",
            "WeChat files",
            "communication",
            "wechat_files",
            [str(p) for p in attachment_roots(home)],
            "Attachment names, paths, size and modification time; not message bodies or proof of opening.",
        )
    )
    # Logs are discoverable for every app, but only metadata is collected by this reader.
    log_root = home / "Library/Logs"
    for path in sorted(log_root.glob("*")):
        if path.name.startswith("."):
            continue
        entries.append(
            (
                "logs." + path.name,
                path.name + " logs",
                category(path.name),
                "metadata",
                [str(path)],
                "File size and modification time only; changes do not prove user interaction.",
            )
        )
    office_apps = [
        ("com.microsoft.Excel", "Excel"),
        ("com.microsoft.Word", "Word"),
        ("com.microsoft.Powerpoint", "PowerPoint"),
    ]
    inventory = apps + [
        {"id": bid, "name": name, "category": "office"}
        for bid, name in office_apps
        if not any(a["id"].lower() == bid.lower() for a in apps)
    ]
    for a in inventory:
        bundle = a["id"]
        if bundle.lower() in {
            "com.microsoft.excel",
            "com.microsoft.word",
            "com.microsoft.powerpoint",
        }:
            pref = home / "Library/Containers" / bundle / "Data/Library/Preferences"
            entries.append(
                (
                    "app." + bundle,
                    a["name"],
                    "office",
                    "office",
                    [
                        str(pref / (bundle + ".securebookmarks.plist")),
                        str(home / "Library/Preferences" / (bundle + ".securebookmarks.plist")),
                    ],
                    "Recent document paths and last-used timestamps from Office bookmarks. No document contents or cell edits.",
                )
            )
        elif a["category"] in ("office", "creative"):
            recent = (
                home
                / "Library/Application Support/com.apple.sharedfilelist/com.apple.LSSharedFileList.ApplicationRecentDocuments"
            )
            entries.append(
                (
                    "app." + bundle,
                    a["name"] + " recent documents",
                    a["category"],
                    "recent_documents",
                    [str(recent / (bundle.lower() + suffix)) for suffix in (".sfl3", ".sfl2")],
                    "macOS recent-document references; may require Full Disk Access. Precise open times are not provided.",
                )
            )
        elif a["category"] == "communication":
            entries.append(
                (
                    "app." + bundle,
                    a["name"],
                    a["category"],
                    "inventory",
                    [],
                    "Foreground usage is supported by the system source. This app's message database has no reader yet.",
                )
            )
    for editor in ("Cursor", "Code"):
        paths = editor_files(home, editor)
        entries.append(
            (
                "editor." + editor.lower(),
                "Cursor" if editor == "Cursor" else "Visual Studio Code",
                "development",
                "editor",
                paths["history"],
                "Recent files and workspaces from the editor index. Does not read file contents or terminal history.",
            )
        )
    entries.append(
        (
            "cursor.conversations",
            "Cursor conversations",
            "development",
            "cursor_index",
            editor_files(home, "Cursor")["conversations"],
            "Conversation titles, workspace scope and update times from Cursor's local index.",
        )
    )
    for name, folder in (("CapCut", "CapCut"), ("Jianying", "JianyingPro")):
        roots = [
            home / "Movies" / folder / "User Data/Projects/com.lveditor.draft/root_meta_info.json",
            home
            / "Library/Application Support"
            / folder
            / "User Data/Projects/com.lveditor.draft/root_meta_info.json",
        ]
        entries.append(
            (
                "projects." + name.lower(),
                name + " projects",
                "creative",
                "capcut",
                list(map(str, roots)),
                "Project names, paths, creation/modification timestamps and native duration metadata from the project index.",
            )
        )
    now = time.time()
    with store.connect() as db:
        from .apps import APPS

        overrides = {
            r["id"]: bool(r["enabled"]) for r in db.execute("SELECT * FROM app_preferences")
        }
        custom = {
            r["source"]: json.loads(r["paths"])
            for r in db.execute("SELECT * FROM source_locations")
        }
        selected_sources = {
            sid: overrides[a["id"]] for a in APPS if a["id"] in overrides for sid in a["sources"]
        }
        db.execute("DELETE FROM applications")
        db.executemany("INSERT INTO applications VALUES (:id,:name,:category,:path,:version)", apps)
        db.execute("UPDATE sources SET status='missing', detail='Not found in latest scan'")
        for sid, name, cat, reader, paths, detail in entries:
            paths = unique([*paths, *custom.get(sid, [])])
            status = "available"
            if reader == "inventory":
                status = "unsupported"
            elif reader == "foreground":
                status = "available" if sys.platform == "darwin" else "unsupported"
            else:
                try:
                    found = False
                    denied = False
                    for p in paths:
                        path = Path(p)
                        try:
                            path.stat()
                        except FileNotFoundError:
                            continue
                        except PermissionError:
                            denied = True
                            continue
                        if path.is_dir():
                            next(path.iterdir(), None)
                        else:
                            with path.open("rb") as f:
                                f.read(16)
                        found = True
                    if not found:
                        status = "permission_required" if denied else "missing"
                except PermissionError:
                    status = "permission_required"
                except OSError:
                    status = "unavailable"
            db.execute(
                """INSERT INTO sources(id,name,category,reader,paths,status,detail,checked,enabled)
                VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,
                category=excluded.category, reader=excluded.reader, paths=excluded.paths,
                status=excluded.status, detail=excluded.detail, checked=excluded.checked""",
                (
                    sid,
                    name,
                    cat,
                    reader,
                    json.dumps(paths),
                    status,
                    detail,
                    now,
                    selected_sources.get(sid, False),
                ),
            )
    return {"applications": len(apps), "sources": len(entries)}
