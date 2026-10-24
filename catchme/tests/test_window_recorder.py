from __future__ import annotations

from unittest.mock import Mock

import pytest

from catchme.config import Config
from catchme.recorders import window
from catchme.recorders.window import WindowRecorder


@pytest.mark.parametrize("app_name", ["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"])
def test_windows_browser_process_names_do_not_infer_a_document_path(
    monkeypatch, tmp_path, app_name
):
    browser_url = Mock(return_value="")
    document_path = Mock(return_value=r"C:\Users\test\Report.txt")
    monkeypatch.setattr(
        window,
        "get_active_window",
        lambda: {"app": app_name, "title": "Report.txt - Browser", "pid": 1234},
    )
    monkeypatch.setattr(window, "get_browser_url", browser_url)
    monkeypatch.setattr(window, "get_document_path", document_path)
    emitted = []
    recorder = WindowRecorder(Config(root=tmp_path))

    recorder.poll(lambda data, blob="": emitted.append(data))

    browser_url.assert_called_once_with(app_name, 1234)
    document_path.assert_not_called()
    assert len(emitted) == 1
    assert "filepath" not in emitted[0]
