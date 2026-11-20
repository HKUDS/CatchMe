"""Tests for catchme.pipelines.filter — window spans, clustering, IME strip."""

from __future__ import annotations

from catchme.pipelines.filter import (
    _blob_relative,
    _has_cjk,
    _serialize_mouse_action,
    _strip_ime_pinyin,
    build_window_spans,
    cluster_events,
)
from catchme.store import Event

from .conftest import make_kb_event, make_window_event


class TestBlobPathSerialization:
    def test_blob_paths_are_relative_for_windows_and_posix(self):
        expected = "2026-10-24/capture/full.webp"
        assert (
            _blob_relative(
                r"C:\archive\blobs\old\profile\.catchme\blobs\2026-10-24\capture\full.webp"
            )
            == expected
        )
        assert _blob_relative("/home/alice/.catchme/blobs/2026-10-24/capture/full.webp") == expected

    def test_mouse_action_serializes_blob_paths_for_web_urls(self, tmp_path):
        blob_dir = tmp_path / "parent" / "blobs" / "2026-10-24" / "capture"
        blob_dir.mkdir(parents=True)
        full_path = blob_dir / "full.webp"
        detail_path = blob_dir / "detail.webp"
        full_path.write_bytes(b"synthetic full image")
        detail_path.write_bytes(b"synthetic detail image")
        event = Event(
            timestamp=1,
            kind="mouse",
            data={"detail": str(detail_path)},
            blob=str(full_path),
        )

        serialized = _serialize_mouse_action(event)

        assert serialized["full"] == "2026-10-24/capture/full.webp"
        assert serialized["detail"] == "2026-10-24/capture/detail.webp"


# ── build_window_spans ──


class TestBuildWindowSpans:
    def test_empty_input(self):
        assert build_window_spans([], min_dwell=3.0) == []

    def test_single_event_always_valid(self):
        ev = make_window_event(100, "Safari", "Google")
        spans = build_window_spans([ev], min_dwell=3.0, now=110)
        assert len(spans) == 1
        assert spans[0].app == "Safari"
        assert spans[0].dwell == 10

    def test_short_dwell_filtered(self):
        events = [
            make_window_event(100, "Safari", "Google"),
            make_window_event(101, "Finder", "Desktop"),  # 1s dwell — brief
            make_window_event(102, "Terminal", "zsh"),
        ]
        spans = build_window_spans(events, min_dwell=3.0, now=110)
        apps = [s.app for s in spans]
        assert "Finder" not in apps or any("Finder" in b.app for s in spans for b in s.briefs)

    def test_merge_same_app_title(self):
        events = [
            make_window_event(100, "VS Code", "main.py"),
            make_window_event(105, "Finder", "temp"),  # brief
            make_window_event(106, "VS Code", "main.py"),
        ]
        spans = build_window_spans(events, min_dwell=3.0, now=120)
        vscode_spans = [s for s in spans if s.app == "VS Code"]
        assert len(vscode_spans) == 1
        assert vscode_spans[0].start == 100

    def test_max_span_dwell_caps(self):
        events = [
            make_window_event(100, "Safari", "Page"),
            make_window_event(500, "Terminal", "zsh"),
        ]
        spans = build_window_spans(events, min_dwell=1.0, now=600, max_span_dwell=60)
        safari = [s for s in spans if s.app == "Safari"][0]
        assert safari.dwell <= 60

    def test_briefs_attached_to_owner(self):
        events = [
            make_window_event(100, "Safari", "Page A"),
            make_window_event(110, "Popup", "Alert"),  # 1s — brief
            make_window_event(111, "Safari", "Page B"),
        ]
        spans = build_window_spans(events, min_dwell=3.0, now=200)
        owners_with_briefs = [s for s in spans if s.briefs]
        assert len(owners_with_briefs) >= 1


# ── cluster_events ──


class TestClusterEvents:
    def test_empty_input(self):
        assert cluster_events([], gap=3.0) == []

    def test_single_event(self):
        ev = make_kb_event(100, "a")
        clusters = cluster_events([ev], gap=3.0)
        assert len(clusters) == 1
        assert len(clusters[0].events) == 1

    def test_close_events_in_one_cluster(self):
        events = [make_kb_event(100 + i * 0.5, chr(97 + i)) for i in range(5)]
        clusters = cluster_events(events, gap=3.0)
        assert len(clusters) == 1
        assert len(clusters[0].events) == 5

    def test_gap_splits_clusters(self):
        events = [
            make_kb_event(100, "a"),
            make_kb_event(101, "b"),
            make_kb_event(110, "c"),  # gap > 3
            make_kb_event(111, "d"),
        ]
        clusters = cluster_events(events, gap=3.0)
        assert len(clusters) == 2
        assert len(clusters[0].events) == 2
        assert len(clusters[1].events) == 2

    def test_scroll_session_keeps_cluster_open(self):
        events = [
            Event(timestamp=100, kind="mouse", data={"action": "scroll_start", "x": 0, "y": 0}),
            Event(timestamp=101, kind="mouse", data={"action": "scroll", "x": 0, "y": 10}),
            # gap of 5s > 3s, but scroll session is still open
            Event(timestamp=106, kind="mouse", data={"action": "scroll", "x": 0, "y": 20}),
            Event(timestamp=107, kind="mouse", data={"action": "scroll_end", "x": 0, "y": 20}),
        ]
        clusters = cluster_events(events, gap=3.0)
        assert len(clusters) == 1

    def test_cluster_timestamps(self):
        events = [make_kb_event(100, "a"), make_kb_event(102, "b")]
        clusters = cluster_events(events, gap=3.0)
        assert clusters[0].start == 100
        assert clusters[0].end == 102

    def test_unordered_input_sorted(self):
        events = [make_kb_event(105, "b"), make_kb_event(100, "a")]
        clusters = cluster_events(events, gap=3.0)
        assert clusters[0].events[0].timestamp == 100


# ── IME pinyin stripping ──


class TestIMEStrip:
    def test_plain_text(self):
        events = [make_kb_event(i, c) for i, c in enumerate("hello")]
        assert _strip_ime_pinyin(events) == "hello"

    def test_cjk_detection(self):
        assert _has_cjk("你好")
        assert _has_cjk("hello你")
        assert not _has_cjk("hello")
        assert not _has_cjk("")

    def test_ime_composition_stripped(self):
        ZWS = "\u200b"
        events = [
            Event(timestamp=1, kind="keyboard", data={"key": ZWS + "n", "type": "text"}),
            Event(timestamp=2, kind="keyboard", data={"key": "i", "type": "text"}),
            Event(timestamp=3, kind="keyboard", data={"key": "你", "type": "text"}),
            Event(timestamp=4, kind="keyboard", data={"key": "h", "type": "text"}),
        ]
        result = _strip_ime_pinyin(events)
        assert "你" in result
        assert "h" in result
        assert ZWS not in result

    def test_special_keys_bracketed(self):
        events = [
            Event(timestamp=1, kind="keyboard", data={"key": "Return", "type": "special"}),
        ]
        assert _strip_ime_pinyin(events) == "<Return>"
