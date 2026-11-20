"""Shared utility functions."""

from __future__ import annotations

import os
import stat


def _is_junction(path: str) -> bool:
    isjunction = getattr(os.path, "isjunction", None)
    if isjunction is not None:
        return isjunction(path)
    if os.name != "nt":
        return False
    try:
        attributes = os.lstat(path).st_file_attributes
    except OSError:
        return False
    return bool(attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def dir_size_mb(path: str) -> float:
    """Total size of all files in a directory tree, in megabytes."""
    total = 0
    if not os.path.isdir(path):
        return 0.0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return total / (1024 * 1024)


def file_size_mb(path: str) -> float:
    """Size of a single file in megabytes."""
    try:
        return os.path.getsize(path) / (1024 * 1024)
    except OSError:
        return 0.0
