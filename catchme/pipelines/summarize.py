"""Hierarchical bottom-up summarization via LLM.

Four levels, each consuming the output of the level below:

  L0  Mouse Cluster  →  vision LLM  →  mouse_summaries (per action)
  L1  Action         →  text   LLM  →  action.summary
  L2  Location       →  text   LLM  →  location.summary
  L3  Session / App  →  text   LLM  →  session.summary / app.summary

Only *closed* nodes (all siblings except the last) are summarized.
The last sibling is the one currently being built by the user.
"""

from __future__ import annotations

import logging
import os
import re
import time
from pathlib import Path
from typing import Any

import yaml

from ..services.llm import LLM, LLMBudgetExhausted
from .filter import load_filter_config
from .tree import load_tree, save_tree

log = logging.getLogger(__name__)


def _get_blob_dir() -> str:
    from ..config import get_default_config

    return str(get_default_config().blob_dir)


# ── Configurable prompts & parameters ──

_PROMPTS_PATH = Path(__file__).resolve().parent.parent / "services" / "prompts.yaml"
_prompts_cache: dict[str, Any] | None = None


def _load_prompts_raw() -> dict[str, Any]:
    global _prompts_cache
    if _prompts_cache is not None:
        return _prompts_cache
    try:
        with open(_PROMPTS_PATH, encoding="utf-8") as f:
            _prompts_cache = yaml.safe_load(f) or {}
    except Exception:
        log.warning("failed to load prompts.yaml, using empty prompts")
        _prompts_cache = {}
    return _prompts_cache


def _load_summary_config() -> dict[str, Any]:
    from ..services import load_config

    return load_config().get("summarize", {})


def _get_prompt(key: str, fallback: str = "") -> str:
    """Resolve a prompt by key, respecting the configured language.

    Supports both the new bilingual format ``{key: {en: ..., zh: ...}}``
    and the legacy flat format ``{key: "..."}`` for backward compatibility.
    """
    prompts = _load_prompts_raw()
    lang = _load_summary_config().get("language", "en")
    val = prompts.get(key)
    if val is None:
        return fallback
    if isinstance(val, dict):
        return (val.get(lang) or val.get("en") or fallback).strip()
    return str(val).strip()


_SUMMARY_RE = re.compile(
    r"##\s*Summary\s*\n(.*?)(?=\n##\s*Evidence|\Z)",
    re.DOTALL | re.IGNORECASE,
)
_EVIDENCE_RE = re.compile(
    r"##\s*Evidence\s*\n(.*)",
    re.DOTALL | re.IGNORECASE,
)


def _parse_structured_summary(raw: str) -> tuple[str, str]:
    """Split LLM output into (summary, evidence).

    Expects the ``## Summary`` / ``## Evidence`` markers produced by the
    updated prompts.  Falls back gracefully: if markers are missing the
    entire text is treated as the summary and evidence is empty.
    """
    m_sum = _SUMMARY_RE.search(raw)
    m_evi = _EVIDENCE_RE.search(raw)

    if m_sum:
        summary = m_sum.group(1).strip()
    else:
        summary = raw.split("\n## ")[0].strip() if "\n## " in raw else raw.strip()

    evidence = m_evi.group(1).strip() if m_evi else ""
    return summary, evidence


def _apply_structured(node: dict, raw: str) -> None:
    """Parse *raw* LLM output and store summary + evidence on *node*."""
    summary, evidence = _parse_structured_summary(raw)
    node["summary"] = summary
    if evidence:
        node["evidence"] = evidence
    else:
        node.pop("evidence", None)


# ── Priority levels for the summary queue ──

LEVEL_ACTION = 1
LEVEL_LOCATION = 2
LEVEL_APP = 2
LEVEL_SESSION = 3

KIND_TO_LEVEL = {
    "action": LEVEL_ACTION,
    "location": LEVEL_LOCATION,
    "app": LEVEL_APP,
    "session": LEVEL_SESSION,
}


