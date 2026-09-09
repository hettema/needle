"""The leverage class is a lens on his rank and never a way to choose work
(card #87, the plan's class line).

Two things hold it. Nothing under the dial — `api/dial.py`, the seat that
plans and starts a defect on his standing ruling, and `board/dial.py`, what
it may take next — imports the leverage result: a dial that read a class
could start the card the focus put first, which is the one move that is
his. And a focus is *chosen* only while the document on disk has the
ruling's fingerprint: the strip's own validator refuses to be built saying
otherwise, so no reader can show yesterday's ruling over today's document.
"""

import ast
from datetime import UTC, datetime

import pytest

from board.focus import strip_of
from domain.focus import (
    FocusDocument,
    FocusRuling,
    FocusState,
    FocusStrip,
    Measure,
)
from domain.lane import Door
from domain.meaning import Meaning, say
from tests.ratchets.paths import REPO

THE_DIAL = [REPO / "api" / "dial.py", REPO / "board" / "dial.py"]
THE_RESULT = "domain.focus"
"""The module every leverage result lives in; the dial may not import it,
by name or by attribute."""


def _imports(source: str) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
        elif isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
    return names


def test_nothing_under_the_dial_imports_the_leverage_result():
    for path in THE_DIAL:
        imported = _imports(path.read_text(encoding="utf-8"))
        offenders = {m for m in imported if m == THE_RESULT or m.startswith(THE_RESULT + ".")}
        assert not offenders, (
            f"{path.relative_to(REPO)} imports {offenders}: the dial never reads a card's "
            "class to choose work; a wrong order is a lens away from his rank and never a lane"
        )
        assert "leverage" not in path.read_text(encoding="utf-8").lower(), (
            f"{path.relative_to(REPO)} names the leverage result"
        )


def _document(fingerprint: str) -> FocusDocument:
    now = datetime(2026, 9, 9, tzinfo=UTC)
    measure = Measure(line="x — command true by 2026-10-01", signal=None, note=None)
    return FocusDocument(
        path="docs/FOCUS.md",
        fingerprint=fingerprint,
        title="t",
        what_matters="more berths paid",
        outcome=measure,
        what_holds="the invoice is late",
        bottleneck=measure,
        evidence="e",
        rival="r",
        recheck=measure,
        proposed=None,
        doubts=[],
        read_at=now,
    )


def _ruling(fingerprint: str) -> FocusRuling:
    return FocusRuling(
        id=1,
        project="p",
        fingerprint=fingerprint,
        what_matters="more berths paid",
        chosen_at=datetime(2026, 9, 9, tzinfo=UTC),
    )


def _door() -> Door:
    return Door(offered=False, label="x", why=say(Meaning.QUIET, "closed"))


def test_a_chosen_strip_cannot_be_built_over_a_document_the_ruling_does_not_bind():
    """The invariant is in the type: a strip saying chosen over a document
    at B with a ruling at A is refused at construction."""
    fields = dict(
        sentence="Focus chosen",
        what_matters=None,
        what_holds=None,
        check=None,
        checking=False,
        check_note=None,
        conversation=None,
        coverage=None,
        moves_proposed=0,
        accepted=None,
        put_back_offered=False,
        paused=None,
        recheck_due=None,
        recheck=None,
        measures=[],
        talk=_door(),
        choose=_door(),
        propose=_door(),
    )
    with pytest.raises(ValueError, match="fingerprint"):
        FocusStrip(
            state=FocusState.CHOSEN, document=_document("bbbb"), ruling=_ruling("aaaa"), **fields
        )
    with pytest.raises(ValueError, match="a document and a ruling"):
        FocusStrip(state=FocusState.PAUSED, document=_document("aaaa"), ruling=None, **fields)
    built = FocusStrip(
        state=FocusState.CHOSEN, document=_document("aaaa"), ruling=_ruling("aaaa"), **fields
    )
    assert built.state == FocusState.CHOSEN


def test_the_one_deriver_reads_a_ruling_over_another_document_as_proposed():
    """`strip_of` is the one place a ruling meets a document: a ruling
    bound to A over a document now at B is proposed, never chosen."""
    strip = strip_of(
        document=_document("bbbb"),
        ruling=_ruling("aaaa"),
        check=None,
        checking=False,
        check_note=None,
        conversation=None,
        talked_before=True,
        coverage=None,
        moves_proposed=0,
        accepted=None,
        put_back_offered=False,
        recheck=None,
        measures=[],
        now=datetime(2026, 9, 9, tzinfo=UTC),
    )
    assert strip.state == FocusState.PROPOSED
    assert strip.sentence == "A focus is ready for your decision"
