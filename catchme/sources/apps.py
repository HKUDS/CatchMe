"""User-facing app catalog: one monitoring preference per app, across its readers."""

from __future__ import annotations

import json
import time

# IDs are stable preferences, separate from platform bundle IDs and reader IDs.
APPS = [
    dict(
        id="excel",
        name="Excel",
        category="office",
        description="表格里的灵感与进展",
        color="#e8f4eb",
        bundles=["com.microsoft.Excel"],
        aliases=["Microsoft Excel", "Excel"],
        sources=["app.com.microsoft.Excel"],
        capabilities=["最近文档", "应用使用记录"],
    ),
    dict(
        id="powerpoint",
        name="PowerPoint",
        category="office",
        description="每一次演示，都有准备的轨迹",
        color="#fff0e8",
        bundles=["com.microsoft.Powerpoint"],
        aliases=["Microsoft PowerPoint", "PowerPoint"],
        sources=["app.com.microsoft.Powerpoint"],
        capabilities=["最近演示文稿", "应用使用记录"],
    ),
    dict(
        id="word",
        name="Word",
        category="office",
        description="写下的想法，留下的足迹",
        color="#eaf1ff",
        bundles=["com.microsoft.Word"],
        aliases=["Microsoft Word", "Word"],
        sources=["app.com.microsoft.Word"],
        capabilities=["最近文档", "应用使用记录"],
    ),
    dict(
        id="wechat",
        name="微信",
        category="social",
        description="记录与人连接的时刻",
        color="#e9f7e7",
        bundles=["com.tencent.xinWeChat"],
        aliases=["WeChat", "微信"],
        sources=["wechat.files"],
        capabilities=["微信文件", "文件打开记录", "应用使用记录"],
        note="基础模式记录微信文件和使用情况；完整模式可记录当前可读取的聊天界面与输入变化，不保证覆盖所有收发消息。",
    ),
    dict(
        id="claude",
        name="Claude",
        category="ai",
        description="和 AI 一起想过的那些事",
        color="#fbede6",
        bundles=["com.anthropic.claudefordesktop"],
        aliases=["Claude", "Claude Code"],
        sources=["claude.sessions", "logs.Claude"],
        capabilities=["本地 Claude Code 会话", "项目关联", "工具调用（完整模式）"],
        note="本地会话来自 Claude Code；完整模式还可回填已有的工具调用，并记录可读取的前台界面。",
    ),
    dict(
        id="codex",
        name="Codex",
        category="ai",
        description="本地会话里的思路、代码与行动",
        color="#e9eeef",
        bundles=["com.openai.codex"],
        aliases=["Codex", "Codex CLI"],
        sources=["codex.sessions"],
        capabilities=["本地对话与会话", "项目关联", "工具调用（完整模式）"],
        note="直接读取本地 Codex 会话文件。完整模式还可回填文件中已有的工具调用和结果；不包含模型隐藏推理或未落盘内容。",
    ),
    dict(
        id="chatgpt",
        name="ChatGPT",
        category="ai",
        description="让每次好奇，都有回声",
        color="#e9f4f0",
        bundles=["com.openai.chat", "com.openai.ChatGPT"],
        aliases=["ChatGPT"],
        sources=[],
        capabilities=["应用使用记录"],
        note="基础模式记录使用情况；完整模式记录当前可读取的对话界面与输入变化，无法读取未显示的消息。",
    ),
    dict(
        id="cursor",
        name="Cursor",
        category="development",
        description="从一个想法，到一段代码",
        color="#efedf7",
        bundles=["com.todesktop.230313mzl4w4u92"],
        aliases=["Cursor", "Cursor conversations"],
        sources=["editor.cursor", "cursor.conversations"],
        capabilities=["最近工作区", "对话主题", "应用使用记录"],
    ),
    dict(
        id="vscode",
        name="VS Code",
        category="development",
        description="项目与文件，随时接着来",
        color="#e8f4fc",
        bundles=["com.microsoft.VSCode"],
        aliases=["Code", "Visual Studio Code"],
        sources=["editor.code"],
        capabilities=["最近工作区", "应用使用记录"],
    ),
    dict(
        id="capcut",
        name="CapCut",
        category="creative",
        description="剪辑时间里的创作片段",
        color="#f4edf8",
        bundles=["com.lemon.lvoverseas"],
        aliases=["CapCut", "CapCut projects"],
        sources=["projects.capcut", "app.com.lemon.lvoverseas"],
        capabilities=["最近工程", "工程更新时间"],
    ),
    dict(
        id="notion",
        name="Notion",
        category="office",
        description="整理想法，也记得来时的路",
        color="#f0efe9",
        bundles=["notion.id"],
        aliases=["Notion", "Notion logs"],
        sources=["logs.Notion", "app.notion.id"],
        capabilities=["应用使用记录", "本地文件变化"],
    ),
    dict(
        id="safari",
        name="Safari",
        category="browser",
        description="走过的网页，再次遇见",
        color="#eaf3fc",
        bundles=["com.apple.Safari"],
        aliases=["Safari"],
        sources=["safari.history", "safari.bookmarks", "safari.downloads"],
        capabilities=["浏览历史", "书签与文件夹", "下载记录"],
        note="直接读取 Safari 本地记录。书签时间是索引更新时间；下载记录不代表下载成功。部分记录需要完全磁盘访问权限。",
    ),
    dict(
        id="chrome",
        name="Chrome",
        category="browser",
        description="收藏之外，还有浏览的记忆",
        color="#fbf3e3",
        bundles=["com.google.Chrome"],
        aliases=["Google Chrome", "Chrome"],
        sources=["chrome.history", "chrome.bookmarks", "chrome.downloads"],
        capabilities=["多配置浏览历史", "书签与文件夹", "下载记录"],
    ),
]


