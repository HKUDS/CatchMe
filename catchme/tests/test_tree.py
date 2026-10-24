"""Tests for catchme.pipelines.tree — ActivityNode, tree build, serialization, persistence."""

from __future__ import annotations

import os
from unittest import mock

from catchme.pipelines.tree import (
    ActivityNode,
    _hash_loc,
    _sanitize_app,
    build_tree,
    extend_tree,
    load_tree,
    merge_summaries,
    save_tree,
)

from .conftest import make_clipboard_event, make_kb_event, make_mouse_event, make_window_event

# ── ActivityNode ──


class TestActivityNode:
    def test_to_dict_minimal(self):
        node = ActivityNode(
            node_id="n1",
            kind="action",
            title="typing",
            start=100,
            end=110,
        )
        d = node.to_dict()
        assert d["node_id"] == "n1"
        assert d["kind"] == "action"
        assert "children" not in d
        assert "summary" not in d
        assert "context" not in d

    def test_to_dict_with_summary(self):
        node = ActivityNode(
            node_id="n2",
            kind="session",
            title="10:00 – 11:00",
            start=100,
            end=200,
            summary="Wrote code",
        )
        d = node.to_dict()
        assert d["summary"] == "Wrote code"

    def test_to_dict_with_children(self):
        child = ActivityNode(node_id="c1", kind="action", title="click", start=100, end=101)
        parent = ActivityNode(
            node_id="p1", kind="app", title="Safari", start=100, end=200, children=[child]
        )
        d = parent.to_dict()
        assert len(d["children"]) == 1
        assert d["children"][0]["node_id"] == "c1"

    def test_to_dict_with_context(self):
        node = ActivityNode(
            node_id="n3",
            kind="location",
            title="github.com",
            start=100,
            end=200,
            context={"full_location": "https://github.com", "span_count": 2},
        )
        d = node.to_dict()
        assert d["context"]["span_count"] == 2

    def test_nested_to_dict_recursive(self):
        grandchild = ActivityNode(node_id="gc", kind="action", title="type", start=100, end=101)
        child = ActivityNode(
            node_id="ch",
            kind="location",
            title="file.py",
            start=100,
            end=110,
            children=[grandchild],
        )
        root = ActivityNode(
            node_id="rt", kind="app", title="VS Code", start=100, end=200, children=[child]
        )
        d = root.to_dict()
        assert d["children"][0]["children"][0]["node_id"] == "gc"


# ── build_tree ──


class TestBuildTree:
    def _populate_store(self, store, base_ts=None):
        base = base_ts or 1_700_000_000.0
        events = [
            make_window_event(base, "Safari", "Google", url="https://google.com"),
            make_window_event(base + 10, "Safari", "GitHub", url="https://github.com"),
            make_window_event(base + 30, "Terminal", "zsh"),
            make_kb_event(base + 5, "h"),
            make_kb_event(base + 6, "i"),
            make_mouse_event(base + 12, "click"),
            make_clipboard_event(base + 20, "some text"),
        ]
        store.insert_raw(events)
        return base

    def test_build_time_mode(self, store):
        base = self._populate_store(store)
        result = build_tree(
            store,
            since=base - 1,
            until=base + 100,
            mode="time",
            cfg={"session_gap": 300, "window_min_dwell": 1.0, "action_gap": 3.0},
        )
        assert result["mode"] == "time"
        tree = result["tree"]
        assert tree is not None
        assert tree["kind"] == "day"
        assert len(tree["children"]) >= 1  # at least one session

    def test_build_app_mode(self, store):
        base = self._populate_store(store)
        result = build_tree(
            store,
            since=base - 1,
            until=base + 100,
            mode="app",
            cfg={"session_gap": 300, "window_min_dwell": 1.0, "action_gap": 3.0},
        )
        assert result["mode"] == "app"
        tree = result["tree"]
        assert tree is not None
        assert tree["kind"] == "day"
        app_names = [ch["title"] for ch in tree.get("children", [])]
        assert "Safari" in app_names or "Terminal" in app_names

    def test_build_empty_store(self, store):
        result = build_tree(store, mode="time")
        assert result["tree"] is None

    def test_extend_app_tree_includes_new_events(self, store):
        base = 1_700_000_000.0
        store.insert_raw([make_window_event(base, "Safari", "First synthetic window")])
        cfg = {"session_gap": 300, "window_min_dwell": 1.0, "action_gap": 3.0}

        with (
            mock.patch("catchme.pipelines.tree.load_filter_config", return_value={}),
            mock.patch("catchme.pipelines.tree.time.time", return_value=base + 10),
        ):
            existing = build_tree(store, since=base - 1, until=base + 100, mode="app", cfg=cfg)
        existing["tree"]["children"][0]["summary"] = "retained synthetic summary"

        store.insert_raw([make_window_event(base + 20, "Terminal", "Second synthetic window")])
        with (
            mock.patch("catchme.pipelines.tree.load_filter_config", return_value={}),
            mock.patch("catchme.pipelines.tree.time.time", return_value=base + 30),
        ):
            changed = extend_tree(existing, store, since=base + 19, until=base + 100, cfg=cfg)

        assert changed
        app_summaries = {
            child["title"]: child.get("summary") for child in existing["tree"]["children"]
        }
        assert set(app_summaries) == {"Safari", "Terminal"}
        assert app_summaries["Safari"] == "retained synthetic summary"


