from __future__ import annotations

from catchme.organizer import Organizer


class _QueueSpy:
    def __init__(self) -> None:
        self.closed: set[str] = set()
        self.enqueued: set[str] = set()

    def register_parent(self, child_nid: str, parent: dict) -> None:
        pass

    def mark_closed(self, nid: str) -> None:
        self.closed.add(nid)

    def enqueue(
        self,
        node: dict,
        level: int,
        parent: dict | None = None,
        is_closed: bool = True,
    ) -> None:
        self.enqueued.add(node["node_id"])


def _node(node_id: str, kind: str, children: list[dict] | None = None) -> dict:
    return {
        "node_id": node_id,
        "kind": kind,
        "children": children or [],
    }


def test_closed_ancestor_closes_its_last_descendants() -> None:
    closed_action = _node("closed-action", "action")
    closed_session = _node(
        "closed-session",
        "session",
        [
            _node(
                "closed-app",
                "app",
                [_node("closed-location", "location", [closed_action])],
            )
        ],
    )
    active_action = _node("active-action", "action")
    active_session = _node(
        "active-session",
        "session",
        [
            _node(
                "active-app",
                "app",
                [_node("active-location", "location", [active_action])],
            )
        ],
    )
    day = _node("day", "day", [closed_session, active_session])

    organizer = Organizer.__new__(Organizer)
    organizer._queue = _QueueSpy()
    organizer._enqueue_closed_nodes(day)

    assert organizer._queue.closed == {
        "closed-action",
        "closed-location",
        "closed-app",
        "closed-session",
    }
    assert organizer._queue.enqueued == organizer._queue.closed
    assert "active-action" not in organizer._queue.closed
    assert "active-action" not in organizer._queue.enqueued