FULL_APPS = {
    "excel",
    "powerpoint",
    "word",
    "wechat",
    "claude",
    "codex",
    "chatgpt",
    "cursor",
    "vscode",
    "notion",
}


def monitoring_settings(db):
    prefs = preferences(db)
    saved = {r["id"]: dict(r) for r in db.execute("SELECT * FROM app_preferences")}
    return {
        a["id"]: {
            "enabled": prefs[a["id"]],
            "mode": saved.get(a["id"], {}).get("mode", "basic"),
            "consented": saved.get(a["id"], {}).get("consented"),
        }
        for a in APPS
    }


def set_mode(store, app_id, mode, consent=False):
    definition(app_id)
    if mode not in ("basic", "full"):
        raise ValueError("请选择基础记录或完整监控")
    if mode == "full" and app_id not in FULL_APPS:
        raise ValueError("这个应用暂不支持完整监控")
    if mode == "full" and consent is not True:
        raise ValueError("请先确认此应用的完整监控范围")
    with store.connect() as db:
        enabled = preferences(db)[app_id]
        db.execute(
            "INSERT INTO app_preferences(id,enabled,mode,consented) VALUES(?,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET mode=excluded.mode,consented=excluded.consented",
            (app_id, enabled, mode, time.time() if mode == "full" else None),
        )


def definition(app_id):
    app = next((a for a in APPS if a["id"] == app_id), None)
    if app is None:
        raise ValueError("未找到这个应用")
    return app


def match_app(name, payload=None, source=None):
    # Names disambiguate installations whose bundle identifier is reused (ChatGPT/Codex).
    for a in APPS:
        if name in a["aliases"] or source in a["sources"]:
            return a
    bundle = (payload or {}).get("bundle_id")
    return next((a for a in APPS if bundle in a["bundles"]), None)


def preferences(db):
    overrides = {r["id"]: bool(r["enabled"]) for r in db.execute("SELECT * FROM app_preferences")}
    enabled_sources = {r[0] for r in db.execute("SELECT id FROM sources WHERE enabled=1")}
    return {
        a["id"]: overrides.get(a["id"], bool(enabled_sources.intersection(a["sources"])))
        for a in APPS
    }


def predicate(app):
    ids = app["sources"]
    # Bundle matching complements localized names, but app records are never matched by category.
    clauses, params = ["source=?"], ["live." + app["id"]]
    if ids:
        clauses.append("source IN (" + ",".join("?" for _ in ids) + ")")
        params.extend(ids)
    aliases = app["aliases"]
    others = [name for other in APPS if other["id"] != app["id"] for name in other["aliases"]]
    clauses.append(
        "(kind='foreground_sample' AND (app IN ("
        + ",".join("?" for _ in aliases)
        + ") OR (json_extract(payload,'$.bundle_id') IN ("
        + ",".join("?" for _ in app["bundles"])
        + ") AND app NOT IN ("
        + ",".join("?" for _ in others)
        + "))))"
    )
    params.extend(aliases + app["bundles"] + others)
    return "(" + " OR ".join(clauses) + ")", params


def gallery(store):
    with store.connect() as db:
        prefs = preferences(db)
        settings = monitoring_settings(db)
        installed = [dict(r) for r in db.execute("SELECT * FROM applications")]
        sources = {s["id"]: dict(s) for s in db.execute("SELECT * FROM sources")}
        result = []
        for a in APPS:
            from .app_views import presentation

            where, args = predicate(a)
            stats = db.execute(
                "SELECT COUNT(*) AS count,MAX(ts) AS last FROM activity WHERE " + where, args
            ).fetchone()
            detected = any(i["id"] in a["bundles"] or i["name"] in a["aliases"] for i in installed)
            available = any(
                sources.get(s, {}).get("status") in ("available", "partial") for s in a["sources"]
            )
            last_sync = max(
                (
                    sources.get(s, {}).get("collected") or 0
                    for s in [*a["sources"], "system.foreground"]
                ),
                default=0,
            )
            result.append(
                {
                    **a,
                    "presentation": presentation({**a, "mode": settings[a["id"]]["mode"]}),
                    "session_count": db.execute(
                        "SELECT COUNT(DISTINCT COALESCE(json_extract(payload,'$.session_id'),json_extract(payload,'$.file'))) FROM activity WHERE source=? AND kind IN ('conversation','tool_call','tool_result','capture_gap')",
                        (a["id"] + ".sessions",),
                    ).fetchone()[0]
                    if a["id"] in ("claude", "codex")
                    else None,
                    "enabled": prefs[a["id"]],
                    "mode": settings[a["id"]]["mode"],
                    "full_supported": a["id"] in FULL_APPS,
                    "source_issues": sum(
                        sources.get(s, {}).get("status")
                        in ("error", "permission_required", "unavailable", "partial")
                        for s in a["sources"]
                    ),
                    "installed": detected,
                    "available": detected or available,
                    "count": stats["count"],
                    "last": stats["last"],
                    "last_sync": last_sync,
                    "needs_permission": any(
                        sources.get(s, {}).get("status") == "permission_required"
                        for s in a["sources"]
                    ),
                }
            )
    return result


