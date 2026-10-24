from __future__ import annotations

import asyncio
import threading

from catchme import mcp_server


def test_search_activity_keeps_event_loop_responsive(monkeypatch):
    started = threading.Event()
    release = threading.Event()

    def blocking_retrieval(query: str) -> dict:
        started.set()
        assert release.wait(timeout=2)
        return {"answer": query, "sources": []}

    monkeypatch.setattr(mcp_server, "_collect_search", blocking_retrieval)

    async def run_search() -> dict:
        search = asyncio.create_task(mcp_server._search_activity("synthetic query"))
        assert await asyncio.to_thread(started.wait, 1)
        heartbeat = asyncio.create_task(asyncio.sleep(0, result={"responsive": True}))
        try:
            assert await asyncio.wait_for(heartbeat, timeout=0.2) == {"responsive": True}
        finally:
            release.set()
        return await search

    assert asyncio.run(run_search()) == {"answer": "synthetic query", "sources": []}
