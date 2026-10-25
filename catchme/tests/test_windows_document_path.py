from __future__ import annotations

from types import SimpleNamespace

import psutil

from catchme.recorders.platform.windows import get_document_path


def test_exact_title_filename_wins_over_substring_match(monkeypatch, tmp_path):
    backup = tmp_path / "report.txt.backup"
    target = tmp_path / "report.txt"
    process = SimpleNamespace(
        open_files=lambda: [SimpleNamespace(path=str(backup)), SimpleNamespace(path=str(target))]
    )
    monkeypatch.setattr(psutil, "Process", lambda pid: process)

    assert get_document_path(123, "report.txt — Editor") == str(target)
