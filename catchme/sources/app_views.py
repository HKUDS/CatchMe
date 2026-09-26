"""Product-level views, tailored to the evidence each app can actually provide."""

from __future__ import annotations

VIEWS = {
    "documents": (
        "最近文档",
        ["document_recent", "document_opened"],
        "documents",
        "搜索文档名称或路径…",
    ),
    "attachments": ("微信文件", ["attachment_available"], "documents", "搜索微信里的文件…"),
    "opened": ("文件查看", ["document_opened"], "timeline", "搜索看过的微信文件…"),
    "history": ("浏览历史", ["browser_visit"], "web", "搜索网页标题、网址…"),
    "bookmarks": ("书签", ["bookmark"], "bookmarks", "搜索书签或文件夹…"),
    "downloads": ("下载", ["download"], "documents", "搜索下载文件或来源…"),
    "workspaces": ("工作区与文件", ["workspace_recent"], "projects", "搜索项目、文件或工作区…"),
    "projects": ("创作工程", ["project_recent"], "projects", "搜索工程名称…"),
    "topics": ("对话主题", ["conversation_index"], "topics", "搜索对话主题…"),
    "screen": (
        "界面记录",
        ["visible_content", "input_changed", "window_context", "app_action"],
        "timeline",
        "搜索可读取的内容…",
    ),
    "changes": ("本地变化", ["file_metadata"], "documents", "搜索本地文件变化…"),
    "usage": (
        "使用足迹",
        ["foreground_sample", "window_context", "app_action"],
        "timeline",
        "搜索使用记录…",
    ),
}


def presentation(app):
    ident = app["id"]
    if ident in ("claude", "codex"):
        keys, heading = ["usage"], "对话会话"
    elif ident in ("excel", "word", "powerpoint"):
        keys, heading = (
            ["documents", "usage"],
            {"excel": "我的表格", "word": "我的文档", "powerpoint": "我的演示文稿"}[ident],
        )
    elif ident == "wechat":
        keys, heading = ["attachments", "opened", "usage"], "微信里的文件与日常"
    elif ident in ("safari", "chrome"):
        keys, heading = ["history", "bookmarks", "downloads", "usage"], "浏览与收藏"
    elif ident in ("cursor", "vscode"):
        keys, heading = (
            ["workspaces", *(["topics"] if ident == "cursor" else []), "usage"],
            "项目与工作区",
        )
    elif ident == "capcut":
        keys, heading = ["projects", "usage"], "我的创作工程"
    elif ident == "notion":
        keys, heading = ["usage", "changes"], "Notion 使用与页面记录"
    else:
        keys, heading = ["usage"], "应用使用记录"
    if app.get("mode") == "full":
        keys.append("screen")
    tabs = []
    for key in keys:
        label, kinds, layout, placeholder = VIEWS[key]
        if key == "screen":
            label = (
                "聊天界面"
                if ident in ("wechat", "chatgpt")
                else "编辑过程"
                if ident in ("excel", "word", "powerpoint", "cursor", "vscode")
                else "可读页面"
            )
        if ident == "powerpoint" and key == "documents":
            label = "演示文稿"
        elif ident == "excel" and key == "documents":
            label = "表格"
        tabs.append({"id": key, "label": label, "layout": layout, "placeholder": placeholder})
    return {
        "type": "sessions" if ident in ("claude", "codex") else "content",
        "heading": heading,
        "tabs": tabs,
    }


def content_page(store, app_id, tab, query="", before=None, limit=30):
    import json
    import math

    from .apps import definition, predicate

    app = definition(app_id)
    if tab not in VIEWS:
        raise ValueError("未知的应用视图")
    _, kinds, layout, _ = VIEWS[tab]
    where, args = predicate(app)
    where += " AND kind IN (" + ",".join("?" for _ in kinds) + ")"
    args.extend(kinds)
    if query:
        text = query[:200].replace("!", "!!").replace("%", "!%").replace("_", "!_")
        where += " AND (title LIKE ? ESCAPE '!' OR payload LIKE ? ESCAPE '!')"
        args.extend([f"%{text}%"] * 2)
    grouped = layout in ("documents", "projects", "topics", "bookmarks")
    identity = "COALESCE(json_extract(payload,'$.file'),json_extract(payload,'$.uri'),json_extract(payload,'$.draft_fold_path'),json_extract(payload,'$.conversation_id'),json_extract(payload,'$.url'),CAST(id AS TEXT))"
    if tab == "bookmarks":
        identity = f"json_array({identity},json_extract(payload,'$.folder'),json_extract(payload,'$.profile'))"
    sql = "WITH selected AS (SELECT *, "
    sql += (
        f"ROW_NUMBER() OVER (PARTITION BY {identity} ORDER BY ts DESC,id DESC) AS rank, COUNT(*) OVER (PARTITION BY {identity}) AS observations "
        if grouped
        else "1 AS rank,1 AS observations "
    )
    sql += "FROM activity WHERE " + where + ") "
    outer, paging = "rank=1", []
    if before:
        try:
            ts, row_id = before.split(":")
            ts, row_id = float(ts), int(row_id)
            if not math.isfinite(ts):
                raise ValueError()
        except (ValueError, AttributeError):
            raise ValueError("无效的记录分页") from None
        outer += " AND (ts<? OR (ts=? AND id<?))"
        paging = [ts, ts, row_id]
    with store.connect() as db:
        total = db.execute(sql + "SELECT COUNT(*) FROM selected WHERE rank=1", args).fetchone()[0]
        rows = db.execute(
            sql + "SELECT * FROM selected WHERE " + outer + " ORDER BY ts DESC,id DESC LIMIT ?",
            [*args, *paging, limit + 1],
        ).fetchall()
    events = [dict(r, payload=json.loads(r["payload"])) for r in rows[:limit]]
    return {
        "events": events,
        "total": total,
        "layout": layout,
        "next": f"{events[-1]['ts']}:{events[-1]['id']}" if len(rows) > limit else None,
    }
