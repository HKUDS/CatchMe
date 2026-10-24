from __future__ import annotations

from types import SimpleNamespace

from catchme.recorders.platform import macos


def test_ambiguous_duplicate_document_names_return_no_path(monkeypatch, tmp_path):
    first = tmp_path / "project-a" / "report.txt"
    second = tmp_path / "project-b" / "report.txt"
    results = iter(
        [
            SimpleNamespace(stdout="2\n"),
            SimpleNamespace(stdout=f"{first}\n{second}\n"),
        ]
    )
    monkeypatch.setattr(macos.subprocess, "run", lambda *args, **kwargs: next(results))

    assert macos.get_document_path(123, "report.txt — Unmatched Workspace") == ""