# ── Public API: single-node summarization ──


def summarize_action_node(node: dict, llm: LLM, force: bool = False) -> bool:
    """Summarize a single action node (L0 mouse clusters + L1 text).

    Returns True if a new summary was produced, False if skipped.
    """
    ctx = node.setdefault("context", {})

    if not force and ctx.get("mouse_summaries") is not None and node.get("summary"):
        return False

    if ctx.get("mouse_actions") and (force or not ctx.get("mouse_summaries")):
        ctx["mouse_summaries"] = _summarize_mouse_clusters(ctx, llm)

    if force or not node.get("summary"):
        raw = _summarize_action(node, llm)
        _apply_structured(node, raw)
        log.info("L1 %s → %s", node.get("node_id"), (node["summary"])[:60])
        return True
    return False


def summarize_location_node(node: dict, llm: LLM, force: bool = False) -> bool:
    """Summarize a single location node (L2). Returns True if produced."""
    if not force and node.get("summary"):
        return False
    children = [ch for ch in node.get("children", []) if ch.get("summary")]
    if not children:
        return False
    raw = _summarize_location(node, children, llm)
    _apply_structured(node, raw)
    log.info("L2 %s → %s", node.get("node_id"), (node["summary"])[:60])
    return True


def summarize_app_node(node: dict, llm: LLM, force: bool = False) -> bool:
    """Summarize a single app node (L2). Returns True if produced."""
    if not force and node.get("summary"):
        return False
    children = [ch for ch in node.get("children", []) if ch.get("summary")]
    if not children:
        return False
    raw = _summarize_app(node, children, llm)
    _apply_structured(node, raw)
    log.info("L2 %s → %s", node.get("node_id"), (node["summary"])[:60])
    return True


def summarize_session_node(node: dict, llm: LLM, force: bool = False) -> bool:
    """Summarize a single session node (L3). Returns True if produced."""
    if not force and node.get("summary"):
        return False
    children = [ch for ch in node.get("children", []) if ch.get("summary")]
    if not children:
        return False
    raw = _summarize_session(node, children, llm)
    _apply_structured(node, raw)
    log.info("L3 %s → %s", node.get("node_id"), (node["summary"])[:60])
    return True


def summarize_node(node: dict, llm: LLM, force: bool = False) -> bool:
    """Dispatch to the correct single-node summarizer by kind."""
    kind = node.get("kind", "")
    if kind == "action":
        return summarize_action_node(node, llm, force)
    if kind == "location":
        return summarize_location_node(node, llm, force)
    if kind == "app":
        return summarize_app_node(node, llm, force)
    if kind == "session":
        return summarize_session_node(node, llm, force)
    return False


# ── Public API: batch / full-tree (kept for manual UI trigger) ──


def summarize_tree(
    date: str,
    mode: str = "time",
    force: bool = False,
) -> dict:
    """Load a saved tree, summarize ALL nodes bottom-up, save back.

    Uses ``include_active=True`` so that every node (including the
    "currently active" last siblings at each level) gets a summary.

    Returns {"summarized": N, "skipped": M, "errors": E}.
    """
    data = load_tree(date, mode)
    if not data or not data.get("tree"):
        return {"summarized": 0, "skipped": 0, "errors": 0, "msg": "no tree found"}

    llm = LLM()
    stats = {"summarized": 0, "skipped": 0, "errors": 0}

    summarize_closed_nodes(data["tree"], llm, force, stats, include_active=True)

    save_tree(data)
    return stats


def summarize_closed_nodes(
    tree: dict,
    llm: LLM,
    force: bool = False,
    stats: dict | None = None,
    include_active: bool = False,
) -> None:
    """Walk tree bottom-up; summarize every closed node (all but last sibling).

    When *include_active* is True, last siblings (the "currently active" node at
    each level) are summarized as well.  Use this when the user explicitly
    triggers summarization from the UI.
    """
    if stats is None:
        stats = {"summarized": 0, "skipped": 0, "errors": 0}
    _walk(tree, llm, force, stats, is_last_sibling=False, include_active=include_active)


