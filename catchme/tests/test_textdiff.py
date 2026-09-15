"""Tests for the shared keyboard text-diff helpers.

``diff_added`` replaced a per-character Python loop that was duplicated in the
macOS and Windows keyboard recorders. The original implementation is kept here
verbatim as ``_reference_diff`` so the fast version can be checked against it.
"""

from __future__ import annotations

import random

from catchme.recorders.textdiff import diff_added, has_non_ascii

ZWS = "​"


def _reference_diff(old: str, new: str) -> str:
    """The original per-character implementation, kept as the oracle."""
    i = 0
    while i < len(old) and i < len(new) and old[i] == new[i]:
        i += 1
    j_old, j_new = len(old) - 1, len(new) - 1
    while j_old >= i and j_new >= i and old[j_old] == new[j_new]:
        j_old -= 1
        j_new -= 1
    return new[i : j_new + 1]


class TestDiffAddedEquivalence:
    """diff_added must agree with the original implementation everywhere."""

    def test_explicit_cases(self):
        cases = [
            ("", ""),
            ("", "hello"),
            ("hello", ""),
            ("hello", "hello"),
            ("hello", "hello world"),  # append
            ("world", "hello world"),  # prepend
            ("hello world", "hello big world"),  # insert in the middle
            ("abcdef", "abef"),  # deletion
            ("abc", "xyz"),  # full replace
            ("aaaa", "aaaaa"),  # repeated chars
            ("hello", "hell"),  # backspace
            ("ni", "ni" + ZWS),  # IME composing marker
            ("", "你好"),  # CJK insert
            ("你好", "你好世界"),
            ("a" * 100, "a" * 50 + "X" + "a" * 50),
        ]
        for old, new in cases:
            assert diff_added(old, new) == _reference_diff(old, new), (old, new)

    def test_randomized_fuzz(self):
        rng = random.Random(1234)
        alphabet = "ab你好" + ZWS
        for _ in range(3000):
            old = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 12)))
            new = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 12)))
            assert diff_added(old, new) == _reference_diff(old, new), (old, new)

    def test_randomized_edits_of_shared_base(self):
        """Edits derived from a common base — the realistic typing shape."""
        rng = random.Random(99)
        for _ in range(2000):
            base = "".join(rng.choice("abcde") for _ in range(rng.randint(0, 30)))
            pos = rng.randint(0, len(base))
            op = rng.choice(["insert", "delete", "replace"])
            if op == "insert":
                new = base[:pos] + rng.choice("xyz") * rng.randint(1, 3) + base[pos:]
            elif op == "delete":
                new = base[:pos] + base[pos + rng.randint(1, 3) :]
            else:
                new = base[:pos] + "Q" + base[pos + 1 :]
            assert diff_added(base, new) == _reference_diff(base, new), (base, new)


class TestDiffAddedBehaviour:
    def test_append_returns_only_the_new_text(self):
        assert diff_added("hello", "hello world") == " world"

    def test_middle_insert_returns_inserted_text(self):
        assert diff_added("hello world", "hello big world") == "big "

    def test_prepend_returns_prefix(self):
        assert diff_added("world", "hello world") == "hello "

    def test_unchanged_returns_empty(self):
        assert diff_added("same", "same") == ""

    def test_deletion_returns_empty(self):
        assert diff_added("abcdef", "abef") == ""

    def test_large_field_is_still_correct(self):
        big = "x" * 200_000
        assert diff_added(big, big[:100_000] + "INSERTED" + big[100_000:]) == "INSERTED"
        assert diff_added(big, big + "tail") == "tail"


class TestHasNonAscii:
    def test_ascii_only(self):
        assert not has_non_ascii("hello world 123")
        assert not has_non_ascii("")

    def test_detects_cjk(self):
        assert has_non_ascii("你好")
        assert has_non_ascii("hello 世界")

    def test_detects_zero_width_space(self):
        assert has_non_ascii(ZWS)

    def test_matches_original_predicate(self):
        rng = random.Random(7)
        alphabet = "ab你" + ZWS
        for _ in range(500):
            s = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 10)))
            assert has_non_ascii(s) == any(ord(ch) > 127 for ch in s)
