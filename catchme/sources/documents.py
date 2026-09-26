"""App-owned recent-document and project indexes; never reads document contents."""

from __future__ import annotations

import hashlib
import json
import plistlib
import sqlite3
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlparse


def stamp(value, fallback):
    if isinstance(value, datetime):
        return value.replace(tzinfo=value.tzinfo or UTC).timestamp()
    if isinstance(value, (float, int)) and value > 0:
        while value > 100_000_000_000:
            value /= 1000
        return float(value)
    return fallback


def observation(source, cursor, origin, key, ts, kind, title, payload):
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
    identity = f"{origin}:{key}"
    signature = f"{ts}:{digest}"
    if cursor.get(identity) == signature:
        return None
    cursor[identity] = signature
    return (
        hashlib.sha256(f"{identity}:{signature}".encode()).hexdigest(),
        ts,
        source["name"],
        kind,
        title,
        {"origin": str(origin), **payload},
    )


def office_rows(source, cursor):
    rows = []
    for raw in source["paths"]:
        path = Path(raw)
        if not path.exists():
            continue
        data = plistlib.loads(path.read_bytes())
        if not isinstance(data, dict):
            raise ValueError("Office bookmark schema changed")
        for url, entry in data.items():
            if (
                not isinstance(url, str)
                or not url.startswith("file://")
                or not isinstance(entry, dict)
            ):
                continue
            file = unquote(urlparse(url).path)
            used = entry.get("kLastUsedDateKey")
            # Without a per-document date, this is a newly observed bookmark, not an open event.
            ts = stamp(used, 0)
            payload = {
                "file": file,
                "last_used": ts or None,
                "evidence": "Office document bookmark; does not describe edits or cell changes",
            }
            row = observation(
                source, cursor, raw, url, ts, "document_recent", Path(file).name, payload
            )
            if row:
                rows.append((row[0], ts or time.time(), *row[2:]))
    return rows


def editor_rows(source, cursor):
    rows = []
    for raw in source["paths"]:
        path = Path(raw)
        if not path.exists():
            continue
        if path.suffix == ".json":
            data = json.loads(path.read_text())
            entries = data.get("openedPathsList", {}).get("entries", [])
        else:
            db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=2)
            try:
                found = db.execute(
                    "SELECT value FROM ItemTable WHERE key='history.recentlyOpenedPathsList'"
                ).fetchone()
                entries = json.loads(found[0]).get("entries", []) if found else []
            finally:
                db.close()
        if not isinstance(entries, list):
            raise ValueError("Editor history schema changed")
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            workspace = entry.get("workspace", {})
            uri = (
                entry.get("fileUri")
                or entry.get("folderUri")
                or (workspace.get("configPath") if isinstance(workspace, dict) else None)
            )
            if not isinstance(uri, str):
                continue
            file = unquote(urlparse(uri).path) if uri.startswith("file:") else uri
            payload = {
                "uri": uri,
                "file": file,
                "entry_type": "file"
                if entry.get("fileUri")
                else "folder"
                if entry.get("folderUri")
                else "workspace",
                "evidence": "最近打开的文件或工作区索引；时间为发现时间，编辑器未提供准确的打开时间。",
            }
            row = observation(
                source, cursor, raw, uri, 0, "workspace_recent", Path(file).name, payload
            )
            if row:
                rows.append((row[0], time.time(), *row[2:]))
    return rows


def cursor_conversations(source, cursor):
    rows = []
    for raw in source["paths"]:
        path = Path(raw)
        db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=2)
        try:
            # Indexed catalog is small; signatures handle edits and equal timestamps without gaps.
            for origin, scope, cid, title, updated in db.execute(
                "SELECT source,scope,id,title,updated_at FROM conversations"
            ):
                ts = stamp(updated, 0)
                payload = {
                    "conversation_id": cid,
                    "scope": scope,
                    "conversation_source": origin,
                    "title": title,
                    "updated_at": ts,
                    "evidence": "Conversation index; message contents are not included",
                }
                row = observation(
                    source,
                    cursor,
                    raw,
                    f"{origin}:{scope}:{cid}",
                    ts,
                    "conversation_index",
                    title,
                    payload,
                )
                if row:
                    rows.append((row[0], ts or time.time(), *row[2:]))
        finally:
            db.close()
    return rows


def capcut_rows(source, cursor):
    rows = []
    for raw in source["paths"]:
        path = Path(raw)
        if not path.exists():
            continue
        data = json.loads(path.read_text())
        entries = data.get("all_draft_store")
        if not isinstance(entries, list):
            raise ValueError("CapCut project index schema changed")
        for entry in entries:
            if not isinstance(entry, dict) or not entry.get("draft_id"):
                continue
            ts = stamp(entry.get("tm_draft_modified"), 0)
            payload = {
                k: entry.get(k)
                for k in (
                    "draft_id",
                    "draft_name",
                    "draft_fold_path",
                    "tm_draft_create",
                    "tm_draft_modified",
                    "tm_duration",
                    "tm_draft_removed",
                )
            }
            payload["evidence"] = (
                "Project index snapshot; duration is stored in the app native units, not user editing time"
            )
            row = observation(
                source,
                cursor,
                raw,
                entry["draft_id"],
                ts,
                "project_recent",
                str(entry.get("draft_name", "Untitled project")),
                payload,
            )
            if row:
                rows.append((row[0], ts or time.time(), *row[2:]))
    return rows


def resolve_bookmark(data):
    from Foundation import (
        NSURL,
        NSURLBookmarkResolutionWithoutMounting,
        NSURLBookmarkResolutionWithoutUI,
    )

    url, stale, error = (
        NSURL.URLByResolvingBookmarkData_options_relativeToURL_bookmarkDataIsStale_error_(
            data,
            NSURLBookmarkResolutionWithoutUI | NSURLBookmarkResolutionWithoutMounting,
            None,
            None,
            None,
        )
    )
    return str(url.absoluteString()) if url else None


def recent_document_rows(source, cursor):
    """Decode standard macOS per-app shared-file lists without opening apps or documents."""
    rows = []
    for raw in source["paths"]:
        path = Path(raw)
        try:
            data = plistlib.loads(path.read_bytes())
        except FileNotFoundError:
            continue
        if not isinstance(data, dict):
            raise ValueError("Recent-documents schema changed")
        objects = data.get("$objects", [])

        def deref(value, objects=objects):
            return (
                objects[value.data]
                if isinstance(value, plistlib.UID) and value.data < len(objects)
                else value
            )

        for obj in objects:
            if not isinstance(obj, dict):
                continue
            # NSKeyedArchiver dictionaries store keys and values by UID.
            if "NS.keys" in obj and "NS.objects" in obj:
                obj = {
                    deref(k): deref(v)
                    for k, v in zip(obj["NS.keys"], obj["NS.objects"], strict=False)
                    if isinstance(deref(k), str)
                }
            bookmark = deref(obj.get("Bookmark"))
            if not isinstance(bookmark, bytes):
                continue
            uri = resolve_bookmark(bookmark)
            if not uri:
                continue
            title = Path(unquote(urlparse(uri).path)).name or uri
            row = observation(
                source,
                cursor,
                raw,
                uri,
                0,
                "document_recent",
                title,
                {
                    "uri": uri,
                    "evidence": "macOS recent-document snapshot; precise open time unavailable",
                },
            )
            if row:
                rows.append((row[0], time.time(), *row[2:]))
    return rows
