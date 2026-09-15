"""Shared text-diff helpers for the keyboard recorders.

Both the macOS (Accessibility) and Windows (UI Automation) keyboard recorders
poll the focused text field and extract what changed. That value can be the
*entire* contents of an editor or document, and the polling thread holds the
GIL while the OS keyboard hook is waiting to be serviced — so a slow diff here
surfaces directly as typing lag.

These helpers therefore scan with C-level slice comparisons instead of
per-character Python loops, which keeps the cost flat even on
multi-hundred-KB fields.
"""

from __future__ import annotations


def has_non_ascii(text: str) -> bool:
    """True if *text* contains any codepoint above U+007F."""
    return not text.isascii()


def _common_prefix_len(a: str, b: str) -> int:
    """Length of the longest common prefix of *a* and *b*."""
    hi = min(len(a), len(b))
    if hi == 0 or a[0] != b[0]:
        return 0
    if a[:hi] == b[:hi]:
        return hi
    lo = 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if a[:mid] == b[:mid]:
            lo = mid
        else:
            hi = mid - 1
    return lo


def _common_suffix_len(a: str, b: str, limit: int) -> int:
    """Length of the longest common suffix of *a* and *b*, capped at *limit*."""
    hi = limit
    if hi <= 0 or a[-1] != b[-1]:
        return 0
    if a[-hi:] == b[-hi:]:
        return hi
    lo = 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if a[-mid:] == b[-mid:]:
            lo = mid
        else:
            hi = mid - 1
    return lo


def diff_added(old: str, new: str) -> str:
    """Extract the text that was added when *old* changed into *new*.

    Trims the common prefix and the common suffix, where the suffix is not
    allowed to reach back past the prefix.
    """
    if new.startswith(old):  # plain append — by far the common case while typing
        return new[len(old) :]
    i = _common_prefix_len(old, new)
    limit = min(len(old) - i, len(new) - i)
    s = _common_suffix_len(old, new, limit)
    return new[i : len(new) - s]