def _walk(
    node: dict,
    llm: LLM,
    force: bool,
    stats: dict,
    is_last_sibling: bool,
    include_active: bool = False,
) -> None:
    """Recursive bottom-up walk.

    * Recurse into children first (so lower-level summaries exist before we use them).
    * children[:-1] are closed -> will be summarized.
    * children[-1] is current -> recurse into it but do NOT summarize it
      (unless *include_active* is True).
    * If *this* node is the last sibling of its parent, skip summarizing it too
      (unless *include_active* is True).
    * Stops immediately when LLM budget is exhausted.
    """
    if stats.get("budget_exhausted"):
        return

    children = node.get("children", [])
    for i, ch in enumerate(children):
        if stats.get("budget_exhausted"):
            return
        child_is_last = i == len(children) - 1
        _walk(ch, llm, force, stats, is_last_sibling=child_is_last, include_active=include_active)

    if is_last_sibling and not include_active:
        return

    _maybe_summarize(node, llm, force, stats)


def _maybe_summarize(node: dict, llm: LLM, force: bool, stats: dict) -> None:
    kind = node.get("kind", "")

    if kind == "action":
        _ensure_action_summary(node, llm, force, stats)
    elif kind in ("location", "app", "session"):
        _ensure_higher_summary(node, llm, force, stats)


# ── L0 + L1: Action summarization ──


def _ensure_action_summary(node: dict, llm: LLM, force: bool, stats: dict) -> None:
    ctx = node.setdefault("context", {})

    if not force and ctx.get("mouse_summaries") is not None and node.get("summary"):
        stats["skipped"] += 1
        return

    try:
        if ctx.get("mouse_actions") and (force or not ctx.get("mouse_summaries")):
            ctx["mouse_summaries"] = _summarize_mouse_clusters(ctx, llm)

        if force or not node.get("summary"):
            raw = _summarize_action(node, llm)
            _apply_structured(node, raw)
            stats["summarized"] += 1
            log.info("L1 %s → %s", node.get("node_id"), (node["summary"])[:60])
        else:
            stats["skipped"] += 1
    except LLMBudgetExhausted:
        stats["budget_exhausted"] = True
        log.warning("LLM budget exhausted, stopping summarization")
    except Exception as exc:
        stats["errors"] += 1
        log.warning("action summarize failed %s: %s", node.get("node_id"), exc)


# ── L2 / L3: Higher-level summarization ──


def _ensure_higher_summary(node: dict, llm: LLM, force: bool, stats: dict) -> None:
    if not force and node.get("summary"):
        stats["skipped"] += 1
        return

    children = node.get("children", [])
    summarized_children = [ch for ch in children if ch.get("summary")]
    if not summarized_children:
        return

    try:
        kind = node["kind"]
        if kind == "location":
            raw = _summarize_location(node, summarized_children, llm)
        elif kind == "app":
            raw = _summarize_app(node, summarized_children, llm)
        elif kind == "session":
            raw = _summarize_session(node, summarized_children, llm)
        else:
            return
        _apply_structured(node, raw)
        stats["summarized"] += 1
        log.info(
            "L%s %s → %s",
            {"location": "2", "app": "2", "session": "3"}.get(kind, "?"),
            node.get("node_id"),
            (node["summary"])[:60],
        )
    except LLMBudgetExhausted:
        stats["budget_exhausted"] = True
        log.warning("LLM budget exhausted, stopping summarization")
    except Exception as exc:
        stats["errors"] += 1
        log.warning("higher summarize failed %s: %s", node.get("node_id"), exc)


# ── L0: Mouse cluster → vision LLM ──


