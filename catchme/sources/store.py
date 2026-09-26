"""Versioned activity storage; source checkpoints and events commit together."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS source_locations (source TEXT PRIMARY KEY, paths TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS app_preferences (id TEXT PRIMARY KEY, enabled INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS sources (
 id TEXT PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL,
 reader TEXT NOT NULL, paths TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 0,
 status TEXT NOT NULL, detail TEXT NOT NULL, checked REAL, collected REAL,
 error TEXT, cursor TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS applications (
 id TEXT PRIMARY KEY, name TEXT, category TEXT, path TEXT, version TEXT
);
CREATE TABLE IF NOT EXISTS activity (
 id INTEGER PRIMARY KEY, source TEXT NOT NULL, external_id TEXT NOT NULL,
 ts REAL NOT NULL, observed REAL NOT NULL, app TEXT NOT NULL,
 category TEXT NOT NULL, kind TEXT NOT NULL, title TEXT NOT NULL,
 payload TEXT NOT NULL, UNIQUE(source, external_id)
);
CREATE INDEX IF NOT EXISTS activity_session_lookup ON activity(
 source,COALESCE(json_extract(payload,'$.session_id'),json_extract(payload,'$.file')),
 ts,id,kind,json_extract(payload,'$.project'),json_extract(payload,'$.role'),
 json_extract(payload,'$.truncated'),title
);
CREATE INDEX IF NOT EXISTS activity_time ON activity(ts DESC, id DESC);
CREATE INDEX IF NOT EXISTS activity_source_time ON activity(source, ts DESC);
CREATE INDEX IF NOT EXISTS activity_kind_app ON activity(kind, app, ts);
CREATE TABLE IF NOT EXISTS analyses (
 id INTEGER PRIMARY KEY, created REAL, since REAL, until REAL,
 service TEXT, model TEXT, facts TEXT, answer TEXT
);
"""


class ActivityStore:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version > 4:
                raise RuntimeError("Activity database is newer than this CatchMe version")
            db.executescript(SCHEMA)
            columns = {r[1] for r in db.execute("PRAGMA table_info(app_preferences)")}
            if "mode" not in columns:
                db.execute(
                    "ALTER TABLE app_preferences ADD COLUMN mode TEXT NOT NULL DEFAULT 'basic'"
                )
            if "consented" not in columns:
                db.execute("ALTER TABLE app_preferences ADD COLUMN consented REAL")
            db.execute("PRAGMA user_version=4")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA journal_mode=WAL")
            with db:
                yield db
        finally:
            db.close()

    def sources(self):
        with self.connect() as db:
            rows = db.execute("SELECT * FROM sources ORDER BY category, name").fetchall()
        return [
            dict(
                r,
                paths=json.loads(r["paths"]),
                enabled=bool(r["enabled"]),
                cursor=json.loads(r["cursor"]),
            )
            for r in rows
        ]

    def events(self, since, until, source="", category="", query="", limit=100, before=None):
        clauses = ["ts >= ?", "ts <= ?"]
        params = [since, until]
        for column, value in [("source", source), ("category", category)]:
            if value:
                clauses.append(f"{column} = ?")
                params.append(value)
        if query:
            clauses.append("(instr(lower(title), lower(?)) > 0 OR instr(lower(app), lower(?)) > 0)")
            params.extend([query, query])
        if before is not None:
            clauses.append("id < ?")
            params.append(before)
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM activity WHERE "
                + " AND ".join(clauses)
                + " ORDER BY id DESC LIMIT ?",
                [*params, limit + 1],
            ).fetchall()
        return {
            "events": [dict(r, payload=json.loads(r["payload"])) for r in rows[:limit]],
            "next": rows[limit - 1]["id"] if len(rows) > limit else None,
        }

    def facts(self, since, until, source="", category=""):
        where = "ts >= ? AND ts <= ?"
        params = [since, until]
        for col, val in [("source", source), ("category", category)]:
            if val:
                where += f" AND {col}=?"
                params.append(val)
        with self.connect() as db:
            total = db.execute(f"SELECT COUNT(*) FROM activity WHERE {where}", params).fetchone()[0]
            apps = [
                dict(r)
                for r in db.execute(
                    f"""SELECT app, category, COUNT(*) AS events,
                SUM(CASE WHEN kind='foreground_sample' THEN 1 ELSE 0 END) AS foreground_samples,
                SUM(CASE WHEN kind='foreground_sample' AND json_extract(payload, '$.idle')=0
                    THEN 1 ELSE 0 END) AS active_samples
                FROM activity WHERE {where} GROUP BY app, category ORDER BY events DESC LIMIT 30""",
                    params,
                )
            ]
            kinds = [
                dict(r)
                for r in db.execute(
                    f"SELECT kind, COUNT(*) AS events FROM activity WHERE {where} GROUP BY kind",
                    params,
                )
            ]
            hours = [
                dict(r)
                for r in db.execute(
                    f"SELECT CAST(ts/3600 AS INTEGER)*3600 AS ts, COUNT(*) AS events FROM activity WHERE {where} GROUP BY 1 ORDER BY 1",
                    params,
                )
            ]
        return {
            "since": since,
            "until": until,
            "total": total,
            "apps": apps,
            "kinds": kinds,
            "hours": hours,
            "source": source,
            "category": category,
            "note": "Event counts measure observations, not productivity or time spent. Foreground samples are point observations; idle samples are excluded from active_samples.",
        }
