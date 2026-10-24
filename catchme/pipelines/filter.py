"""Filter & temporal clustering: window spans → keyboard/mouse clusters.

Pure functions. No storage side-effects — computes a filtered view on the fly.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any

from ..store import Event, Store

_DEFAULT_FILTER = {
    "window_min_dwell": 3.0,
    "keyboard_cluster_gap": 3.0,
    "mouse_cluster_gap": 3.0,
}


def load_filter_config() -> dict:
    from ..services import load_config

    cfg = load_config()
    return {**_DEFAULT_FILTER, **cfg.get("filter", {})}


# ── Window spans ──


@dataclass
class WindowSpan:
    app: str
    title: str
    url: str
    filepath: str
    start: float
    end: float
    dwell: float
    briefs: list[WindowSpan] = field(default_factory=list)


def _make_span(ev: Event, end: float) -> WindowSpan:
    d = ev.data
    return WindowSpan(
        app=d.get("app", ""),
        title=d.get("title", ""),
        url=d.get("url", ""),
        filepath=d.get("filepath", ""),
        start=ev.timestamp,
        end=end,
        dwell=end - ev.timestamp,
    )


def build_window_spans(
    events: list[Event],
    min_dwell: float,
    now: float | None = None,
    max_span_dwell: float | None = None,
) -> list[WindowSpan]:
    """Build window spans: filter short dwells, merge same-name adjacents,
    attach filtered-out brief windows to their parent merged span.

    If *max_span_dwell* is set, any span whose dwell exceeds that value is
    capped so that downstream session splitting can detect the real gap.
    """
    if not events:
        return []
    ordered = sorted(events, key=lambda e: e.timestamp)
    now = now or time.time()

    # Phase 1: build all spans (valid + brief)
    # A span is forced valid when:
    #   - it's the last event (currently active window), OR
    #   - it continues the same (app, title) as the most recent valid span
    #     (e.g. A(60s) → B(1s) → A(2s): the second A merges back into A)
    valid: list[WindowSpan] = []
    brief: list[WindowSpan] = []
    last_idx = len(ordered) - 1
    for i, ev in enumerate(ordered):
        end = ordered[i + 1].timestamp if i + 1 < len(ordered) else now
        span = _make_span(ev, end)
        continues_prev = valid and span.app == valid[-1].app and span.title == valid[-1].title
        if i == last_idx or span.dwell >= min_dwell or continues_prev:
            valid.append(span)
        else:
            brief.append(span)

    # Phase 2: merge consecutive valid spans with same (app, title)
    if not valid:
        return []
    merged: list[WindowSpan] = [valid[0]]
    for span in valid[1:]:
        prev = merged[-1]
        if span.app == prev.app and span.title == prev.title:
            prev.end = span.end
            prev.dwell = prev.end - prev.start
        else:
            merged.append(span)

    # Phase 2.5: cap spans that are unreasonably long (indicates sleep/idle).
    # Without this, every span extends to the next event's timestamp, so
    # adjacent spans never have a gap and _split_sessions can't cut.
    if max_span_dwell is not None:
        for span in merged:
            if span.dwell > max_span_dwell:
                span.end = span.start + max_span_dwell
                span.dwell = max_span_dwell

    # Phase 3: attach brief spans to the merged span that owns them.
    # A brief belongs to the merged span whose extended range covers it:
    # from m.start up to (but not including) the next merged span's start.
    # Briefs after the last merged span attach to the last one.
    for b in brief:
        owner = None
        for i, m in enumerate(merged):
            boundary = merged[i + 1].start if i + 1 < len(merged) else float("inf")
            if m.start <= b.start < boundary:
                owner = m
                break
        if owner is not None:
            owner.briefs.append(b)

    return merged


# ── Generic temporal clustering ──


@dataclass
class Cluster:
    start: float
    end: float
    events: list[Event] = field(default_factory=list)


def _mouse_scroll_session_open(events: list[Event]) -> bool:
    """True when there is at least one scroll_start not yet closed by scroll_end.

    Matches recorder semantics (mouse.py): scroll_start opens a session,
    scroll_end closes it. Nested starts increment a balance.
    """
    balance = 0
    for e in events:
        if e.kind != "mouse":
            continue
        act = (e.data.get("action") or "").lower()
        if act == "scroll_start":
            balance += 1
        elif act == "scroll_end":
            balance = max(0, balance - 1)
    return balance > 0


def cluster_events(events: list[Event], gap: float) -> list[Cluster]:
    """Split a sorted event stream into clusters separated by ``gap`` seconds.

    Closure rule (AND semantics):
      A cluster is cut **only** when BOTH conditions are true:
        1. ``dt >= gap``  (time since last event exceeds threshold)
        2. no open scroll session  (every scroll_start has a matching scroll_end)
      If a scroll session is still open, the cluster stays open regardless of dt.
    """
    if not events:
        return []
    ordered = sorted(events, key=lambda e: e.timestamp)
    clusters: list[Cluster] = []
    cur = Cluster(start=ordered[0].timestamp, end=ordered[0].timestamp, events=[ordered[0]])
    for ev in ordered[1:]:
        dt = ev.timestamp - cur.end
        if dt < gap or _mouse_scroll_session_open(cur.events):
            cur.events.append(ev)
            cur.end = ev.timestamp
        else:
            clusters.append(cur)
            cur = Cluster(start=ev.timestamp, end=ev.timestamp, events=[ev])
    clusters.append(cur)
    return clusters


# ── Keyboard cluster → serialisable dict ──

_ZWS = "\u200b"


def _has_cjk(s: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" or "\u3400" <= ch <= "\u4dbf" for ch in s)


def _strip_ime_pinyin(events: list[Event]) -> str:
    """Concatenate text, stripping IME composition fragments.

    IME composing is signalled by a zero-width space (\\u200b) in the key.
    Subsequent pure-ASCII events are pinyin continuations until a CJK commit
    event arrives.
    """
    composing = False
    parts: list[str] = []
    for ev in events:
        key = ev.data.get("key", "")
        if _ZWS in key:
            composing = True
            continue
        if composing:
            if _has_cjk(key):
                parts.append(key)
                composing = False
            continue
        if ev.data.get("type") == "special":
            parts.append(f"<{key}>")
        else:
            parts.append(key)
    return "".join(parts)


def _serialize_keyboard_cluster(c: Cluster) -> dict:
    types_seen: set[str] = set()
    for ev in c.events:
        types_seen.add(ev.data.get("type", "key"))

    text = _strip_ime_pinyin(c.events)

    if len(types_seen) > 1:
        label = "mixed"
    else:
        label = types_seen.pop() if types_seen else "key"

    return {"start": c.start, "end": c.end, "text": text, "type": label, "count": len(c.events)}


# ── Mouse cluster → serialisable dict ──


def _blob_relative(blob_abs: str) -> str:
    """Extract a URL-safe path relative to the blobs directory."""
    normalized = blob_abs.replace("\\", "/")
    marker = "/blobs/"
    idx = normalized.rfind(marker)
    if idx >= 0:
        return normalized[idx + len(marker) :]
    return normalized


def _serialize_mouse_action(ev: Event) -> dict:
    d = ev.data
    action: dict[str, Any] = {
        "ts": ev.timestamp,
        "action": d.get("action", ""),
        "x": d.get("x", 0),
        "y": d.get("y", 0),
    }
    if d.get("button"):
        action["button"] = d["button"]
    if d.get("display"):
        action["display"] = d["display"]
    if ev.blob and os.path.exists(ev.blob):
        action["full"] = _blob_relative(ev.blob)
    if d.get("detail") and os.path.exists(d["detail"]):
        action["detail"] = _blob_relative(d["detail"])
    return action


def _serialize_mouse_cluster(c: Cluster) -> dict:
    return {
        "start": c.start,
        "end": c.end,
        "actions": [_serialize_mouse_action(ev) for ev in c.events],
        "count": len(c.events),
    }


# ── Main entry point ──


def _events_in_range(events: list[Event], start: float, end: float) -> list[Event]:
    return [e for e in events if start <= e.timestamp < end]


def _kb_in_range(events: list[Event], start: float, end: float) -> list[Event]:
    return [
        e for e in events if start <= e.timestamp < end and e.data.get("type") in ("text", "key")
    ]


def _span_data(
    span_start: float,
    span_end: float,
    kb_sorted: list[Event],
    mouse_sorted: list[Event],
    kb_gap: float,
    ms_gap: float,
) -> tuple[list[dict], list[dict]]:
    kb = [
        _serialize_keyboard_cluster(c)
        for c in cluster_events(_kb_in_range(kb_sorted, span_start, span_end), kb_gap)
    ]
    ms = [
        _serialize_mouse_cluster(c)
        for c in cluster_events(_events_in_range(mouse_sorted, span_start, span_end), ms_gap)
    ]
    return kb, ms


def _serialize_clipboard(ev: Event) -> dict:
    d = ev.data
    content = d.get("content", "")
    return {
        "ts": ev.timestamp,
        "type": d.get("type", "text"),
        "preview": content[:120],
    }


def build_filtered(
    store: Store,
    since: float | None = None,
    until: float | None = None,
    cfg: dict | None = None,
) -> dict:
    cfg = cfg or load_filter_config()
    min_dwell = cfg["window_min_dwell"]
    kb_gap = cfg["keyboard_cluster_gap"]
    ms_gap = cfg["mouse_cluster_gap"]

    now = time.time()
    limit = 50_000

    windows = store.query_raw(kind="window", since=since, until=until, limit=limit)
    all_kb = store.query_raw(kind="keyboard", since=since, until=until, limit=limit)
    all_mouse = store.query_raw(kind="mouse", since=since, until=until, limit=limit)
    all_clip = store.query_raw(kind="clipboard", since=since, until=until, limit=limit)

    spans = build_window_spans(windows, min_dwell, now=now)

    kb_sorted = sorted(all_kb, key=lambda e: e.timestamp)
    mouse_sorted = sorted(all_mouse, key=lambda e: e.timestamp)
    clip_sorted = sorted(all_clip, key=lambda e: e.timestamp)

    result_windows: list[dict] = []
    for span in spans:
        kb_clusters, mouse_clusters = _span_data(
            span.start,
            span.end,
            kb_sorted,
            mouse_sorted,
            kb_gap,
            ms_gap,
        )

        clips = [
            _serialize_clipboard(e) for e in _events_in_range(clip_sorted, span.start, span.end)
        ]

        briefs: list[dict] = []
        for b in span.briefs:
            b_kb, b_ms = _span_data(
                b.start,
                b.end,
                kb_sorted,
                mouse_sorted,
                kb_gap,
                ms_gap,
            )
            briefs.append(
                {
                    "app": b.app,
                    "title": b.title,
                    "url": b.url,
                    "filepath": b.filepath,
                    "start": b.start,
                    "end": b.end,
                    "dwell": round(b.dwell, 2),
                    "keyboard": b_kb,
                    "mouse": b_ms,
                }
            )

        result_windows.append(
            {
                "app": span.app,
                "title": span.title,
                "url": span.url,
                "filepath": span.filepath,
                "start": span.start,
                "end": span.end,
                "dwell": round(span.dwell, 2),
                "keyboard": kb_clusters,
                "mouse": mouse_clusters,
                "clipboard": clips,
                "briefs": briefs,
            }
        )

    return {"config": cfg, "windows": result_windows}
