"""CatchMe MCP Server — exposes the activity tree as MCP tools over stdio.

Start with:  catchme mcp

Register in Claude Desktop (claude_desktop_config.json)::

    {
      "mcpServers": {
        "catchme": {
          "command": "catchme",
          "args": ["mcp"]
        }
      }
    }

Tools
-----
search_activity(query, date="")  — Natural-language search over screen history.
list_days()                       — List all recorded days with summaries.
get_session(session_id)           — Full detail for one session node.
get_tree(date)                    — Full activity tree JSON for a given date.
"""

from __future__ import annotations

import asyncio
import json
import logging

log = logging.getLogger(__name__)


def _require_mcp():
    try:
        import mcp  # noqa: F401
    except ImportError as e:
        raise ImportError(
            "The 'mcp' package is required for MCP server mode.\n"
            "Install it with:  pip install 'catchme[mcp]'"
        ) from e


def _collect_search(query: str) -> dict:
    from .pipelines.retrieve import retrieve

    answer = "No relevant information found."
    sources: list[str] = []
    for step in retrieve(query):
        if step.get("type") == "answer":
            answer = step.get("content", answer)
            sources = step.get("sources", [])
    return {"answer": answer, "sources": sources}


async def _search_activity(query: str) -> dict:
    """Run synchronous retrieval without blocking the MCP event loop."""
    return await asyncio.to_thread(_collect_search, query)


def serve() -> None:
    """Start the CatchMe MCP stdio server. Blocks until the host disconnects."""
    _require_mcp()

    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import TextContent, Tool

    from .pipelines.retrieve import _load_all_trees, _node_index

    server = Server("catchme")

    # ── Tool definitions ────────────────────────────────────────────────────

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="search_activity",
                description=(
                    "Search your recorded screen activity using natural language. "
                    "Returns the answer and the source node IDs used to build it. "
                    "Optionally scope to a specific date (YYYY-MM-DD)."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language question about your activity.",
                        },
                        "date": {
                            "type": "string",
                            "description": "Optional ISO date to restrict search (YYYY-MM-DD).",
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="list_days",
                description="List all days that have recorded activity, with top-level summaries.",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="get_session",
                description=(
                    "Get full detail for a specific session node, including app and "
                    "location breakdown. Use list_days first to find session IDs."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "The node_id of the session (e.g. '2026-04-15::s0').",
                        }
                    },
                    "required": ["session_id"],
                },
            ),
            Tool(
                name="get_tree",
                description="Return the full raw activity tree JSON for a given date (YYYY-MM-DD).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "ISO date string, e.g. '2026-04-15'.",
                        }
                    },
                    "required": ["date"],
                },
            ),
        ]

    # ── Tool handlers ───────────────────────────────────────────────────────

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        if name == "search_activity":
            return await _handle_search(arguments)
        if name == "list_days":
            return _handle_list_days()
        if name == "get_session":
            return _handle_get_session(arguments)
        if name == "get_tree":
            return _handle_get_tree(arguments)
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    # ── search_activity ─────────────────────────────────────────────────────

    async def _handle_search(args: dict) -> list[TextContent]:
        query = args.get("query", "").strip()
        date_hint = args.get("date", "").strip()
        if date_hint:
            query = f"{query} on {date_hint}"
        if not query:
            return [TextContent(type="text", text="Error: query is required.")]

        try:
            result = await _search_activity(query)
        except Exception as exc:
            log.exception("retrieve() failed")
            return [TextContent(type="text", text=f"Error during retrieval: {exc}")]

        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    # ── list_days ────────────────────────────────────────────────────────────

    def _handle_list_days() -> list[TextContent]:
        trees = _load_all_trees()
        if not trees:
            return [TextContent(type="text", text=json.dumps([]))]
        days = []
        for t in trees:
            node = t.get("tree", {})
            days.append(
                {
                    "date": t.get("date", node.get("title", "?")),
                    "node_id": node.get("node_id", ""),
                    "summary": (node.get("summary") or "")[:300],
                    "session_count": len(node.get("children", [])),
                }
            )
        return [TextContent(type="text", text=json.dumps(days, ensure_ascii=False, indent=2))]

    # ── get_session ──────────────────────────────────────────────────────────

    def _handle_get_session(args: dict) -> list[TextContent]:
        session_id = args.get("session_id", "").strip()
        if not session_id:
            return [TextContent(type="text", text="Error: session_id is required.")]
        trees = _load_all_trees()
        idx: dict = {}
        for t in trees:
            _node_index(t.get("tree", {}), idx)
        node = idx.get(session_id)
        if not node:
            return [TextContent(type="text", text=f"Session '{session_id}' not found.")]

        def _slim(n: dict, depth: int = 0) -> dict:
            """Return a summary-only view to keep payload reasonable."""
            out = {
                "node_id": n.get("node_id"),
                "kind": n.get("kind"),
                "title": n.get("title"),
                "summary": (n.get("summary") or "")[:500],
            }
            if depth < 2:
                out["children"] = [_slim(c, depth + 1) for c in n.get("children", [])]
            return out

        return [
            TextContent(type="text", text=json.dumps(_slim(node), ensure_ascii=False, indent=2))
        ]

    # ── get_tree ─────────────────────────────────────────────────────────────

    def _handle_get_tree(args: dict) -> list[TextContent]:
        date = args.get("date", "").strip()
        if not date:
            return [TextContent(type="text", text="Error: date is required (YYYY-MM-DD).")]
        trees = _load_all_trees()
        matched = [t for t in trees if t.get("date") == date]
        if not matched:
            return [TextContent(type="text", text=f"No activity tree found for date '{date}'.")]
        tree_data = matched[0].get("tree", {})
        return [TextContent(type="text", text=json.dumps(tree_data, ensure_ascii=False, indent=2))]

    # ── run ──────────────────────────────────────────────────────────────────

    async def _run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(_run())
