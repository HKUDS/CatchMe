"""Session-first queries, with stable pagination and complete chronological transcripts."""

from __future__ import annotations

import json
import math

from .apps import definition

SESSION_EXPR = "COALESCE(json_extract(payload,'$.session_id'),json_extract(payload,'$.file'))"
KINDS = "('conversation','tool_call','tool_result','capture_gap')"
TRANSCRIPT_PAGE_BYTES = 2 * 1024 * 1024


def session_scope(app_id):
    definition(app_id)
    if app_id not in ("claude", "codex"):
        raise ValueError("这个应用没有可读取的本地聊天历史")
    return (
        f"source=? AND kind IN {KINDS} AND {SESSION_EXPR} IS NOT NULL",
        [app_id + ".sessions"],
    )


def cursor_value(value):
    try:
        ts, key = json.loads(value)
        if not isinstance(ts, (int, float)) or not math.isfinite(ts) or not isinstance(key, str):
            raise ValueError()
        return ts, key
    except (ValueError, TypeError):
        raise ValueError("无效的会话分页") from None


def list_sessions(store, app_id, query="", before=None, limit=30):
    where, args = session_scope(app_id)
    search = query[:200].replace("!", "!!").replace("%", "!%").replace("_", "!_")
    having, tail_args = [], []
    if search:
        having.append("MAX(title LIKE ? ESCAPE '!' OR payload LIKE ? ESCAPE '!')=1")
        tail_args.extend([f"%{search}%"] * 2)
    if before:
        ts, sid = cursor_value(before)
        having.append("(MAX(ts) < ? OR (MAX(ts)=? AND " + SESSION_EXPR + " < ?))")
        tail_args.extend([ts, ts, sid])
    sql = (
        "SELECT "
        + SESSION_EXPR
        + " AS session_id, MAX(json_extract(payload,'$.project')) AS project, "
        "MIN(ts) AS started, MAX(ts) AS updated, COUNT(*) AS count, "
        "SUM(kind='conversation') AS messages,SUM(kind IN ('tool_call','tool_result')) AS tools, "
        "SUM(kind='capture_gap' OR json_extract(payload,'$.truncated')=1) AS gaps "
        "FROM activity WHERE " + where + " GROUP BY " + SESSION_EXPR
    )
    if having:
        sql += " HAVING " + " AND ".join(having)
    sql += " ORDER BY updated DESC,session_id DESC LIMIT ?"
    with store.connect() as db:
        total = db.execute(
            "SELECT COUNT(DISTINCT " + SESSION_EXPR + ") FROM activity WHERE " + where, args
        ).fetchone()[0]
        rows = [dict(r) for r in db.execute(sql, [*args, *tail_args, limit + 1])]
        page = rows[:limit]
        for row in page:
            title = db.execute(
                "SELECT title FROM activity WHERE "
                + where
                + " AND "
                + SESSION_EXPR
                + "=? ORDER BY CASE WHEN kind='conversation' AND json_extract(payload,'$.role')='user' "
                "AND substr(ltrim(title),1,1)!='<' THEN 0 ELSE 1 END,ts,id LIMIT 1",
                [*args, row["session_id"]],
            ).fetchone()[0]
            row["title"] = (
                title[:180] if title and not title.lstrip().startswith("<") else "本地对话"
            )
    return {
        "sessions": page,
        "total": total,
        "next": json.dumps([page[-1]["updated"], page[-1]["session_id"]])
        if len(rows) > limit
        else None,
    }


def transcript_page(store, app_id, session_id, after=None, limit=80):
    if not isinstance(session_id, str) or not session_id or len(session_id) > 4096:
        raise ValueError("请选择一个对话会话")
    where, args = session_scope(app_id)
    where += " AND " + SESSION_EXPR + "=?"
    args.append(session_id)
    with store.connect() as db:
        stats = db.execute(
            "SELECT COUNT(*) AS total,MIN(ts) AS started,MAX(ts) AS updated,"
            "MAX(json_extract(payload,'$.project')) AS project FROM activity WHERE " + where,
            args,
        ).fetchone()
        if not stats["total"]:
            raise ValueError("没有找到这个会话的聊天记录")
        if after:
            ts, key = cursor_value(after)
            if not key.isdigit():
                raise ValueError("无效的聊天分页")
            where += " AND (ts>? OR (ts=? AND id>?))"
            args.extend([ts, ts, int(key)])
        rows = db.execute(
            "SELECT * FROM activity WHERE " + where + " ORDER BY ts,id LIMIT ?", [*args, limit + 1]
        )
        events, size, more = [], 0, False
        for row in rows:
            row_size = len(row["payload"].encode("utf-8"))
            # Keep each message intact, even when the first message exceeds the budget.
            if events and (len(events) >= limit or size + row_size > TRANSCRIPT_PAGE_BYTES):
                more = True
                break
            events.append(dict(row, payload=json.loads(row["payload"])))
            size += row_size
    return {
        "session_id": session_id,
        **dict(stats),
        "events": events,
        "next": json.dumps([events[-1]["ts"], str(events[-1]["id"])]) if more else None,
    }
