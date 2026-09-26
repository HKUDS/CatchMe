"""Chrome bookmarks and download indexes across discovered browser profiles."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path


def bookmark_rows(source, cursor):
    rows = []
    for raw in source["paths"]:
        path = Path(raw)
        stat = path.stat()
        signature = f"{stat.st_mtime_ns}:{stat.st_size}"
        if cursor.get(raw) == signature:
            continue
        if stat.st_size > 32 * 1024 * 1024:
            raise ValueError("Bookmark index too large")
        data = json.loads(path.read_text())
        roots = data.get("roots", {})
        if not isinstance(roots, dict):
            raise ValueError("Unknown bookmark format")
        stack = [(v, []) for v in roots.values()]
        visited = 0
        while stack:
            node, parents = stack.pop()
            visited += 1
            if visited > 20000:
                raise ValueError("Bookmark count limit exceeded")
            if not isinstance(node, dict):
                continue
            url, title = node.get("url"), str(node.get("name", ""))
            if node.get("type") == "url" and isinstance(url, str):
                payload = {
                    "url": url,
                    "folder": " / ".join(parents),
                    "profile": path.parent.name,
                    "meaning": "Chrome 本地书签快照，时间为索引更新时间。",
                }
                key = hashlib.sha256(
                    f"{raw}:{node.get('id')}:{url}:{title}:{parents}".encode()
                ).hexdigest()
                rows.append((key, stat.st_mtime, "Chrome", "bookmark", title or url, payload))
            children = node.get("children", [])
            if isinstance(children, list):
                stack.extend((child, [*parents, title]) for child in children)
        cursor[raw] = signature
    return rows


def download_rows(source, cursor):
    rows = []
    for raw in source["paths"]:
        path = Path(raw)
        with path.open("rb") as handle:
            handle.read(16)
        db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=2)
        try:
            if not db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='downloads'"
            ).fetchone():
                continue
            columns = {r[1] for r in db.execute("PRAGMA table_info(downloads)")}
            if not {"id", "start_time", "target_path"}.issubset(columns):
                raise ValueError("Unknown Chrome download format")
            state = "state" if "state" in columns else "NULL"
            received = "received_bytes" if "received_bytes" in columns else "NULL"
            urls = bool(
                db.execute(
                    "SELECT 1 FROM sqlite_master WHERE name='downloads_url_chains'"
                ).fetchone()
            )
            # Revisit IDs to notice completion/state changes, including equal timestamps.
            for rid, started, target, status, size in db.execute(
                f"SELECT id,start_time,target_path,{state},{received} FROM downloads ORDER BY id DESC LIMIT 5000"
            ):
                url_row = (
                    db.execute(
                        "SELECT url FROM downloads_url_chains WHERE id=? ORDER BY chain_index DESC LIMIT 1",
                        (rid,),
                    ).fetchone()
                    if urls
                    else None
                )
                url = url_row[0] if url_row else ""
                signature = f"{started}:{target}:{status}:{size}:{url}"
                key = f"{raw}:{rid}"
                if cursor.get(key) == signature:
                    continue
                cursor[key] = signature
                rows.append(
                    (
                        hashlib.sha256(f"{key}:{signature}".encode()).hexdigest(),
                        started / 1e6 - 11644473600,
                        "Chrome",
                        "download",
                        Path(target).name or url,
                        {
                            "file": target,
                            "url": url,
                            "size": size,
                            "state": status,
                            "profile": path.parent.name,
                            "meaning": "Chrome 下载索引中的状态；不保证文件目前仍存在。",
                        },
                    )
                )
        finally:
            db.close()
    return rows
