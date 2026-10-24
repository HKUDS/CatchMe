from __future__ import annotations

import pytest

from catchme.pipelines.summarize import _apply_structured


@pytest.mark.parametrize(
    "raw",
    [
        "## Summary\nUpdated summary without evidence",
        "## Summary\nUpdated summary with an empty evidence section\n## Evidence\n",
    ],
)
def test_apply_structured_clears_evidence_from_previous_summary(raw):
    node = {"summary": "Previous summary", "evidence": "Evidence for previous summary"}

    _apply_structured(node, raw)

    assert node["summary"].startswith("Updated summary")
    assert "evidence" not in node


def test_apply_structured_replaces_evidence_with_current_output():
    node = {"summary": "Previous summary", "evidence": "Evidence for previous summary"}

    _apply_structured(
        node,
        "## Summary\nUpdated summary\n## Evidence\nEvidence for updated summary",
    )

    assert node == {
        "summary": "Updated summary",
        "evidence": "Evidence for updated summary",
    }
