"""Organizer: boundary-event-driven tree rebuild + async summarization.

Watches for window switches and idle events. When triggered, rebuilds
the activity tree for today, then enqueues closed nodes into the
:class:`SummaryQueue` for asynchronous LLM summarization.

Designed to run as a daemon thread inside :class:`Engine`.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime

from .config import Config
from .store import Event, Store

log = logging.getLogger(__name__)

_FALLBACK_INTERVAL = 300.0  # 5 min idle poll


class Organizer:
    def __init__(self, store: Store, config: Config) -> None:
        self._store = store
        self._config = config
        self._last_window_key: tuple | None = None
        self._pending = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._tree_cache: dict | None = None
        self._last_event_ts: float = 0.0
        self._last_build_time: float = 0.0

        from .services import load_config

        scfg = load_config().get("summarize", {})
        self._debounce_sec: float = float(scfg.get("debounce_sec", 3.0))
        max_workers: int = int(scfg.get("max_workers", 2))

        from .summary_queue import SummaryQueue

        self._queue = SummaryQueue(
            max_workers=max_workers,
            save_fn=self._save_tree,
        )

    # ── Event hook (called from Engine emitter — must be lightweight) ──

    def on_event(self, event: Event) -> None:
        if event.kind == "window":
            key = (event.data.get("app"), event.data.get("title"))
            if key != self._last_window_key:
                self._last_window_key = key
                self._pending.set()
        elif event.kind == "idle":
            if event.data.get("status") in ("idle", "locked"):
                self._pending.set()

    # ── Main loop ──

    def run(self) -> None:
        """Block until stopped. Waits for boundary events then processes."""
        self._thread = threading.current_thread()
        while not self._stop.is_set():
            self._pending.wait(timeout=_FALLBACK_INTERVAL)
            if self._stop.is_set():
                break
            self._pending.clear()
            try:
                self._process()
            except Exception:
                log.exception("organizer processing error")

    def stop(self) -> None:
        self._stop.set()
        self._pending.set()
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join()
        self._queue.stop()
        self._save_tree()

    # ── Core processing ──

    def _process(self) -> None:
        now = time.time()
        if now - self._last_build_time < self._debounce_sec:
            return

        from .pipelines.tree import (
            build_tree,
            extend_tree,
            load_tree,
        )

        today = datetime.now().strftime("%Y-%m-%d")
        d0 = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        d1 = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
        until = d1.timestamp()

        if self._tree_cache is None:
            cached = load_tree(today, "time")
            if cached and cached.get("tree"):
                self._tree_cache = cached
                tree_children = cached["tree"].get("children", [])
                if tree_children:
                    self._last_event_ts = max(ch.get("end", 0) for ch in tree_children)
            else:
                since = d0.timestamp()
                result = build_tree(self._store, since=since, until=until, mode="time")
                if not result or not result.get("tree"):
                    self._last_build_time = now
                    return
                self._tree_cache = result
                self._last_event_ts = result["tree"].get("end", 0)
        else:
            if self._last_event_ts > 0:
                query_since = self._last_event_ts - 1.0
            else:
                query_since = d0.timestamp()

            modified = extend_tree(
                self._tree_cache,
                self._store,
                since=query_since,
                until=until,
            )
            if not modified:
                self._last_build_time = now
                return

            tree = self._tree_cache.get("tree")
            if tree:
                self._last_event_ts = tree.get("end", self._last_event_ts)

        tree = self._tree_cache.get("tree")
        if tree:
            self._enqueue_closed_nodes(tree)
            # Persist latest tree snapshot so `catchme ask` can read it immediately,
            # even when the current session is still open.
            self._save_tree()

        self._last_build_time = now

    # ── Enqueue closed nodes into the async queue ──

    def _enqueue_closed_nodes(self, tree: dict) -> None:
        from .pipelines.summarize import KIND_TO_LEVEL

        self._walk_enqueue(tree, is_last_sibling=False, parent=None, kind_to_level=KIND_TO_LEVEL)

    def _walk_enqueue(
        self,
        node: dict,
        is_last_sibling: bool,
        parent: dict | None,
        kind_to_level: dict,
    ) -> None:
        children = node.get("children", [])
        for i, ch in enumerate(children):
            child_is_last = i == len(children) - 1
            self._walk_enqueue(ch, child_is_last, parent=node, kind_to_level=kind_to_level)

        kind = node.get("kind", "")
        if kind not in kind_to_level:
            return

        nid = node.get("node_id", "")
        if parent:
            self._queue.register_parent(nid, parent)

        is_closed = not is_last_sibling
        if is_closed:
            self._queue.mark_closed(nid)

        if not is_closed:
            return

        if node.get("summary"):
            return

        level = kind_to_level[kind]
        self._queue.enqueue(node, level, parent=parent, is_closed=True)

    # ── Tree persistence ──

    def _save_tree(self) -> None:
        if self._tree_cache:
            from .pipelines.tree import save_tree

            save_tree(self._tree_cache)
