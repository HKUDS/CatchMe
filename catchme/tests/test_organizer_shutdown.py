from __future__ import annotations

import threading
from unittest import mock

from catchme.config import Config
from catchme.organizer import Organizer


def test_organizer_finishes_current_processing_before_stopping_summary_queue():
    entered = threading.Event()
    release = threading.Event()
    stopped = threading.Event()
    operations = []
    summary_queue = mock.Mock()
    summary_queue.stop.side_effect = lambda: operations.append("queue stopped")

    with mock.patch("catchme.summary_queue.SummaryQueue", return_value=summary_queue):
        organizer = Organizer(mock.Mock(), Config())

    def process():
        entered.set()
        release.wait()
        operations.append("processing finished")

    organizer._process = process
    organizer._save_tree = lambda: operations.append("tree saved")
    organizer._pending.set()
    worker = threading.Thread(target=organizer.run, daemon=True)
    worker.start()
    assert entered.wait(timeout=1)

    def stop():
        organizer.stop()
        stopped.set()

    stopper = threading.Thread(target=stop, daemon=True)
    stopper.start()
    try:
        assert not stopped.wait(timeout=0.05)
        assert not summary_queue.stop.called
    finally:
        release.set()
        stopper.join(timeout=2)
        worker.join(timeout=2)

    assert stopped.is_set()
    assert operations == ["processing finished", "queue stopped", "tree saved"]
