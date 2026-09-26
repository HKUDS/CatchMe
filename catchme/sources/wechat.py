"""WeChat attachment metadata. Never opens message databases or file contents."""

from __future__ import annotations

import os
from pathlib import Path


def attachment_roots(home):
    base = home / "Library/Containers/com.tencent.xinWeChat/Data"
    patterns = [
        (base / "Documents/xwechat_files", "*/msg/file"),
        (base / "Library/Application Support/com.tencent.xinWeChat", "*/Message/MessageTemp"),
        (base / "Library/Application Support/com.tencent.xinWeChat", "*/*/Message/MessageTemp"),
        (home / "Documents/xwechat_files", "*/msg/file"),
        (home / "Documents/WeChat Files", "*/FileStorage/File"),
        (home / "Library/Containers/com.tencent.xinWeChat/Data/Documents", "*/FileStorage/File"),
    ]
    roots = []
    for parent, pattern in patterns:
        try:
            roots.extend(p for p in parent.glob(pattern) if p.is_dir() and not p.is_symlink())
        except OSError:
            continue
    return sorted(set(roots))


def file_rows(source, cursor):
    # Persist the traversal queue so a large archive cannot starve later directories.
    queue = cursor.get("queue") or list(source["paths"])
    seen = cursor.setdefault("files", {})
    rows, visited = [], 0
    while queue and visited < 3000:
        folder = Path(queue.pop(0))
        try:
            with os.scandir(folder) as entries:
                for entry in entries:
                    if entry.name.startswith(".") or entry.is_symlink():
                        continue
                    if entry.is_dir(follow_symlinks=False):
                        queue.append(entry.path)
                    elif entry.is_file(follow_symlinks=False):
                        stat = entry.stat(follow_symlinks=False)
                        sig = f"{stat.st_mtime_ns}:{stat.st_size}"
                        if seen.get(entry.path) != sig:
                            seen[entry.path] = sig
                            rows.append(
                                (
                                    entry.path + ":" + sig,
                                    stat.st_mtime,
                                    "微信",
                                    "attachment_available",
                                    entry.name,
                                    {
                                        "file": entry.path,
                                        "size": stat.st_size,
                                        "evidence": "wechat_attachment_directory",
                                        "meaning": "微信文件目录中发现的文件；不代表已打开，也无法据此判断收发方向。",
                                    },
                                )
                            )
                    visited += 1
        except FileNotFoundError:
            continue
    cursor["queue"] = queue
    return rows
