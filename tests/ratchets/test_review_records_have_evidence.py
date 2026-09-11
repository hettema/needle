"""New records carry a reviewer and verification evidence, without recursive review.

Archived records are historical. The close door applies the same evidence
check to still-closing records, including older records.
"""

from pathlib import Path

from board.review_rules import held, record_faults
from tests.ratchets.paths import REPO

REVIEWS = REPO / "docs" / "reviews"


def faults_of(records: list[Path]) -> list[str]:
    return [
        fault
        for record in records
        if held(record.name)
        for fault in record_faults(record.read_text(encoding="utf-8"), record.name)
    ]


def test_review_records_identify_reader_and_verification():
    faults = faults_of(sorted(REVIEWS.glob("*.md")))
    assert not faults, "; ".join(faults)


def test_empty_evidence_is_refused_but_no_second_review_is_required(tmp_path):
    path = tmp_path / "2026-09-11-finite.md"
    path.write_text("**Reviewer:** Codex\n**Verification:** Retry regression passed.\n")
    assert faults_of([path]) == []
    path.write_text("**Reviewer:** \n**Verification:** \n")
    assert len(faults_of([path])) == 2