def _summarize_mouse_clusters(ctx: dict, llm: LLM) -> list[dict]:
    """Sub-cluster mouse events within an action, summarize each with vision.

    Only full-screen screenshots are used (detail crops are reserved for other
    purposes).  Events without a resolvable ``full`` blob are dropped entirely
    since the LLM cannot interpret coordinates alone.

    When a cluster has more images than ``llm.max_images_per_cluster``, events
    are equal-distance sampled down to the limit.

    The final multi-modal message interleaves action text and image for each
    selected event so the LLM sees them in chronological pairs.
    """
    mouse_actions = ctx.get("mouse_actions", [])
    if not mouse_actions:
        return []

    cfg = load_filter_config()
    gap = cfg.get("mouse_cluster_gap", 3.0)

    from ..services import load_config

    llm_cfg = load_config().get("llm", {})
    max_imgs = int(llm_cfg.get("max_images_per_cluster", 4))

    clusters = _sub_cluster_mouse(mouse_actions, gap)
    results: list[dict] = []

    scfg = _load_summary_config()
    sys_prompt = _get_prompt("l0_mouse_cluster", "Describe the mouse interaction.")
    mt = scfg.get("max_tokens_l0", 400)
    temp = scfg.get("temperature", 0.3)

    for cluster in clusters:
        with_img = []
        for ma in cluster:
            img = _resolve_blob(ma.get("full"))
            if img:
                with_img.append((ma, img))

        if not with_img:
            continue

        if len(with_img) > max_imgs:
            step = len(with_img) / max_imgs
            with_img = [with_img[int(i * step)] for i in range(max_imgs)]

        dur = cluster[-1]["ts"] - cluster[0]["ts"]
        header = f"{sys_prompt}\n\nMouse cluster ({len(with_img)} events shown, {dur:.1f}s):\n"

        content: list[dict] = [{"type": "text", "text": header}]
        for ma, img_path in with_img:
            ts_str = _fmt_ts(ma["ts"])
            act = ma.get("action", "")
            coord = f"({ma.get('x', 0)}, {ma.get('y', 0)})"
            extra = ""
            if ma.get("button"):
                extra += f" button={ma['button']}"
            if ma.get("display"):
                extra += f" display={ma['display']}"
            desc = f"- {ts_str}  {act}{extra} at {coord}\n"
            content.append({"type": "text", "text": desc})
            content.append(_encode_image(img_path))

        messages = [{"role": "user", "content": content}]
        raw = llm.complete(messages, temperature=temp, max_tokens=mt).strip()
        summary, evidence = _parse_structured_summary(raw)

        entry: dict[str, Any] = {
            "start": cluster[0]["ts"],
            "end": cluster[-1]["ts"],
            "summary": summary,
        }
        if evidence:
            entry["evidence"] = evidence
        results.append(entry)
        log.info("L0 mouse cluster → %s", summary[:60])

    return results


def _encode_image(path: str, detail: str = "auto") -> dict:
    """Read an image file and return an OpenAI image_url content block."""
    import base64

    raw = Path(path).read_bytes()
    b64 = base64.b64encode(raw).decode()
    ext = Path(path).suffix.lstrip(".").lower()
    mime_map = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp", "gif": "gif"}
    mime = mime_map.get(ext, "jpeg")
    return {
        "type": "image_url",
        "image_url": {"url": f"data:image/{mime};base64,{b64}", "detail": detail},
    }


def _sub_cluster_mouse(actions: list[dict], gap: float) -> list[list[dict]]:
    """Re-cluster mouse actions by gap, respecting scroll session semantics."""
    if not actions:
        return []

    sorted_acts = sorted(actions, key=lambda a: a["ts"])
    clusters: list[list[dict]] = [[sorted_acts[0]]]

    scroll_balance = 1 if sorted_acts[0].get("action") == "scroll_start" else 0

    for ma in sorted_acts[1:]:
        dt = ma["ts"] - clusters[-1][-1]["ts"]
        if dt < gap or scroll_balance > 0:
            clusters[-1].append(ma)
        else:
            clusters.append([ma])
            scroll_balance = 0

        act = ma.get("action", "")
        if act == "scroll_start":
            scroll_balance += 1
        elif act == "scroll_end":
            scroll_balance = max(0, scroll_balance - 1)

    return clusters


