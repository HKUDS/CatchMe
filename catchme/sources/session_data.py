"""Semantic data from local assistant session formats, without executing recorded tools."""

from __future__ import annotations

import json


def metadata(obj, reader, previous, fallback):
    result = dict(previous)
    result.setdefault("session_id", fallback)
    if reader == "claude":
        for key, target in (
            ("sessionId", "session_id"),
            ("cwd", "project"),
            ("gitBranch", "branch"),
        ):
            if isinstance(obj.get(key), str):
                result[target] = obj[key][:1000]
        message = obj.get("message")
        if isinstance(message, dict) and isinstance(message.get("model"), str):
            result["model"] = message["model"]
    elif obj.get("type") == "session_meta" and isinstance(obj.get("payload"), dict):
        payload = obj["payload"]
        for key, target in (
            ("id", "session_id"),
            ("cwd", "project"),
            ("model_provider", "provider"),
            ("originator", "originator"),
        ):
            if isinstance(payload.get(key), str):
                result[target] = payload[key][:1000]
    elif obj.get("type") == "turn_context" and isinstance(obj.get("payload"), dict):
        for key in ("model", "cwd"):
            value = obj["payload"].get(key)
            if isinstance(value, str):
                result["project" if key == "cwd" else key] = value[:1000]
    return result


def safe_text(value):
    if isinstance(value, str):
        return value[:16000]
    if isinstance(value, list):
        return "\n".join(
            b.get("text", "")
            for b in value
            if isinstance(b, dict)
            and b.get("type") in ("text", "input_text", "output_text")
            and isinstance(b.get("text"), str)
        )[:16000]
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)[:16000]
    return ""


def tools_in(obj, reader):
    items = []
    if reader == "claude":
        message = obj.get("message")
        content = message.get("content", []) if isinstance(message, dict) else []
        if not isinstance(content, list):
            return []
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                items.append(
                    (
                        "tool_call",
                        str(block.get("name", "工具调用")),
                        {
                            "tool": block.get("name"),
                            "call_id": block.get("id"),
                            "text": safe_text(block.get("input")),
                        },
                    )
                )
            elif block.get("type") == "tool_result":
                items.append(
                    (
                        "tool_result",
                        "工具返回结果",
                        {
                            "call_id": block.get("tool_use_id"),
                            "text": safe_text(block.get("content")),
                            "is_error": bool(block.get("is_error")),
                        },
                    )
                )
    elif obj.get("type") == "response_item" and isinstance(obj.get("payload"), dict):
        payload = obj["payload"]
        kind = payload.get("type")
        if kind in ("function_call", "custom_tool_call"):
            items.append(
                (
                    "tool_call",
                    str(payload.get("name", "工具调用")),
                    {
                        "tool": payload.get("name"),
                        "call_id": payload.get("call_id"),
                        "text": safe_text(payload.get("arguments", payload.get("input"))),
                    },
                )
            )
        elif kind in ("function_call_output", "custom_tool_call_output"):
            items.append(
                (
                    "tool_result",
                    "工具返回结果",
                    {"call_id": payload.get("call_id"), "text": safe_text(payload.get("output"))},
                )
            )
    return items
