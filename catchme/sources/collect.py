"""Bounded readers with durable offsets, deduplication and per-source failure isolation."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

from .catalog import category

MAX_LINE = 8 * 1024 * 1024
SECRET = re.compile(
    r"(?i)(?:\b(?:sk|sk-or-v1)-[a-z0-9_-]{12,}|\bBearer\s+[a-z0-9._-]+|(?:api[_-]?key|password|access_token)\s*[=:]\s*[^\s,;]+)"
)


def redact(value):
    if isinstance(value, str):
        return SECRET.sub("[REDACTED]", value)
    if isinstance(value, dict):
        return {
            k: "[REDACTED]" if re.search(r"(?i)password|secret|token|api.?key", k) else redact(v)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


def timestamp(value, fallback):
    try:
        if isinstance(value, (int, float)):
            return float(value)
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except (ValueError, TypeError, AttributeError):
        return fallback


def transcript(obj, reader):
    """Only conversational text; tool arguments/results and model reasoning are excluded."""
    if reader == "claude":
        msg = obj.get("message", {})
        role = obj.get("type")
        content = msg.get("content", []) if isinstance(msg, dict) else []
    else:
        msg = obj.get("payload", {})
        if (
            obj.get("type") != "response_item"
            or not isinstance(msg, dict)
            or msg.get("type") != "message"
        ):
            return None
        role, content = msg.get("role"), msg.get("content", [])
    if role not in ("user", "assistant"):
        return None
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        text = "\n".join(
            b.get("text", "")
            for b in content
            if isinstance(b, dict)
            and b.get("type") in ("text", "input_text", "output_text")
            and isinstance(b.get("text", ""), str)
        )
    else:
        return None
    if not text.strip():
        return None
    return role, text


def jsonl_rows(source, cursor):
    return read_jsonl(source, cursor)[0]


def read_jsonl(source, cursor):
    """Share a pass budget across files; failed files never discard good checkpoints."""
    import copy

    rows, failures, readable = [], 0, 0
    budget = [16 * 1024 * 1024]
    version = 7 if source.get("full") else 6
    visited = set()
    first_error = None
    for root in source["paths"]:
        try:
            base = Path(root)
            if not base.exists():
                continue
            paths = [base] if base.is_file() else sorted(base.rglob("*.jsonl"))
            if not paths:
                readable += 1
        except OSError as exc:
            first_error = first_error or exc
            failures += 1
            continue
        for path in paths:
            try:
                resolved = str(path.resolve())
                if resolved in visited:
                    continue
                visited.add(resolved)
                checkpoint = copy.deepcopy(cursor.get(str(path), {}))
                file_cursor = {str(path): checkpoint}
                part = _jsonl_file(source, file_cursor, path, budget, version)
                cursor.update(file_cursor)
                rows.extend(part)
                readable += 1
            except OSError as exc:
                first_error = first_error or exc
                failures += 1
            if budget[0] <= 0:
                break
        if budget[0] <= 0:
            break
    if failures and not readable:
        raise first_error
    return rows, failures


def _jsonl_file(source, cursor, path, budget, version):
    from .session_data import metadata, tools_in

    rows = []
    stat = path.stat()
    key = str(path)
    identity = f"{stat.st_dev}:{stat.st_ino}:{getattr(stat, 'st_birthtime', 0)}"
    old = cursor.get(key, {})
    offset = old.get("offset", 0)
    if old.get("identity") != identity or stat.st_size < offset or old.get("version") != version:
        offset = 0
    context = old.get("context", {}) if offset else {}
    discarding = bool(old.get("discarding")) if offset else False
    if stat.st_size == offset:
        return rows
    spent = 0
    with path.open("rb") as f:
        f.seek(offset)
        while spent < 2 * 1024 * 1024 and budget[0] > 0:
            start = f.tell()
            line = f.readline(MAX_LINE + 1)
            if not line:
                break
            if discarding or len(line) > MAX_LINE:
                if not discarding:
                    rows.append(
                        (
                            f"gap:{identity}:{key}:{start}",
                            stat.st_mtime,
                            "Claude Code" if source["reader"] == "claude" else "Codex",
                            "capture_gap",
                            "一条过大的会话记录未导入",
                            {
                                **context,
                                "file": key,
                                "offset": start,
                                "meaning": "这条原始记录超过 8 MiB，可能包含大型附件；已跳过，其他对话继续导入。",
                            },
                        )
                    )
                discarding = not line.endswith(b"\n")
                spent += len(line)
                budget[0] -= len(line)
                offset = f.tell()
                continue
            if not line.endswith(b"\n"):
                break  # Writer has not finished the record; retry next pass.
            spent += len(line)
            budget[0] -= len(line)
            offset = f.tell()
            try:
                obj = json.loads(line)
            except (ValueError, UnicodeDecodeError):
                continue
            if not isinstance(obj, dict):
                continue
            context = metadata(obj, source["reader"], context, path.stem)
            item = transcript(obj, source["reader"])
            if item:
                role, text = item
                external = hashlib.sha256(f"{key}:{identity}:{start}:".encode() + line).hexdigest()
                rows.append(
                    (
                        external,
                        timestamp(obj.get("timestamp"), stat.st_mtime),
                        "Claude Code" if source["reader"] == "claude" else "Codex",
                        "conversation",
                        text[:180],
                        {
                            **context,
                            "role": role,
                            "text": text,
                            "file": key,
                            "offset": start,
                            "evidence": "local_session",
                            "truncated": False,
                        },
                    )
                )
            if source.get("full"):
                for index, (kind, title, payload) in enumerate(tools_in(obj, source["reader"])):
                    external = hashlib.sha256(
                        f"{key}:{identity}:{start}:{kind}:{index}:".encode() + line
                    ).hexdigest()
                    rows.append(
                        (
                            external,
                            timestamp(obj.get("timestamp"), stat.st_mtime),
                            "Claude Code" if source["reader"] == "claude" else "Codex",
                            kind,
                            title[:180],
                            {
                                **context,
                                **payload,
                                "file": key,
                                "offset": start,
                                "evidence": "local_session",
                                "meaning": "会话文件中记录的工具调用或结果；CatchMe 不会执行这些操作。",
                            },
                        )
                    )
    cursor[key] = {
        "identity": identity,
        "offset": offset,
        "context": context,
        "version": version,
        "discarding": discarding,
    }
    return rows


def metadata_rows(source, cursor):
    rows = []
    for root in source["paths"]:
        path = Path(root)
        files = [path] if path.is_file() else path.rglob("*")
        for i, file in enumerate(files):
            if i >= 5000:
                break
            if not file.is_file() or file.is_symlink():
                continue
            stat = file.stat()
            signature = f"{stat.st_mtime_ns}:{stat.st_size}"
            if cursor.get(str(file)) == signature:
                continue
            cursor[str(file)] = signature
            rows.append(
                (
                    str(file) + ":" + signature,
                    stat.st_mtime,
                    source["name"],
                    "file_metadata",
                    file.name,
                    {
                        "file": str(file),
                        "size": stat.st_size,
                        "mtime": stat.st_mtime,
                        "meaning": "File observed/changed; not a user-action log",
                    },
                )
            )
    return rows


def browser_rows(source, cursor):
    rows = []
    for path in source["paths"]:
        # A direct read preserves macOS permission failures instead of flattening them
        # into SQLite's generic "unable to open" error.
        with Path(path).open("rb") as handle:
            handle.read(16)
        # A normal read-only SQLite connection includes committed WAL data.
        # A short read transaction never copies or modifies the application's database.
        db = sqlite3.connect(Path(path).as_uri() + "?mode=ro", uri=True, timeout=2)
        try:
            last = cursor.get(path, 0)
            if source["reader"] == "safari":
                sql = """SELECT v.id, v.visit_time + 978307200, i.url, v.title
                    FROM history_visits v JOIN history_items i ON i.id=v.history_item
                    WHERE v.id>? ORDER BY v.id LIMIT 1000"""
            else:
                sql = """SELECT v.id, v.visit_time / 1000000.0 - 11644473600, u.url, u.title
                    FROM visits v JOIN urls u ON u.id=v.url
                    WHERE v.id>? ORDER BY v.id LIMIT 1000"""
            stat = Path(path).stat()
            identity = f"{stat.st_dev}:{stat.st_ino}"
            if cursor.get(path + ":identity") != identity:
                last = 0
            for row_id, ts, url, title in db.execute(sql, (last,)):
                rows.append(
                    (
                        f"{identity}:{row_id}:{ts}",
                        ts,
                        source["name"].replace(" history", ""),
                        "browser_visit",
                        title or url,
                        {"url": url, "title": title, "profile": Path(path).parent.name},
                    )
                )
                cursor[path] = row_id
            cursor[path + ":identity"] = identity
        finally:
            db.close()
    return rows


def foreground_rows(source, cursor):
    if sys.platform != "darwin":
        raise RuntimeError("macOS required")
    from AppKit import NSWorkspace
    from Quartz import (
        CGEventSourceSecondsSinceLastEventType,
        kCGAnyInputEventType,
        kCGEventSourceStateCombinedSessionState,
    )

    front = NSWorkspace.sharedWorkspace().frontmostApplication()
    if front is None:
        return []
    now = time.time()
    name = str(front.localizedName())
    idle_seconds = CGEventSourceSecondsSinceLastEventType(
        kCGEventSourceStateCombinedSessionState, kCGAnyInputEventType
    )
    return [
        (
            str(int(now // 10)),
            now,
            name,
            "foreground_sample",
            name,
            {
                "bundle_id": str(front.bundleIdentifier() or ""),
                "pid": int(front.processIdentifier()),
                "idle": idle_seconds >= 300,
                "idle_seconds": round(idle_seconds, 1),
            },
        )
    ]


def legacy_rows(source, cursor):
    rows = []
    path = source["paths"][0]
    db = sqlite3.connect(Path(path).as_uri() + "?mode=ro", uri=True, timeout=2)
    try:
        for row_id, ts, kind, data in db.execute(
            "SELECT id,ts,kind,data FROM events_raw WHERE id>? ORDER BY id LIMIT 1000",
            (cursor.get("id", 0),),
        ):
            payload = json.loads(data)
            rows.append(
                (
                    str(row_id),
                    ts,
                    payload.get("app", "CatchMe recorder"),
                    "recorder." + kind,
                    str(payload.get("title") or payload.get("app") or kind),
                    payload,
                )
            )
            cursor["id"] = row_id
    finally:
        db.close()
    return rows


from .chrome import bookmark_rows, download_rows
from .documents import (
    capcut_rows,
    cursor_conversations,
    editor_rows,
    office_rows,
    recent_document_rows,
)
from .safari import plist_rows
from .wechat import file_rows

READERS = {
    "wechat_files": file_rows,
    "chrome_bookmarks": bookmark_rows,
    "chrome_downloads": download_rows,
    "safari_bookmarks": plist_rows,
    "safari_downloads": plist_rows,
    "office": office_rows,
    "editor": editor_rows,
    "cursor_index": cursor_conversations,
    "capcut": capcut_rows,
    "recent_documents": recent_document_rows,
    "claude": jsonl_rows,
    "codex": jsonl_rows,
    "metadata": metadata_rows,
    "safari": browser_rows,
    "chrome": browser_rows,
    "foreground": foreground_rows,
    "legacy": legacy_rows,
}


def read_source(source, cursor):
    """A missing or locked profile must not block other readable locations."""
    import copy

    if source["reader"] in ("claude", "codex"):
        return read_jsonl(source, cursor)

    split_readers = {
        "chrome",
        "safari",
        "chrome_bookmarks",
        "chrome_downloads",
        "safari_bookmarks",
        "safari_downloads",
        "office",
        "editor",
        "cursor_index",
        "capcut",
        "recent_documents",
    }
    if source["reader"] not in split_readers or not source["paths"]:
        return READERS[source["reader"]](source, cursor), 0
    rows, failures, readable = [], 0, 0
    first_error = None
    for raw in source["paths"]:
        try:
            # Missing alternatives are common across versions/installations.
            if not Path(raw).exists():
                continue
            checkpoint = copy.deepcopy(cursor)
            part = READERS[source["reader"]]({**source, "paths": [raw]}, checkpoint)
            cursor.clear()
            cursor.update(checkpoint)
            rows.extend(part)
            readable += 1
        except Exception as exc:
            first_error = first_error or exc
            failures += 1
    if not readable:
        raise first_error or FileNotFoundError("No readable locations")
    return rows, failures


def collect(store):
    # Cross-process exclusion prevents a dashboard and CLI collector racing checkpoints.
    enabled = [
        s for s in store.sources() if s["enabled"] and s["status"] not in ("missing", "unsupported")
    ]
    if not enabled:
        return {"busy": False, "inserted": 0, "errors": {}}
    import fcntl

    with store.path.with_suffix(".lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"busy": True, "inserted": 0}
        total, errors = 0, {}
        for source in enabled:
            try:
                cursor = source["cursor"]
                if source["reader"] in ("claude", "codex"):
                    from .apps import monitoring_settings
                    from .live import full_enabled

                    with store.connect() as db:
                        settings = monitoring_settings(db)
                    source["full"] = full_enabled(settings, source["reader"])
                    source["consented"] = settings.get(source["reader"], {}).get("consented")
                rows, failed_locations = read_source(source, cursor)
                now = time.time()
                inserted = 0
                with store.connect() as db:
                    from .apps import match_app, preferences

                    app_prefs = preferences(db)
                    # Recheck in the write transaction, so a concurrent disable takes effect.
                    if not db.execute(
                        "SELECT enabled FROM sources WHERE id=?", (source["id"],)
                    ).fetchone()[0]:
                        continue
                    for external, ts, app, kind, title, payload in rows:
                        if kind in ("tool_call", "tool_result"):
                            current = monitoring_settings(db)
                            if not full_enabled(current, source["reader"]) or current[
                                source["reader"]
                            ]["consented"] != source.get("consented"):
                                continue
                        owner = match_app(app, payload, source["id"])
                        if (
                            owner
                            and (
                                kind == "foreground_sample"
                                or source["id"] in owner["sources"]
                                or source["reader"] == "legacy"
                            )
                            and not app_prefs[owner["id"]]
                        ):
                            continue
                        if kind == "foreground_sample" and owner is None:
                            continue
                        changed = db.execute(
                            """INSERT OR IGNORE INTO activity
                            (source,external_id,ts,observed,app,category,kind,title,payload)
                            VALUES(?,?,?,?,?,?,?,?,?)""",
                            (
                                source["id"],
                                external,
                                ts,
                                now,
                                app,
                                category(app)
                                if source["category"] == "system"
                                else source["category"],
                                kind,
                                redact(title),
                                json.dumps(redact(payload), ensure_ascii=False),
                            ),
                        ).rowcount
                        if (
                            not changed
                            and source["reader"] in ("claude", "codex")
                            and kind == "conversation"
                        ):
                            db.execute(
                                "UPDATE activity SET payload=? WHERE source=? AND external_id=?",
                                (
                                    json.dumps(redact(payload), ensure_ascii=False),
                                    source["id"],
                                    external,
                                ),
                            )
                        inserted += changed
                    db.execute(
                        "UPDATE sources SET cursor=?,collected=?,error=?,status=? WHERE id=?",
                        (
                            json.dumps(cursor),
                            now,
                            f"{failed_locations} locations unavailable; readable locations collected"
                            if failed_locations
                            else None,
                            "partial" if failed_locations else "available",
                            source["id"],
                        ),
                    )
                total += inserted
            except Exception as exc:
                status = "permission_required" if isinstance(exc, PermissionError) else "error"
                # Avoid surfacing paths, DB values or transcript content in exception messages.
                error = (
                    type(exc).__name__ + ": source could not be read; check permissions and format"
                )
                errors[source["id"]] = error
                with store.connect() as db:
                    db.execute(
                        "UPDATE sources SET status=?,error=? WHERE id=?",
                        (status, error, source["id"]),
                    )
        return {"busy": False, "inserted": total, "errors": errors}