# ── L1: Action → text summary ──


def _summarize_action(node: dict, llm: LLM) -> str:
    ctx = node.get("context", {})
    timeline = _build_action_timeline(node)
    dur = node.get("end", 0) - node.get("start", 0)

    header = ""
    if ctx.get("app"):
        header += f"App: {ctx['app']}\n"
    if ctx.get("location"):
        header += f"Location: {ctx['location']}\n"
    header += f"Time: {_fmt_ts(node['start'])} → {_fmt_ts(node['end'])} ({dur:.1f}s)\n"
    header += f"Event count: {ctx.get('count', 0)}\n"

    scfg = _load_summary_config()
    sys_prompt = _get_prompt("l1_action", "Summarize the user action.")
    mt = scfg.get("max_tokens_l1", 600)
    temp = scfg.get("temperature", 0.3)

    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": header + "\nTimeline:\n" + timeline},
    ]
    return llm.complete(messages, temperature=temp, max_tokens=mt).strip()


def _build_action_timeline(node: dict) -> str:
    """Interleave keyboard, clipboard, and mouse-cluster summaries by time.

    Mouse events are NOT expanded individually — only L0 summaries are used.
    If no L0 summaries exist, a count fallback is shown.
    """
    ctx = node.get("context", {})
    events: list[tuple[float, str]] = []

    if ctx.get("text"):
        text = ctx["text"]
        preview = text if len(text) <= 200 else text[:200] + "…"
        events.append((node["start"], f'[keyboard] typed ({len(text)} chars): "{preview}"'))

    for sc in ctx.get("shortcuts", []):
        events.append((node["start"], f"[keyboard] shortcut: {sc}"))

    for clip in ctx.get("clipboard", []):
        ts = clip.get("ts", node["start"])
        ct = clip.get("type", "text")
        preview = clip.get("preview", "")
        events.append((ts, f'[clipboard] {ct}: "{preview}"'))

    for ms in ctx.get("mouse_summaries", []):
        events.append((ms.get("start", node["start"]), f"[mouse] {ms.get('summary', '')}"))

    if not ctx.get("mouse_summaries"):
        raw_count = len(ctx.get("mouse_actions", []))
        if raw_count:
            events.append((node["start"], f"[mouse] {raw_count} mouse events (not yet summarized)"))

    events.sort(key=lambda x: x[0])
    lines = [f"  {_fmt_ts(ts)}  {desc}" for ts, desc in events]
    return "\n".join(lines) if lines else "  (no detail)"


# ── L2: Location → text summary ──


def _summarize_location(node: dict, children: list[dict], llm: LLM) -> str:
    ctx = node.get("context", {})
    loc = ctx.get("full_location", node.get("title", ""))
    dur = node.get("end", 0) - node.get("start", 0)
    header = f"Location: {loc}\n"
    header += f"Time: {_fmt_ts(node['start'])} → {_fmt_ts(node['end'])} ({dur:.0f}s)\n"
    header += f"Total visits: {ctx.get('span_count', 0)}, Active time: {ctx.get('total_dwell', 0):.0f}s\n\n"

    lines = []
    for ch in children:
        ch_ctx = ch.get("context", {})
        ch_dur = ch.get("end", 0) - ch.get("start", 0)
        title = ch.get("title", "")
        summary = ch.get("summary", "")
        events = ch_ctx.get("count", 0)
        line = f"  {_fmt_ts(ch['start'])} [{title}] ({events} events, {ch_dur:.0f}s)"
        if summary:
            line += f"\n    → {summary}"
        lines.append(line)

    scfg = _load_summary_config()
    sys_prompt = _get_prompt("l2_location", "Summarize the user's work at this location.")
    mt = scfg.get("max_tokens_l2", 800)
    temp = scfg.get("temperature", 0.3)

    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": header + "Actions:\n" + "\n".join(lines)},
    ]
    return llm.complete(messages, temperature=temp, max_tokens=mt).strip()


