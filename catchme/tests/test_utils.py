"""Tests for catchme.utils — dir_size_mb, file_size_mb."""

from __future__ import annotations

from catchme.utils import dir_size_mb, file_size_mb


class TestDirSizeMb:
    def test_empty_directory(self, tmp_path):
        assert dir_size_mb(str(tmp_path)) == 0.0

    def test_single_file(self, tmp_path):
        f = tmp_path / "data.bin"
        f.write_bytes(b"\x00" * 1024)  # 1 KB
        size = dir_size_mb(str(tmp_path))
        assert abs(size - 1024 / (1024 * 1024)) < 0.001

    def test_nested_files(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
        (sub / "b.txt").write_text("world", encoding="utf-8")
        size = dir_size_mb(str(tmp_path))
        assert size > 0

    def test_does_not_count_symlink_targets(self, monkeypatch, tmp_path):
        linked_file = tmp_path / "linked.bin"
        linked_file.write_bytes(b"x" * 1024)
        monkeypatch.setattr(
            "catchme.utils.os.path.islink",
            lambda path: path == str(linked_file),
        )

        assert dir_size_mb(str(tmp_path)) == 0.0

    def test_does_not_traverse_junction_targets(self, monkeypatch, tmp_path):
        linked_dir = tmp_path / "linked"
        linked_dir.mkdir()
        (linked_dir / "external.bin").write_bytes(b"x" * 1024)
        monkeypatch.setattr(
            "catchme.utils.os.path.isjunction",
            lambda path: path == str(linked_dir),
            raising=False,
        )

        assert dir_size_mb(str(tmp_path)) == 0.0

    def test_nonexistent_directory(self):
        assert dir_size_mb("/nonexistent/path/xyzzy") == 0.0


class TestFileSizeMb:
    def test_existing_file(self, tmp_path):
        f = tmp_path / "test.bin"
        f.write_bytes(b"\x00" * 2048)  # 2 KB
        size = file_size_mb(str(f))
        assert abs(size - 2048 / (1024 * 1024)) < 0.001

    def test_nonexistent_file(self):
        assert file_size_mb("/does/not/exist.txt") == 0.0

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("", encoding="utf-8")
        assert file_size_mb(str(f)) == 0.0