def set_monitoring(store, app_id, enabled):
    a = definition(app_id)
    with store.connect() as db:
        db.execute(
            "INSERT INTO app_preferences(id,enabled) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET enabled=excluded.enabled",
            (app_id, enabled),
        )
        for sid in a["sources"]:
            db.execute(
                "UPDATE sources SET enabled=? WHERE id=? AND (status NOT IN ('missing','unsupported') OR ?=0)",
                (enabled, sid, enabled),
            )
        db.execute(
            "UPDATE app_preferences SET consented=? WHERE id=? AND mode='full'",
            (time.time(), app_id),
        )
        if enabled:
            db.execute("UPDATE sources SET enabled=1 WHERE id='system.foreground'")


def recent(store, app_id, limit=30, before=None, kind=None, query="", session=None):
    a = definition(app_id)
    where, args = predicate(a)
    filters = {
        "files": [
            "attachment_available",
            "document_opened",
            "document_recent",
            "workspace_recent",
            "project_recent",
            "download",
        ],
        "content": ["conversation", "visible_content", "conversation_index", "input_changed"],
        "browsing": ["browser_visit", "bookmark", "download"],
        "actions": ["app_action", "window_context", "tool_call", "tool_result"],
    }
    if kind and kind != "all":
        if kind not in filters:
            raise ValueError("未知活动类型")
        where += " AND kind IN (" + ",".join("?" for _ in filters[kind]) + ")"
        args += filters[kind]
    if session:
        where += (
            " AND COALESCE(json_extract(payload,'$.session_id'),json_extract(payload,'$.file'))=?"
        )
        args.append(session)
    if query:
        query = query[:200].replace("!", "!!").replace("%", "!%").replace("_", "!_")
        where += " AND (title LIKE ? ESCAPE '!' OR payload LIKE ? ESCAPE '!')"
        args += ["%" + query + "%"] * 2
    if before:
        try:
            ts, rowid = before.split(":")
            ts, rowid = float(ts), int(rowid)
        except (ValueError, AttributeError) as exc:
            raise ValueError("无效的活动分页") from exc
        where += " AND (ts < ? OR (ts=? AND id<?))"
        args += [ts, ts, rowid]
    with store.connect() as db:
        rows = db.execute(
            "SELECT * FROM activity WHERE " + where + " ORDER BY ts DESC,id DESC LIMIT ?",
            [*args, limit + 1],
        ).fetchall()
    events = [dict(r, payload=json.loads(r["payload"])) for r in rows[:limit]]
    return {
        "events": events,
        "next": f"{events[-1]['ts']}:{events[-1]['id']}" if len(rows) > limit else None,
        "updated": time.time(),
    }


def sessions(store, app_id):
    app = definition(app_id)
    if app_id not in ("claude", "codex"):
        return []
    where, args = predicate(app)
    with store.connect() as db:
        rows = db.execute(
            "SELECT COALESCE(json_extract(payload,'$.session_id'),json_extract(payload,'$.file')) AS session_id, "
            "MAX(json_extract(payload,'$.project')) AS project, MIN(ts) AS started, MAX(ts) AS updated, "
            "COALESCE(MIN(CASE WHEN json_extract(payload,'$.role')='user' AND substr(ltrim(title),1,1)!='<' THEN id END),MIN(id)) AS first_record, COUNT(*) AS count, SUM(kind='conversation') AS messages, SUM(kind IN ('tool_call','tool_result')) AS tools "
            "FROM activity WHERE "
            + where
            + " AND kind IN ('conversation','tool_call','tool_result') "
            "GROUP BY session_id ORDER BY updated DESC LIMIT 100",
            args,
        ).fetchall()
        titles = (
            {
                r["id"]: r["title"]
                for r in db.execute(
                    "SELECT id,title FROM activity WHERE id IN ("
                    + ",".join("?" for _ in rows)
                    + ")",
                    [r["first_record"] for r in rows],
                )
            }
            if rows
            else {}
        )
    return [
        {**dict(r), "title": titles.get(r["first_record"], "")[:180]}
        for r in rows
        if r["session_id"]
    ]