# ── L2 (app): App → text summary ──


def _summarize_app(node: dict, children: list[dict], llm: LLM) -> str:
    ctx = node.get("context", {})
    dur = node.get("end", 0) - node.get("start", 0)
    header = f"App: {node.get('title', '')}\n"
    header += f"Time: {_fmt_ts(node['start'])} → {_fmt_ts(node['end'])} ({dur:.0f}s)\n"
    header += f"Locations visited: {len(children)}, Spans: {ctx.get('span_count', 0)}, Active: {ctx.get('total_dwell', 0):.0f}s\n\n"

    lines = []
    for ch in children:
        ch_ctx = ch.get("context", {})
        loc_title = ch.get("title", "")
        loc_full = ch_ctx.get("full_location", loc_title)
        loc_summary = ch.get("summary", "")
        action_count = len(ch.get("children", []))
        ch_dwell = ch_ctx.get("total_dwell", 0)
        line = f"  [{loc_title}] ({action_count} actions, {ch_dwell:.0f}s active)"
        if loc_full != loc_title:
            line += f"\n    full: {loc_full}"
        if loc_summary:
            line += f"\n    → {loc_summary}"
        lines.append(line)

    scfg = _load_summary_config()
    sys_prompt = _get_prompt(
        "l2_app", _get_prompt("l2_location", "Summarize the user's work in this app.")
    )
    mt = scfg.get("max_tokens_l2", 800)
    temp = scfg.get("temperature", 0.3)

    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": header + "Locations:\n" + "\n".join(lines)},
    ]
    return llm.complete(messages, temperature=temp, max_tokens=mt).strip()


# ── L3: Session → text summary ──


def _summarize_session(node: dict, children: list[dict], llm: LLM) -> str:
    ctx = node.get("context", {})
    dur = node.get("end", 0) - node.get("start", 0)
    header = f"Session: {node.get('title', '')}\n"
    header += f"Time: {_fmt_ts(node['start'])} → {_fmt_ts(node['end'])} ({dur:.0f}s)\n"
    if ctx.get("apps"):
        header += f"Apps used: {', '.join(ctx['apps'])}\n"
    header += f"Spans: {ctx.get('span_count', 0)}, Active: {ctx.get('total_dwell', 0):.0f}s\n\n"

    lines = []
    for ch in children:
        app_title = ch.get("title", "")
        app_summary = ch.get("summary", "")
        loc_count = len(ch.get("children", []))
        ch_ctx = ch.get("context", {})
        ch_dwell = ch_ctx.get("total_dwell", 0)
        line = f"  [{app_title}] ({loc_count} locations, {ch_dwell:.0f}s active)"
        if app_summary:
            line += f"\n    → {app_summary}"
        lines.append(line)

    scfg = _load_summary_config()
    sys_prompt = _get_prompt("l3_session", "Summarize the user's work session.")
    mt = scfg.get("max_tokens_l3", 1200)
    temp = scfg.get("temperature", 0.3)

    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": header + "Apps:\n" + "\n".join(lines)},
    ]
    return llm.complete(messages, temperature=temp, max_tokens=mt).strip()


# ── Helpers ──


def _resolve_blob(rel: str | None) -> str | None:
    if not rel:
        return None
    full = os.path.join(_get_blob_dir(), rel)
    return full if os.path.isfile(full) else None


def _fmt_ts(ts: float) -> str:
    return time.strftime("%H:%M:%S", time.localtime(ts))
