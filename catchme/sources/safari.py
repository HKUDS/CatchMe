"""Safari's local bookmark and download indexes; timestamps describe index evidence."""

from __future__ import annotations

import hashlib
import plistlib
from datetime import UTC, datetime
from pathlib import Path

MAX_PLIST = 32 * 1024 * 1024


def plist_rows(source, cursor):
    rows = []
    for filename in source["paths"]:
        path = Path(filename)
        if not path.exists():
            continue
        stat = path.stat()
        if stat.st_size > MAX_PLIST:
            raise ValueError("Safari index exceeds size limit")
        signature = f"{stat.st_mtime_ns}:{stat.st_size}"
        if cursor.get(filename) == signature:
            continue
        with path.open("rb") as handle:
            value = plistlib.load(handle)
        if not isinstance(value, dict):
            raise ValueError("Unknown Safari index format")
        if source["reader"] == "safari_bookmarks":
            stack = [(value, [])]
            visited = 0
            while stack:
                node, folders = stack.pop()
                visited += 1
                if visited > 20000:
                    raise ValueError("Safari bookmark limit exceeded")
                if not isinstance(node, dict):
                    continue
                uri = node.get("URLString")
                title = (node.get("URIDictionary") or {}).get("title") or node.get("Title") or uri
                if isinstance(uri, str) and uri.startswith(("https://", "http://")):
                    identifier = (
                        node.get("WebBookmarkUUID")
                        or hashlib.sha256((str(folders) + uri).encode()).hexdigest()
                    )
                    payload = {
                        "url": uri,
                        "folder": " / ".join(folders),
                        "evidence": "safari_bookmarks",
                        "meaning": "Safari 本地书签快照，时间为索引更新时间，不代表访问或添加时间。",
                    }
                    rows.append(
                        (
                            f"{identifier}:{uri}:{title}:{folders}",
                            stat.st_mtime,
                            "Safari",
                            "bookmark",
                            str(title)[:500],
                            payload,
                        )
                    )
                children = node.get("Children", [])
                if isinstance(children, list):
                    child_folders = (
                        folders + [node["Title"]] if isinstance(node.get("Title"), str) else folders
                    )
                    stack.extend((child, child_folders) for child in reversed(children))
        else:
            entries = value.get("DownloadHistory", [])
            if not isinstance(entries, list):
                raise ValueError("Unknown Safari downloads format")
            if len(entries) > 20000:
                raise ValueError("Safari download limit exceeded")
            for item in entries:
                if not isinstance(item, dict):
                    continue
                url, file = item.get("DownloadEntryURL"), item.get("DownloadEntryPath")
                if not isinstance(url, str) and not isinstance(file, str):
                    continue
                added = item.get("DownloadEntryDateAdded")
                ts = (
                    added.replace(tzinfo=UTC).timestamp()
                    if isinstance(added, datetime)
                    else stat.st_mtime
                )
                payload = {
                    "url": url if isinstance(url, str) else "",
                    "file": file if isinstance(file, str) else "",
                    "evidence": "safari_downloads",
                    "meaning": "Safari 下载列表中的记录，不保证下载完成或文件仍存在。",
                }
                key = str(item.get("DownloadEntryIdentifier") or f"{url}:{file}:{ts}")
                rows.append(
                    (
                        key,
                        ts,
                        "Safari",
                        "download",
                        Path(file).name if isinstance(file, str) else url[:500],
                        payload,
                    )
                )
        cursor[filename] = signature
    return rows