# ── save_tree / load_tree ──


class TestTreePersistence:
    def test_save_and_load(self, cfg):
        tree_dict = {
            "node_id": "d20241115",
            "kind": "day",
            "title": "2024-11-15",
            "start": 100,
            "end": 200,
            "children": [
                {"node_id": "s1", "kind": "session", "title": "10:00", "start": 100, "end": 200}
            ],
        }
        result = {"tree": tree_dict, "mode": "time"}

        with mock.patch("catchme.pipelines.tree._get_tree_dir", return_value=str(cfg.tree_dir)):
            path = save_tree(result)
            assert path is not None
            assert os.path.isfile(path)

            loaded = load_tree("2024-11-15", mode="time")
            assert loaded is not None
            assert loaded["tree"]["node_id"] == "d20241115"
            assert loaded["mode"] == "time"

    def test_save_none_tree_returns_none(self, cfg):
        result = {"tree": None, "mode": "time"}
        assert save_tree(result) is None

    def test_load_nonexistent(self, cfg):
        with mock.patch("catchme.pipelines.tree._get_tree_dir", return_value=str(cfg.tree_dir)):
            assert load_tree("1999-01-01") is None


# ── merge_summaries ──


class TestMergeSummaries:
    def test_copy_summary_from_old(self):
        old = {
            "node_id": "root",
            "kind": "day",
            "title": "2024-01-01",
            "start": 0,
            "end": 100,
            "summary": "Busy day",
            "children": [
                {
                    "node_id": "s1",
                    "kind": "session",
                    "summary": "Morning work",
                    "start": 0,
                    "end": 50,
                    "children": [],
                },
            ],
        }
        new = {
            "node_id": "root",
            "kind": "day",
            "title": "2024-01-01",
            "start": 0,
            "end": 100,
            "children": [
                {"node_id": "s1", "kind": "session", "start": 0, "end": 50, "children": []},
            ],
        }
        merge_summaries(old, new)
        assert new["children"][0].get("summary") == "Morning work"

    def test_no_overwrite_existing_summary(self):
        old = {"node_id": "n1", "summary": "old text", "children": []}
        new = {"node_id": "n1", "summary": "new text", "children": []}
        merge_summaries(old, new)
        assert new["summary"] == "new text"

    def test_evidence_merged(self):
        old = {"node_id": "a1", "evidence": "screenshot showed X", "children": []}
        new = {"node_id": "a1", "children": []}
        merge_summaries(old, new)
        assert new.get("evidence") == "screenshot showed X"


# ── Helpers ──


class TestHelpers:
    def test_sanitize_app(self):
        assert _sanitize_app("VS Code") == "vs_code"
        assert _sanitize_app("Safari") == "safari"
        assert _sanitize_app("") != ""  # falls back to hash
        assert len(_sanitize_app("A" * 100)) <= 24

    def test_hash_loc_deterministic(self):
        h1 = _hash_loc("https://github.com")
        h2 = _hash_loc("https://github.com")
        assert h1 == h2
        assert len(h1) == 8

    def test_hash_loc_different_inputs(self):
        assert _hash_loc("a") != _hash_loc("b")
