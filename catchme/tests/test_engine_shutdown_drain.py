from __future__ import annotations

import threading
from queue import Queue

from catchme.config import Config
from catchme.engine import Engine
from catchme.store import Event


class _ObservedQueue(Queue):
    def __init__(self):
        super().__init__()
        self.item_consumed = threading.Event()

    def get(self, block=True, timeout=None):
        item = super().get(block=block, timeout=timeout)
        self.item_consumed.set()
        return item


def test_stop_waits_for_writer_to_persist_dequeued_event(cfg, store):
    slow_batch_config = Config(root=cfg.root, batch_size=100, batch_timeout=8.0)
    engine = Engine(slow_batch_config, store, [])
    observed_queue = _ObservedQueue()
    engine._queue = observed_queue
    engine._organizer.stop = lambda: None
    engine._writer = threading.Thread(target=engine._write_loop, daemon=True)
    engine._writer.start()
    observed_queue.put(Event(timestamp=1.0, kind="synthetic", data={"value": 1}))
    assert observed_queue.item_consumed.wait(timeout=2)

    stopped = threading.Event()

    def stop_engine():
        engine.stop()
        stopped.set()

    stopper = threading.Thread(target=stop_engine, daemon=True)
    stopper.start()
    try:
        assert not stopped.wait(timeout=5.2), "stop returned while the writer still owned a batch"
        assert stopped.wait(timeout=4)
        assert store.count() == 1
    finally:
        engine._stop.set()
        engine._writer.join(timeout=5)
        stopper.join(timeout=5)
