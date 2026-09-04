"""What the dial may take, what counts against its number, and who filed
each defect (plan 11), pure over domain values."""

from datetime import UTC, datetime, timedelta

from board.dial import (
    LIVE_STAGES,
    dial_state,
    filer_of,
    is_quiet,
    rail_count,
    rail_defects,
    running,
    why_not_eligible,
)
from board.lane import lane_for
from board.parse import parse_document
from domain.card import Actor, Card, CardOrigin, DocumentLink, Place
from domain.column import DEFECTS_RAIL, Column
from domain.corpus import CorpusIndex
from domain.dial import Dial, Filer, FixLane, FixStage
from domain.document import DocumentKind
from domain.lane import LaneState
from domain.row import Row, RowKind
from domain.signal import Reading
from tests.board.test_lane import facts, session

NOW = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)


def suggestion(stem: str, head: str, *, title: str = "A thing"):
    return parse_document(
        f"# {title}\n\n{head}\n\n## Observation\n\nx\n",
        kind=DocumentKind.SUGGESTION,
        path=f"docs/slice-suggestions/{stem}.md",
        archived=False,
        read_at=NOW,
    )


def card(number: int, stem: str, *, rows: list[Row] | None = None, born: datetime = NOW) -> Card:
    return Card(
        number=number,
        project="proj",
        place=Place(column=Column.BACKLOG, group=DEFECTS_RAIL, position=0),
        title="The thing",
        gate=None,
        tags=[],
        deep="",
        citations=[],
        link=DocumentLink(kind=DocumentKind.SUGGESTION, stem=stem, title="A thing", archived=False),
        origin=CardOrigin.ARRIVED,
        born_at=born,
        rows=rows or [],
    )


def reading(delivered: bool | None) -> Reading:
    return Reading(
        id=1, card_number=1, at=NOW, delivered=delivered, words="read", actor=Actor.MACHINE
    )


def test_the_filer_is_read_from_the_opening_words_of_found_by():
    assert filer_of("the owner, from the board's Idea door on 2026-09-04") == Filer.OWNER
    assert filer_of("The owner, 2026-09-01.") == Filer.OWNER
    assert filer_of("the lane on card #26 (plan 10), running the suite") == Filer.FEATURE_LANE
    assert filer_of("card #27's lane (the colour language), in the review's pass") == (
        Filer.FEATURE_LANE
    )
    assert filer_of("the review of card #249 (`docs/reviews/x.md`, finding 1)") == (
        Filer.FEATURE_LANE
    )
    assert filer_of("the close of card #249, carried out.") == Filer.FEATURE_LANE
    assert filer_of("#253's reading, 2026-09-05") == Filer.READING
    assert filer_of("the fix lane on card #40 (started by the dial), 2026-09-06") == (
        Filer.FIX_LANE
    )
    # "reading card #196's open face" is the owner reading, not a reading session.
    assert filer_of("the owner, reading card #196's open face") == Filer.OWNER
    assert filer_of("the meter reconcile of 2026-08-29.") == Filer.UNKNOWN
    assert filer_of(None) == Filer.UNKNOWN


def test_the_rail_is_counted_by_filer_over_defects_standing_on_their_own():
    documents = [
        suggestion("a", "**Kind:** defect\n**Found by:** the owner"),
        suggestion("b", "**Kind:** defect\n**Found by:** the lane on card #3"),
        suggestion("c", "**Kind:** idea\n**Found by:** the owner"),
        suggestion("d", "**Kind:** defect\n**Found by:** the owner"),
    ]
    index = CorpusIndex(documents=documents, read_at=NOW)
    cards = [card(1, "a"), card(2, "b"), card(3, "c"), card(4, "d")]
    cards[3].folded_into = 1
    assert [c.number for c, _ in rail_defects(cards, index)] == [1, 2]
    rail = rail_count("proj", cards, index)
    assert rail.total == 2
    assert rail.counts == {Filer.OWNER: 1, Filer.FEATURE_LANE: 1}


def test_eligibility_is_the_documents_mark_plus_the_cards_latest_reading():
    now = suggestion("a", "**Kind:** defect\n**Fix:** now")
    his = suggestion("b", "**Kind:** defect\n**Fix:** his")
    unmarked = suggestion("c", "**Kind:** defect")
    when = suggestion(
        "d",
        "**Kind:** defect\n**Fix:** when a row exists — file docs/row.md by 2026-12-31",
    )
    bare_when = suggestion("e", "**Kind:** defect\n**Fix:** when")
    common = dict(last=None, lane=None, planning_open=False, ran_before=False)
    assert why_not_eligible(card(1, "a"), now, **common) is None
    assert why_not_eligible(card(2, "b"), his, **common) == "marked his"
    assert why_not_eligible(card(3, "c"), unmarked, **common) == (
        "unmarked (no Fix: line); an unmarked defect reads as his"
    )
    assert why_not_eligible(card(4, "d"), when, **common) == (
        "marked when, and its trigger has not been read as delivered"
    )
    assert why_not_eligible(card(4, "d"), when, **{**common, "last": reading(False)}) == (
        "marked when, and its trigger last read not delivered"
    )
    assert why_not_eligible(card(4, "d"), when, **{**common, "last": reading(None)}) == (
        "marked when, and its trigger last read unreadable"
    )
    assert why_not_eligible(card(4, "d"), when, **{**common, "last": reading(True)}) is None
    assert why_not_eligible(card(5, "e"), bare_when, **common) == (
        "marked when, and the line names no trigger"
    )
    # A lane on it, a planning session open, a fix lane already run, or a
    # question left for the owner: the dial leaves it where it is.
    lane = lane_for(card(7, "a"), facts(sessions=[session()]))
    assert lane.state == LaneState.WORKING
    assert why_not_eligible(card(7, "a"), now, **{**common, "lane": lane}) == (
        "a lane exists for it (working)"
    )
    assert why_not_eligible(card(1, "a"), now, **{**common, "planning_open": True}) == (
        "the dial is planning it now"
    )
    assert why_not_eligible(card(1, "a"), now, **{**common, "ran_before": True}) == (
        "the dial took it once already; it is the owner's from here"
    )
    asked = card(1, "a", rows=[Row(kind=RowKind.ASK, text="which of the two?")])
    assert why_not_eligible(asked, now, **common) == "it carries a question for the owner"


def test_the_number_counts_a_fix_lane_from_its_planning_session_to_its_end():
    def fix(stage: FixStage) -> FixLane:
        return FixLane(
            id=1,
            project="proj",
            card_number=1,
            stage=stage,
            planning_started_at=NOW,
            planned_at=None,
            started_at=None,
            ended_at=None,
            note=None,
        )

    assert {FixStage.PLANNING, FixStage.PLANNED, FixStage.STARTED} == LIVE_STAGES
    assert running([fix(s) for s in FixStage]) == 3
    assert running([]) == 0


def test_quiet_is_no_lane_with_hands_on_any_project():
    working = lane_for(card(7, "a"), facts(sessions=[session()]))
    nothing = lane_for(card(2, "b"), facts(worktrees={}))
    assert is_quiet({"a": {2: nothing}, "b": {}})
    assert not is_quiet({"a": {2: nothing}, "b": {1: working}})
    state = dial_state(
        Dial(on=True, lanes=2, changed_at=NOW, first_on_at=NOW - timedelta(days=1)),
        [],
        {"b": {1: working}},
    )
    assert (state.running, state.quiet, state.dial.lanes) == (0, False, 2)
