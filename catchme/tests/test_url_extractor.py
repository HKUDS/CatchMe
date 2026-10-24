from __future__ import annotations

import requests

from catchme.extractors import url as url_extractor


class _FakeResponse:
    def __init__(self, headers=None, content=b""):
        self.headers = headers or {}
        self.content = content

    def raise_for_status(self):
        pass


class _FakeSession:
    def __init__(self):
        self.headers = {}

    def get(self, url, timeout):
        if url == "https://example.test/":
            return _FakeResponse()
        return _FakeResponse(
            headers={"content-type": "application/PDF"},
            content=b"%PDF-1.7\n" + b"x" * 512,
        )


def test_pdf_media_type_is_case_insensitive_for_small_response(monkeypatch):
    monkeypatch.setattr(requests, "Session", _FakeSession)
    monkeypatch.setattr(
        url_extractor,
        "_extract_pdf_text",
        lambda _path, _max_chars: "synthetic extracted text",
    )

    text = url_extractor._fetch_pdf("https://example.test/report.pdf", max_chars=100)

    assert text == "synthetic extracted text"
