"""Tests for catchme.extractors.file — file content extraction."""

from __future__ import annotations

import sys
import types

from catchme.extractors.file import extract_pdf_text, read_file_content


class TestReadFileContent:
    def test_python_file(self, tmp_path):
        f = tmp_path / "hello.py"
        f.write_text("print('hello')\n", encoding="utf-8")
        content, ftype = read_file_content(str(f))
        assert ftype == "code"
        assert "print" in content

    def test_json_file(self, tmp_path):
        f = tmp_path / "data.json"
        f.write_text('{"key": "value"}', encoding="utf-8")
        content, ftype = read_file_content(str(f))
        assert ftype == "code"
        assert "key" in content

    def test_markdown_file(self, tmp_path):
        f = tmp_path / "README.md"
        f.write_text("# Title\nSome text", encoding="utf-8")
        content, ftype = read_file_content(str(f))
        assert ftype == "code"
        assert "# Title" in content

    def test_plain_text_file(self, tmp_path):
        f = tmp_path / "notes.txt"
        f.write_text("just some notes", encoding="utf-8")
        content, ftype = read_file_content(str(f))
        assert ftype == "text"
        assert "notes" in content

    def test_image_returns_empty(self, tmp_path):
        f = tmp_path / "photo.png"
        f.write_bytes(b"\x89PNG\r\n\x1a\n")
        content, ftype = read_file_content(str(f))
        assert ftype == "image"
        assert content == ""

    def test_nonexistent_file(self):
        content, ftype = read_file_content("/does/not/exist.py")
        assert content == ""
        assert ftype == "unknown"

    def test_max_chars_truncation(self, tmp_path):
        f = tmp_path / "big.py"
        f.write_text("x" * 10_000, encoding="utf-8")
        content, ftype = read_file_content(str(f), max_chars=100)
        assert len(content) <= 100

    def test_unicode_content(self, tmp_path):
        f = tmp_path / "chinese.py"
        f.write_text("# 你好世界\nprint('hello')", encoding="utf-8")
        content, ftype = read_file_content(str(f))
        assert "你好世界" in content

    def test_pdf_document_closes_when_page_extraction_fails(self, monkeypatch):
        class FailingPage:
            def get_text(self):
                raise RuntimeError("synthetic extraction failure")

        class FakeDocument:
            closed = False

            def __getitem__(self, _page_slice):
                return [FailingPage()]

            def close(self):
                self.closed = True

        document = FakeDocument()
        pymupdf = types.ModuleType("pymupdf")
        pymupdf.open = lambda _path: document
        monkeypatch.setitem(sys.modules, "pymupdf", pymupdf)

        assert extract_pdf_text("synthetic.pdf", max_chars=100) == ""
        assert document.closed

    def test_unknown_extension_reads_as_text(self, tmp_path):
        f = tmp_path / "data.xyz"
        f.write_text("custom format content", encoding="utf-8")
        content, ftype = read_file_content(str(f))
        assert ftype == "text"
        assert "custom format" in content
