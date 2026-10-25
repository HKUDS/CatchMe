from __future__ import annotations

import importlib
import threading
import time

import catchme.services as services
from catchme import summary_queue


def test_stop_persists_summary_completed_by_in_flight_worker(monkeypatch):
    started = threading.Event()
    release = threading.Event()
    stopped = threading.Event()
    saved_summaries = []
    node = {"node_id": "synthetic::action", "kind": "action", "summary": ""}
    summarize_module = importlib.import_module("catchme.pipelines.summarize")

    def blocking_summarize(target, llm, force):
        started.set()
        assert release.wait(timeout=3)
        target["summary"] = "completed synthetic summary"
        return True

    monkeypatch.setattr(summary_queue, "LLM", lambda: object())
    monkeypatch.setattr(services, "load_config", lambda: {})
    monkeypatch.setattr(summarize_module, "summarize_node", blocking_summarize)
    queue = summary_queue.SummaryQueue(save_fn=lambda: saved_summaries.append(node["summary"]))
    queue._write_notification = lambda target: None
    queue._last_save = time.time()
    queue._save_interval = 60.0

    try:
        queue.enqueue(node, level=0)
        assert started.wait(timeout=2)

        def stop_queue():
            queue.stop()
            stopped.set()

        stopper = threading.Thread(target=stop_queue)
        stopper.start()
        assert not stopped.wait(timeout=0.1), (
            "stop returned before its active summary worker finished"
        )
        release.set()
        assert stopped.wait(timeout=3)
        stopper.join(timeout=1)
        assert node["summary"] == "completed synthetic summary"
        assert saved_summaries[-1] == "completed synthetic summary"
    finally:
        release.set()
        queue.stop()
        queue._dispatcher.join(timeout=2)
        queue._pool.shutdown(wait=True, cancel_futures=True)
