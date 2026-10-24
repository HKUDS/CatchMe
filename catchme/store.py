"""SQLite store — single-table event storage with FTS5 full-text search."""

from __future__ import annotations

import json
import re
import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Event:
    timestamp: float
    kind: str
    data: dict
    blob: str = ""
    id: int | None = None


_SCHEMA = """
CREATE TABLE IF NOT EXISTS events_raw (
    id        INTEGER PRIMARY KEY,
    ts        REAL NOT NULL,
    kind      TEXT NOT NULL,
    data      TEXT NOT NULL,
    blob      TEXT DEFAULT '',
    processed INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_raw_kind_proc ON events_raw(kind, processed);
CREATE INDEX IF NOT EXISTS idx_raw_ts ON events_raw(ts);

CREATE VIRTUAL TABLE IF NOT EXISTS events_raw_fts USING fts5(
    data, content=events_raw, content_rowid=id
);
CREATE TRIGGER IF NOT EXISTS events_raw_ai AFTER INSERT ON events_raw BEGIN
    INSERT INTO events_raw_fts(rowid, data) VALUES (new.id, new.data);
END;
CREATE TRIGGER IF NOT EXISTS events_raw_ad AFTER DELETE ON events_raw BEGIN
    INSERT INTO events_raw_fts(events_raw_fts, rowid, data)
        VALUES ('delete', old.id, old.data);
END;
"""


class Store:
    def __init__(self, db_path: Path) -> None:
        self._path = str(db_path)
        self._local = threading.local()
        self._init_db(self._conn)

    @property
    def _conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self._path)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            self._init_db(conn)
            self._local.conn = conn
        return conn

    def _init_db(self, conn: sqlite3.Connection) -> None:
        existing = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table','trigger')"
            )
        }
        conn.executescript(_SCHEMA)
        if "events_raw_fts" not in existing:
            conn.execute("INSERT INTO events_raw_fts(rowid, data) SELECT id, data FROM events_raw")
            conn.commit()

    # ── Write ──

    def insert_raw(self, events: list[Event]) -> None:
        if not events:
            return
        rows = [
            (e.timestamp, e.kind, json.dumps(e.data, ensure_ascii=False), e.blob) for e in events
        ]
        conn = self._conn
        conn.executemany("INSERT INTO events_raw (ts, kind, data, blob) VALUES (?, ?, ?, ?)", rows)
        conn.commit()

    # ── Read ──

    def query_raw(
        self,
        kind: str | None = None,
        since: float | None = None,
        until: float | None = None,
        limit: int = 500,
    ) -> list[Event]:
        clauses, params = [], []
        if kind:
            clauses.append("kind = ?")
            params.append(kind)
        if since is not None:
            clauses.append("ts >= ?")
            params.append(since)
        if until is not None:
            clauses.append("ts <= ?")
            params.append(until)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT id, ts, kind, data, blob FROM events_raw{where} ORDER BY ts DESC LIMIT ?"
        params.append(limit)
        return [self._row_to_event(r) for r in self._conn.execute(sql, params)]

    def search(
        self,
        text: str,
        kind: str | None = None,
        since: float | None = None,
        until: float | None = None,
        limit: int = 100,
    ) -> list[Event]:
        # Treat input as keyword text, not FTS5 grammar; punctuation such as
        # `C++` or an unmatched quote must not break the search endpoint.
        terms = re.findall(r"[^\W_]+", text)
        if not terms:
            return []
        match_query = " ".join(f'"{term}"' for term in terms)
        clauses = ["events_raw_fts MATCH ?"]
        params: list = [match_query]
        if kind:
            clauses.append("e.kind = ?")
            params.append(kind)
        if since is not None:
            clauses.append("e.ts >= ?")
            params.append(since)
        if until is not None:
            clauses.append("e.ts <= ?")
            params.append(until)
        where = " AND ".join(clauses)
        sql = (
            f"SELECT e.id, e.ts, e.kind, e.data, e.blob "
            f"FROM events_raw e JOIN events_raw_fts ON e.id = events_raw_fts.rowid "
            f"WHERE {where} ORDER BY rank LIMIT ?"
        )
        params.append(limit)
        return [self._row_to_event(r) for r in self._conn.execute(sql, params)]

    @staticmethod
    def _row_to_event(row: tuple) -> Event:
        return Event(
            id=row[0],
            timestamp=row[1],
            kind=row[2],
            data=json.loads(row[3]),
            blob=row[4],
        )

    def count(self) -> int:
        """Total number of raw events."""
        row = self._conn.execute("SELECT COUNT(*) FROM events_raw").fetchone()
        return row[0] if row else 0

    def stats(self) -> list[dict]:
        """Per-kind event statistics: count, first timestamp, last timestamp."""
        rows = self._conn.execute(
            "SELECT kind, COUNT(*) as cnt, MIN(ts), MAX(ts) "
            "FROM events_raw GROUP BY kind ORDER BY cnt DESC"
        ).fetchall()
        return [{"kind": r[0], "count": r[1], "first": r[2], "last": r[3]} for r in rows]

    def close(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn:
            conn.close()
            self._local.conn = None
