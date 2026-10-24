"""Activity tree: rule-based hierarchical organization of filtered events.

Two modes:
  time — Day → Session → App → Location → Action
  app  — Day → App → Location → Action

Every level is determined by pure structural/temporal signals. No LLM.
Trees are persisted to JSON for incremental append.
Each node carries a ``summary`` field populated later by summarize.py.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any

from ..store import Event, Store
from .filter import (
    WindowSpan,
    _blob_relative,
    _strip_ime_pinyin,
    build_window_spans,
    cluster_events,
    load_filter_config,
)

_DEFAULT_TREE = {
    "session_gap": 300.0,
    "window_min_dwell": 3.0,
    "action_gap": 3.0,
}


def _get_tree_dir() -> str:
    from ..config import get_default_config

    return str(get_default_config().tree_dir)


# ── Data model ──


@dataclass
class ActivityNode:
    node_id: str
    kind: str  # day | session | app | location | action
    title: str
    start: float
    end: float
    children: list[ActivityNode] = field(default_factory=list)
    context: dict = field(default_factory=dict)
    summary: str = ""

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "node_id": self.node_id,
            "kind": self.kind,
            "title": self.title,
            "start": self.start,
            "end": self.end,
        }
        if self.summary:
            d["summary"] = self.summary
        if self.context:
            d["context"] = self.context
        if self.children:
            d["children"] = [c.to_dict() for c in self.children]
        return d


# ── Public entry point ──


def build_tree(
    store: Store,
    since: float | None = None,
    until: float | None = None,
    mode: str = "time",
    cfg: dict | None = None,
) -> dict:
    """Pure function. mode='time' or 'app'."""
    merged_cfg = {**_DEFAULT_TREE, **(load_filter_config()), **(cfg or {})}
    now = time.time()
    limit = 50_000

    windows = store.query_raw(kind="window", since=since, until=until, limit=limit)
    all_kb = store.query_raw(kind="keyboard", since=since, until=until, limit=limit)
    all_mouse = store.query_raw(kind="mouse", since=since, until=until, limit=limit)
    all_clip = store.query_raw(kind="clipboard", since=since, until=until, limit=limit)
    all_idle = store.query_raw(kind="idle", since=since, until=until, limit=limit)

    spans = build_window_spans(
        windows,
        merged_cfg["window_min_dwell"],
        now=now,
        max_span_dwell=merged_cfg["session_gap"],
    )
    if not spans:
        return {"tree": None, "mode": mode}

    kb_sorted = sorted(all_kb, key=lambda e: e.timestamp)
    mouse_sorted = sorted(all_mouse, key=lambda e: e.timestamp)
    clip_sorted = sorted(all_clip, key=lambda e: e.timestamp)

    interaction = (kb_sorted, mouse_sorted, clip_sorted)
    action_gap = merged_cfg["action_gap"]

    day_start = spans[0].start
    day_end = spans[-1].end
    day_date = time.strftime("%Y-%m-%d", time.localtime(day_start))
    day_id = f"d{day_date.replace('-', '')}"

    if mode == "app":
        root = _build_by_app(day_id, day_date, day_start, day_end, spans, interaction, action_gap)
    else:
        root = _build_by_time(
            day_id,
            day_date,
            day_start,
            day_end,
            spans,
            all_idle,
            merged_cfg["session_gap"],
            interaction,
            action_gap,
        )

    result = {"tree": root.to_dict(), "mode": mode}
    return result


def extend_tree(
    existing: dict,
    store: Store,
    since: float,
    until: float | None = None,
    cfg: dict | None = None,
) -> bool:
    """Incrementally extend *existing* tree dict with events newer than *since*.

    Rebuilds the last session in time mode. In app mode, rebuilds the existing
    date range and merges summaries from the prior tree. Returns True if modified.
    """
    tree = existing.get("tree")
    if not tree or not tree.get("children"):
        return False
    mode = existing.get("mode", "time")
    merged_cfg = {**_DEFAULT_TREE, **(load_filter_config()), **(cfg or {})}
    now = time.time()
    limit = 50_000

    windows = store.query_raw(kind="window", since=since, until=until, limit=limit)
    all_kb = store.query_raw(kind="keyboard", since=since, until=until, limit=limit)
    all_mouse = store.query_raw(kind="mouse", since=since, until=until, limit=limit)
    all_clip = store.query_raw(kind="clipboard", since=since, until=until, limit=limit)

    new_spans = build_window_spans(
        windows,
        merged_cfg["window_min_dwell"],
        now=now,
        max_span_dwell=merged_cfg["session_gap"],
    )
    if not new_spans:
        return False

    kb_sorted = sorted(all_kb, key=lambda e: e.timestamp)
    mouse_sorted = sorted(all_mouse, key=lambda e: e.timestamp)
    clip_sorted = sorted(all_clip, key=lambda e: e.timestamp)
    interaction = (kb_sorted, mouse_sorted, clip_sorted)
    action_gap = merged_cfg["action_gap"]

    if mode == "time":
        return _extend_time_tree(
            tree, new_spans, store, since, until, merged_cfg, interaction, action_gap
        )

    if mode == "app":
        tree_start = tree.get("start", since)
        rebuilt = build_tree(store, since=tree_start, until=until, mode=mode, cfg=merged_cfg)
        new_tree = rebuilt.get("tree")
        if not new_tree:
            return False
        merge_summaries(tree, new_tree)
        existing["tree"] = new_tree
        return True

    return False


def _extend_time_tree(
    tree: dict,
    new_spans: list[WindowSpan],
    store: Store,
    since: float,
    until: float | None,
    cfg: dict,
    interaction: tuple,
    action_gap: float,
) -> bool:
    """Extend a time-mode tree with new spans.

    Strategy: rebuild only the last session (which might still be open) and
    detect whether a new session boundary has appeared.
    """
    day_id = tree.get("node_id", "")
    children = tree.get("children", [])
    if not children:
        return False

    all_idle = store.query_raw(kind="idle", since=since, until=until, limit=50_000)
    session_gap = cfg["session_gap"]

    last_session = children[-1]
    last_end = last_session.get("end", 0)

    gap_to_new = new_spans[0].start - last_end
    idle_breaks = []
    for ev in all_idle:
        d = ev.data
        if d.get("status") in ("idle", "locked"):
            s = d.get("start", ev.timestamp)
            e = d.get("end", ev.timestamp)
            if e - s >= session_gap:
                idle_breaks.append((s, e))

    in_idle = any(s <= last_end and e >= new_spans[0].start for s, e in idle_breaks)

    if gap_to_new >= session_gap or in_idle:
        # New session — close old, create fresh session from new spans
        session_groups = _split_sessions(new_spans, all_idle, session_gap)
        for sess_spans in session_groups:
            s_start = sess_spans[0].start
            s_end = sess_spans[-1].end
            sid = f"{day_id}_s{int(s_start)}"
            sess_dict = ActivityNode(
                node_id=sid,
                kind="session",
                title=f"{_fmt_hm(s_start)} \u2013 {_fmt_hm(s_end)}",
                start=s_start,
                end=s_end,
                context=_session_context(sess_spans),
            )
            sess_dict.children = _build_app_location_children(
                sid, sess_spans, interaction, action_gap
            )
            children.append(sess_dict.to_dict())
        tree["end"] = children[-1]["end"]
    else:
        # Extend the last session — full rebuild of that session's time range
        session_since = last_session.get("start", since)
        all_win = store.query_raw(kind="window", since=session_since, until=until, limit=50_000)
        all_kb2 = store.query_raw(kind="keyboard", since=session_since, until=until, limit=50_000)
        all_ms2 = store.query_raw(kind="mouse", since=session_since, until=until, limit=50_000)
        all_cl2 = store.query_raw(kind="clipboard", since=session_since, until=until, limit=50_000)
        sess_spans = build_window_spans(
            all_win,
            cfg["window_min_dwell"],
            time.time(),
            max_span_dwell=cfg["session_gap"],
        )
        if not sess_spans:
            return False
        inter2 = (
            sorted(all_kb2, key=lambda e: e.timestamp),
            sorted(all_ms2, key=lambda e: e.timestamp),
            sorted(all_cl2, key=lambda e: e.timestamp),
        )
        s_start = sess_spans[0].start
        s_end = sess_spans[-1].end
        sid = f"{day_id}_s{int(s_start)}"
        new_sess = ActivityNode(
            node_id=sid,
            kind="session",
            title=f"{_fmt_hm(s_start)} \u2013 {_fmt_hm(s_end)}",
            start=s_start,
            end=s_end,
            context=_session_context(sess_spans),
        )
        new_sess.children = _build_app_location_children(sid, sess_spans, inter2, action_gap)
        new_dict = new_sess.to_dict()
        # Merge summaries from old last session
        old_index: dict[str, dict] = {}
        _index_tree(last_session, old_index)
        _apply_merge(new_dict, old_index)
        children[-1] = new_dict
        tree["end"] = s_end

    return True


def _apply_merge(node: dict, old_index: dict[str, dict]) -> None:
    """Recursively copy summaries from old_index into node by node_id."""
    nid = node.get("node_id", "")
    old = old_index.get(nid)
    if old:
        if old.get("summary") and not node.get("summary"):
            node["summary"] = old["summary"]
        if old.get("evidence") and not node.get("evidence"):
            node["evidence"] = old["evidence"]
        old_ctx = old.get("context", {})
        new_ctx = node.get("context", {})
        if old_ctx.get("mouse_summaries") and not new_ctx.get("mouse_summaries"):
            new_ctx["mouse_summaries"] = old_ctx["mouse_summaries"]
    for ch in node.get("children", []):
        _apply_merge(ch, old_index)


# ── Persistence ──


def _tree_path(date: str, mode: str) -> str:
    return os.path.join(_get_tree_dir(), f"{date}_{mode}.json")


def save_tree(result: dict) -> str | None:
    """Atomically save tree dict to JSON. Returns path or None."""
    tree = result.get("tree")
    if not tree:
        return None
    mode = result.get("mode", "time")
    date = tree.get("title", "unknown")
    os.makedirs(_get_tree_dir(), exist_ok=True)
    path = _tree_path(date, mode)
    tmp = path + ".tmp"
    meta = {
        "saved_at": time.time(),
        "mode": mode,
        "date": date,
        "tree": tree,
    }
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    return path


def load_tree(date: str, mode: str = "time") -> dict | None:
    """Load persisted tree. Returns {"tree": ..., "mode": ...} or None."""
    path = _tree_path(date, mode)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            meta = json.load(f)
        return {"tree": meta.get("tree"), "mode": meta.get("mode", mode)}
    except (json.JSONDecodeError, OSError):
        return None


def list_saved_trees() -> list[dict]:
    """List all saved tree files with metadata."""
    tree_dir = _get_tree_dir()
    if not os.path.isdir(tree_dir):
        return []
    result = []
    for fname in sorted(os.listdir(tree_dir)):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(tree_dir, fname)
        try:
            with open(path, encoding="utf-8") as f:
                meta = json.load(f)
            result.append(
                {
                    "file": fname,
                    "date": meta.get("date", ""),
                    "mode": meta.get("mode", ""),
                    "saved_at": meta.get("saved_at", 0),
                }
            )
        except (json.JSONDecodeError, OSError):
            continue
    return result


# ── Summary merge across rebuilds ──


def merge_summaries(old_tree: dict, new_tree: dict) -> None:
    """Copy summary, evidence, and mouse_summaries from *old_tree* into *new_tree*.

    Matching is by ``node_id`` only (start time may shift slightly when
    events are re-clustered during extend).
    """
    old_index: dict[str, dict] = {}
    _index_tree(old_tree, old_index)

    def _apply(node: dict) -> None:
        nid = node.get("node_id", "")
        old = old_index.get(nid)
        if old:
            if old.get("summary") and not node.get("summary"):
                node["summary"] = old["summary"]
            if old.get("evidence") and not node.get("evidence"):
                node["evidence"] = old["evidence"]
            old_ctx = old.get("context", {})
            new_ctx = node.get("context", {})
            if old_ctx.get("mouse_summaries") and not new_ctx.get("mouse_summaries"):
                new_ctx["mouse_summaries"] = old_ctx["mouse_summaries"]
        for ch in node.get("children", []):
            _apply(ch)

    _apply(new_tree)


def _index_tree(node: dict, idx: dict) -> None:
    idx[node.get("node_id", "")] = node
    for ch in node.get("children", []):
        _index_tree(ch, idx)


# ── Shared: collect events from spans → cluster → Action nodes ──


def _collect_actions(
    spans: list[WindowSpan],
    parent_id: str,
    interaction: tuple[list[Event], list[Event], list[Event]],
    action_gap: float,
    app: str = "",
    location: str = "",
) -> list[ActivityNode]:
    kb_sorted, mouse_sorted, clip_sorted = interaction
    all_kb: list[Event] = []
    all_mouse: list[Event] = []
    all_clip: list[Event] = []
    for span in spans:
        all_kb.extend(e for e in kb_sorted if span.start <= e.timestamp < span.end)
        all_mouse.extend(e for e in mouse_sorted if span.start <= e.timestamp < span.end)
        all_clip.extend(e for e in clip_sorted if span.start <= e.timestamp < span.end)

    merged = sorted(all_kb + all_mouse + all_clip, key=lambda e: e.timestamp)
    clusters = cluster_events(merged, action_gap)

    return [
        ActivityNode(
            node_id=f"{parent_id}_t{int(c.start)}",
            kind="action",
            title=_derive_action_title(c.events),
            start=c.start,
            end=c.end,
            context=_action_context(c.events, app=app, location=location),
        )
        for ai, c in enumerate(clusters)
    ]


# ── App → Location → Action (shared by time & app modes) ──


def _build_app_location_children(
    id_prefix: str,
    spans: list[WindowSpan],
    interaction: tuple,
    action_gap: float,
) -> list[ActivityNode]:
    """Group spans by app name, then by URL / file / title; one Location node per link."""
    by_app: OrderedDict[str, list[WindowSpan]] = OrderedDict()
    for s in spans:
        by_app.setdefault(s.app, []).append(s)

    app_nodes: list[ActivityNode] = []
    for _ai, (app_name, app_spans) in enumerate(by_app.items()):
        a_start = min(s.start for s in app_spans)
        a_end = max(s.end for s in app_spans)
        total_dwell = sum(s.dwell for s in app_spans)
        aid = f"{id_prefix}_{_sanitize_app(app_name)}"

        app_node = ActivityNode(
            node_id=aid,
            kind="app",
            title=app_name,
            start=a_start,
            end=a_end,
            context={
                "span_count": len(app_spans),
                "total_dwell": round(total_dwell, 1),
            },
        )

        by_loc: OrderedDict[str, list[WindowSpan]] = OrderedDict()
        for s in app_spans:
            loc_key = s.url or s.filepath or s.title
            by_loc.setdefault(loc_key, []).append(s)

        for _li, (loc_key, loc_spans) in enumerate(by_loc.items()):
            lid = f"{aid}_l{_hash_loc(loc_key)}"
            l_start = min(s.start for s in loc_spans)
            l_end = max(s.end for s in loc_spans)
            loc_dwell = sum(s.dwell for s in loc_spans)

            loc_display = loc_key
            if len(loc_display) > 60:
                loc_display = loc_display[:57] + "..."

            loc_node = ActivityNode(
                node_id=lid,
                kind="location",
                title=loc_display,
                start=l_start,
                end=l_end,
                children=_collect_actions(
                    loc_spans,
                    lid,
                    interaction,
                    action_gap,
                    app=app_name,
                    location=loc_key,
                ),
                context={
                    "full_location": loc_key,
                    "span_count": len(loc_spans),
                    "total_dwell": round(loc_dwell, 1),
                },
            )
            app_node.children.append(loc_node)

        app_nodes.append(app_node)

    return app_nodes


# ── Mode: time (Day → Session → App → Location → Action) ──


def _build_by_time(
    day_id: str,
    day_date: str,
    day_start: float,
    day_end: float,
    spans: list[WindowSpan],
    idle_events: list[Event],
    session_gap: float,
    interaction: tuple,
    action_gap: float,
) -> ActivityNode:
    day_node = ActivityNode(
        node_id=day_id,
        kind="day",
        title=day_date,
        start=day_start,
        end=day_end,
    )
    session_groups = _split_sessions(spans, idle_events, session_gap)

    for _si, sess_spans in enumerate(session_groups):
        s_start = sess_spans[0].start
        s_end = sess_spans[-1].end
        sid = f"{day_id}_s{int(s_start)}"

        session_node = ActivityNode(
            node_id=sid,
            kind="session",
            title=f"{_fmt_hm(s_start)} \u2013 {_fmt_hm(s_end)}",
            start=s_start,
            end=s_end,
            context=_session_context(sess_spans),
        )
        session_node.children = _build_app_location_children(
            sid, sess_spans, interaction, action_gap
        )

        day_node.children.append(session_node)

    return day_node


# ── Mode: app (Day → App → Location → Action) ──


def _build_by_app(
    day_id: str,
    day_date: str,
    day_start: float,
    day_end: float,
    spans: list[WindowSpan],
    interaction: tuple,
    action_gap: float,
) -> ActivityNode:
    day_node = ActivityNode(
        node_id=day_id,
        kind="day",
        title=day_date,
        start=day_start,
        end=day_end,
    )
    day_node.children = _build_app_location_children(day_id, spans, interaction, action_gap)
    return day_node


# ── Session splitting ──


def _split_sessions(
    spans: list[WindowSpan],
    idle_events: list[Event],
    gap: float,
) -> list[list[WindowSpan]]:
    if not spans:
        return []

    idle_breaks: list[tuple[float, float]] = []
    for ev in idle_events:
        d = ev.data
        if d.get("status") in ("idle", "locked"):
            start = d.get("start", ev.timestamp)
            end = d.get("end", ev.timestamp)
            if end - start >= gap:
                idle_breaks.append((start, end))

    sessions: list[list[WindowSpan]] = [[spans[0]]]
    for i in range(1, len(spans)):
        prev_end = spans[i - 1].end
        curr_start = spans[i].start
        span_gap = curr_start - prev_end

        in_idle = any(s <= prev_end and e >= curr_start for s, e in idle_breaks)

        if span_gap >= gap or in_idle:
            sessions.append([])
        sessions[-1].append(spans[i])

    return sessions


# ── Action title derivation ──


def _derive_action_title(events: list[Event]) -> str:
    kinds = {e.kind for e in events}
    has_clip = "clipboard" in kinds
    kb_events = [e for e in events if e.kind == "keyboard"]
    mouse_events = [e for e in events if e.kind == "mouse"]

    kb_types = {e.data.get("type") for e in kb_events}
    mouse_actions = {e.data.get("action") for e in mouse_events}

    if has_clip:
        return "copy-paste"
    if "text" in kb_types:
        text = _strip_ime_pinyin(kb_events)
        preview = text[:40].strip()
        return f"typing: {preview}" if preview else f"typing ({len(kb_events)})"
    _scroll_acts = {"scroll", "scroll_start", "scroll_end"}
    if mouse_actions and mouse_actions.issubset(_scroll_acts):
        return "scroll"
    if mouse_actions & {"click", "double_click"}:
        return f"click \u00d7 {len(mouse_events)}"
    if "shortcut" in kb_types:
        keys = ", ".join(e.data.get("key", "") for e in kb_events)
        return f"shortcut: {keys[:40]}"
    return f"interaction \u00d7 {len(events)}"


# ── Context builders ──


def _action_context(events: list[Event], app: str = "", location: str = "") -> dict:
    ctx: dict[str, Any] = {"count": len(events)}
    if app:
        ctx["app"] = app
    if location:
        ctx["location"] = location

    by_kind: dict[str, list[Event]] = {}
    for e in events:
        by_kind.setdefault(e.kind, []).append(e)

    if "keyboard" in by_kind:
        text = _strip_ime_pinyin(by_kind["keyboard"])
        if text:
            ctx["text"] = text
        shortcuts = [
            e.data.get("key", "") for e in by_kind["keyboard"] if e.data.get("type") == "shortcut"
        ]
        if shortcuts:
            ctx["shortcuts"] = shortcuts

    if "mouse" in by_kind:
        ctx["mouse_actions"] = [
            {
                "ts": e.timestamp,
                "action": e.data.get("action", ""),
                "x": e.data.get("x", 0),
                "y": e.data.get("y", 0),
                "full": _blob_relative(e.blob) if e.blob and os.path.exists(e.blob) else None,
                "detail": _blob_relative(e.data["detail"])
                if e.data.get("detail") and os.path.exists(e.data["detail"])
                else None,
            }
            for e in by_kind["mouse"]
        ]

    if "clipboard" in by_kind:
        ctx["clipboard"] = [
            {
                "ts": e.timestamp,
                "type": e.data.get("type", "text"),
                "preview": (e.data.get("content", ""))[:120],
            }
            for e in by_kind["clipboard"]
        ]

    return ctx


def _session_context(spans: list[WindowSpan]) -> dict:
    apps = list(dict.fromkeys(s.app for s in spans))
    urls = list(dict.fromkeys(s.url for s in spans if s.url))
    files = list(dict.fromkeys(s.filepath for s in spans if s.filepath))
    total_dwell = sum(s.dwell for s in spans)
    return {
        "apps": apps,
        "urls": urls[:10],
        "files": files[:10],
        "span_count": len(spans),
        "total_dwell": round(total_dwell, 1),
    }


def _fmt_hm(ts: float) -> str:
    return time.strftime("%H:%M", time.localtime(ts))


# ── Stable node-id helpers ──

_SAFE_RE = re.compile(r"[^a-z0-9]+")


def _sanitize_app(name: str, max_len: int = 24) -> str:
    """Lowercase, strip special chars, truncate — safe for use in a node id."""
    cleaned = _SAFE_RE.sub("_", name.lower()).strip("_")[:max_len]
    if not cleaned:
        cleaned = hashlib.sha1(name.encode("utf-8", errors="replace")).hexdigest()[:12]
    return cleaned


def _hash_loc(key: str) -> str:
    """Short 8-char hex hash of a location key (URL / filepath / title)."""
    return hashlib.sha1(key.encode("utf-8", errors="replace")).hexdigest()[:8]
