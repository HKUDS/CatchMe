"""Asynchronous priority-based summary queue.

Nodes are enqueued when they close. Workers call the LLM and, on
success, cascade to the parent node if all its children are done.

Notifications are appended to ``data/summary_updates.jsonl`` so the
web process can stream them via SSE.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from queue import Empty, PriorityQueue

from .services.llm import LLM, LLMBudgetExhausted

log = logging.getLogger(__name__)

_MAX_NOTIFY_LINES = 500


def _get_notify_path() -> str:
    from .config import get_default_config

    return str(get_default_config().notify_path)


class _QueueItem:
    """Wrapper for PriorityQueue ordering: (level, enqueue_time, node_id)."""

    __slots__ = ("level", "ts", "node_id", "node", "retry")

    def __init__(self, level: int, node: dict, retry: int = 0) -> None:
        self.level = level
        self.ts = time.time()
        self.node_id: str = node.get("node_id", "")
        self.node = node
        self.retry = retry

    def __lt__(self, other: _QueueItem) -> bool:
        if self.level != other.level:
            return self.level < other.level
        return self.ts < other.ts


class SummaryQueue:
    """Priority queue + thread-pool for async LLM summarization."""

    def __init__(self, max_workers: int = 2, save_fn: Callable[[], None] | None = None) -> None:
        self._q: PriorityQueue[_QueueItem] = PriorityQueue()
        self._max_workers = max(1, max_workers)
        self._pool = ThreadPoolExecutor(max_workers=self._max_workers, thread_name_prefix="sumq")
        self._in_flight: set[str] = set()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._llm = LLM()

        self._parent_map: dict[str, dict] = {}
        self._closed_set: set[str] = set()

        self._save_fn = save_fn
        self._last_save = 0.0
        from .services import load_config

        scfg = load_config().get("summarize", {})
        self._save_interval = float(scfg.get("save_interval_sec", 5.0))

        self._dispatcher = threading.Thread(
            target=self._dispatch_loop, daemon=True, name="sumq-dispatch"
        )
        self._dispatcher.start()

    # ── Public API ──

    def enqueue(
        self, node: dict, level: int, parent: dict | None = None, is_closed: bool = True
    ) -> None:
        nid = node.get("node_id", "")
        if not nid:
            return

        with self._lock:
            if nid in self._in_flight:
                return
            if not self._needs_summary(node):
                return
            self._in_flight.add(nid)

        if parent:
            self._parent_map[nid] = parent
        if is_closed:
            self._closed_set.add(nid)

        self._q.put(_QueueItem(level, node))
        log.debug("enqueued %s (level=%d)", nid, level)

    def register_parent(self, child_nid: str, parent: dict) -> None:
        self._parent_map[child_nid] = parent

    def mark_closed(self, nid: str) -> None:
        self._closed_set.add(nid)

    def stop(self) -> None:
        self._stop.set()
        self._dispatcher.join()
        self._pool.shutdown(wait=True, cancel_futures=True)
        self._force_save()

    # ── Dispatch loop ──

    def _dispatch_loop(self) -> None:
        while not self._stop.is_set():
            try:
                item = self._q.get(timeout=1.0)
            except Empty:
                continue

            if self._stop.is_set():
                break

            self._pool.submit(self._process_item, item)

    def _process_item(self, item: _QueueItem) -> None:
        node = item.node
        nid = item.node_id

        try:
            if not self._ready(node):
                if item.retry < 10:
                    time.sleep(1.0)
                    with self._lock:
                        self._in_flight.discard(nid)
                    item.retry += 1
                    self.enqueue(node, item.level, parent=self._parent_map.get(nid))
                else:
                    log.debug("giving up on %s after %d retries", nid, item.retry)
                    with self._lock:
                        self._in_flight.discard(nid)
                return

            from .pipelines.summarize import summarize_node

            produced = summarize_node(node, self._llm, force=False)

            if produced:
                self._write_notification(node)
                self._maybe_save()
                self._cascade_parent(nid)

        except LLMBudgetExhausted:
            log.warning("LLM budget exhausted, queue stopping")
            self._stop.set()
        except Exception:
            log.exception("summary worker error for %s", nid)
        finally:
            with self._lock:
                self._in_flight.discard(nid)

    # ── Helpers ──

    @staticmethod
    def _needs_summary(node: dict) -> bool:
        kind = node.get("kind", "")
        if kind not in ("action", "location", "app", "session"):
            return False
        return not node.get("summary")

    def _ready(self, node: dict) -> bool:
        """For higher-level nodes, check that at least one child has a summary."""
        kind = node.get("kind", "")
        if kind == "action":
            return True
        children = node.get("children", [])
        return any(ch.get("summary") for ch in children)

    def _cascade_parent(self, child_nid: str) -> None:
        parent = self._parent_map.get(child_nid)
        if not parent:
            return
        pid = parent.get("node_id", "")
        if not pid:
            return

        if pid not in self._closed_set:
            return

        if parent.get("summary"):
            return

        from .pipelines.summarize import KIND_TO_LEVEL

        level = KIND_TO_LEVEL.get(parent.get("kind", ""), 3)
        self.enqueue(parent, level, parent=self._parent_map.get(pid))

    def _write_notification(self, node: dict) -> None:
        ctx = node.get("context", {})
        entry = {
            "ts": time.time(),
            "node_id": node.get("node_id", ""),
            "kind": node.get("kind", ""),
            "title": node.get("title", ""),
            "summary": node.get("summary", ""),
            "start": node.get("start", 0),
            "end": node.get("end", 0),
            "app": ctx.get("app", ""),
            "location": ctx.get("full_location", ctx.get("location", "")),
        }
        if node.get("evidence"):
            entry["evidence"] = node["evidence"]

        try:
            with open(_get_notify_path(), "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                f.flush()
        except OSError:
            log.debug("failed to write notification", exc_info=True)

    def _maybe_save(self) -> None:
        now = time.time()
        if now - self._last_save < self._save_interval:
            return
        self._last_save = now
        self._force_save()

    def _force_save(self) -> None:
        if self._save_fn:
            try:
                self._save_fn()
            except Exception:
                log.debug("save_fn error", exc_info=True)


def truncate_notification_file() -> None:
    """Keep only the last *_MAX_NOTIFY_LINES* lines in the notification file."""
    path = _get_notify_path()
    if not os.path.isfile(path):
        return
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
        if len(lines) <= _MAX_NOTIFY_LINES:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(lines[-_MAX_NOTIFY_LINES:])
    except OSError:
        pass


def get_notification_path() -> str:
    return _get_notify_path()
