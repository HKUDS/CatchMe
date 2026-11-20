"""Tests for catchme.store — Event dataclass and SQLite Store."""

from __future__ import annotations

import threading

from catchme.store import Event, Store


class TestEvent:
    def test_default_fields(self):
        ev = Event(timestamp=1.0, kind="window", data={"app": "Finder"})
        assert ev.blob == ""
        assert ev.id is None

    def test_equality(self):
        a = Event(timestamp=1.0, kind="window", data={"x": 1})
        b = Event(timestamp=1.0, kind="window", data={"x": 1})
        assert a == b

    def test_different_blob(self):
        a = Event(timestamp=1.0, kind="mouse", data={}, blob="/a.png")
        b = Event(timestamp=1.0, kind="mouse", data={}, blob="/b.png")
        assert a != b


class TestStoreInsertAndQuery:
    def test_insert_and_count(self, store, sample_events):
        assert store.count() == 0
        store.insert_raw(sample_events)
        assert store.count() == len(sample_events)

    def test_insert_empty_is_noop(self, store):
        store.insert_raw([])
        assert store.count() == 0

    def test_query_all(self, store, sample_events):
        store.insert_raw(sample_events)
        rows = store.query_raw(limit=100)
        assert len(rows) == len(sample_events)
        assert all(isinstance(r, Event) for r in rows)

    def test_query_by_kind(self, store, sample_events):
        store.insert_raw(sample_events)
        windows = store.query_raw(kind="window")
        assert all(e.kind == "window" for e in windows)
        assert len(windows) == 3

    def test_query_since(self, store, sample_events):
        store.insert_raw(sample_events)
        base = sample_events[0].timestamp
        rows = store.query_raw(since=base + 15)
        assert all(e.timestamp >= base + 15 for e in rows)

    def test_query_until(self, store, sample_events):
        store.insert_raw(sample_events)
        base = sample_events[0].timestamp
        rows = store.query_raw(until=base + 10)
        assert all(e.timestamp <= base + 10 for e in rows)

    def test_query_since_and_until(self, store, sample_events):
        store.insert_raw(sample_events)
        base = sample_events[0].timestamp
        rows = store.query_raw(since=base + 5, until=base + 20)
        assert all(base + 5 <= e.timestamp <= base + 20 for e in rows)

    def test_query_limit(self, store, sample_events):
        store.insert_raw(sample_events)
        rows = store.query_raw(limit=2)
        assert len(rows) == 2

    def test_query_order_desc(self, store, sample_events):
        store.insert_raw(sample_events)
        rows = store.query_raw(limit=100)
        timestamps = [r.timestamp for r in rows]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_roundtrip_preserves_data(self, store):
        original = Event(
            timestamp=123.456,
            kind="keyboard",
            data={"key": "a", "type": "text", "unicode": "\u4f60\u597d"},
            blob="/some/path.png",
        )
        store.insert_raw([original])
        rows = store.query_raw()
        assert len(rows) == 1
        r = rows[0]
        assert r.kind == "keyboard"
        assert r.data["key"] == "a"
        assert r.data["unicode"] == "\u4f60\u597d"
        assert r.blob == "/some/path.png"
        assert r.id is not None


class TestStoreSearch:
    def test_fts_basic(self, store):
        store.insert_raw(
            [
                Event(timestamp=1.0, kind="window", data={"app": "Finder", "title": "Documents"}),
                Event(timestamp=2.0, kind="window", data={"app": "Safari", "title": "Python docs"}),
            ]
        )
        results = store.search("Python")
        assert len(results) == 1
        assert results[0].data["title"] == "Python docs"

    def test_fts_with_kind_filter(self, store):
        store.insert_raw(
            [
                Event(timestamp=1.0, kind="window", data={"title": "pytest guide"}),
                Event(timestamp=2.0, kind="keyboard", data={"key": "pytest", "type": "text"}),
            ]
        )
        results = store.search("pytest", kind="keyboard")
        assert len(results) == 1
        assert results[0].kind == "keyboard"

    def test_fts_with_time_range(self, store):
        store.insert_raw(
            [
                Event(timestamp=100.0, kind="window", data={"title": "old doc"}),
                Event(timestamp=200.0, kind="window", data={"title": "new doc"}),
            ]
        )
        results = store.search("doc", since=150.0)
        assert len(results) == 1
        assert results[0].timestamp == 200.0

    def test_fts_punctuation_is_treated_as_keyword_text(self, store):
        store.insert_raw(
            [
                Event(timestamp=1.0, kind="window", data={"title": "C++ guide"}),
                Event(timestamp=2.0, kind="window", data={"title": "unterminated quote guide"}),
            ]
        )

        cpp_results = store.search("C++")
        assert [event.data["title"] for event in cpp_results] == ["C++ guide"]
        quoted_results = store.search('"unterminated')
        assert [event.data["title"] for event in quoted_results] == ["unterminated quote guide"]
        assert store.search('"') == []

    def test_fts_no_match(self, store):
        store.insert_raw(
            [
                Event(timestamp=1.0, kind="window", data={"title": "hello"}),
            ]
        )
        results = store.search("nonexistent_xyzzy")
        assert results == []


class TestStoreStats:
    def test_stats_grouped(self, store, sample_events):
        store.insert_raw(sample_events)
        stats = store.stats()
        kinds = {s["kind"] for s in stats}
        assert "window" in kinds
        assert "keyboard" in kinds
        for s in stats:
            assert s["count"] > 0
            assert s["first"] <= s["last"]

    def test_stats_empty(self, store):
        assert store.stats() == []


class TestStoreThreadSafety:
    def test_concurrent_inserts(self, store):
        """Multiple threads inserting simultaneously should not raise."""
        errors = []

        def worker(offset):
            try:
                events = [
                    Event(timestamp=float(offset * 100 + i), kind="test", data={"i": i})
                    for i in range(50)
                ]
                store.insert_raw(events)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert store.count() == 200


class TestStoreClose:
    def test_close_and_reopen(self, cfg, sample_events):
        s1 = Store(cfg.db_path)
        s1.insert_raw(sample_events)
        s1.close()

        s2 = Store(cfg.db_path)
        assert s2.count() == len(sample_events)
        s2.close()
