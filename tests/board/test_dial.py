"""What the dial may take, what counts against its number, and who filed
each defect (plan 11), pure over domain values."""

from datetime import UTC, datetime, timedelta

from board.dial import (
    LIVE_STAGES,
    MEMORY_FLOOR_BYTES,
    dial_state,
    filer_of,
    headroom,
    held_lanes,
    is_quiet,
    rail_count,
    rail_defects,
    running,
    why_not_eligible,
)
from board.lane import lane_for
from board.parse import parse_document
from board.triage import routing_of
from domain.card import Actor, Card, CardOrigin, DocumentLink, Place
from domain.column import DEFECTS_RAIL, Column
from domain.corpus import CorpusIndex
from domain.dial import Dial, Filer, FixLane, FixStage, Meminfo
from domain.document import DocumentKind
from domain.lane import LaneState
from domain.row import Row, RowKind
from domain.signal import Reading
from domain.triage import Direction, Routing, Triage, TriageResult
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


def verified(document, result: TriageResult = TriageResult.NOW) -> Triage:
    """A reading that agrees with the document as it stands: what the dial
    now needs before it takes anything (plan 59)."""
    return Triage(
        id=1,
        project="proj",
        card_number=1,
        at=NOW,
        actor=Actor.SESSION,
        result=result,
        words="the source says so",
        decision="d0",
        parent=None,
        direction=Direction.NONE if result == TriageResult.NOW else None,
        source_ref=None,
        source_path=None,
        source_fingerprint=None,
        document_fingerprint=document.fingerprint,
        session_id="s",
    )


def routed_for(document, triage: Triage | None):
    return routing_of(document, triage, source_fingerprint=None)


def test_a_mark_alone_no_longer_opens_the_dial_and_an_unmarked_defect_is_nobodys():
    """The measured failure this plan exists for: the mark was written once,
    by the session that found the defect, and nothing read it again. Now the
    dial needs the mark *and* a reading of it that agrees."""
    now = suggestion("a", "**Kind:** defect\n**Fix:** now the rule already says it")
    unmarked = suggestion("c", "**Kind:** defect")
    common = dict(last=None, lane=None, planning_open=False, triage_open=False, ran_before=False)
    unread = why_not_eligible(card(1, "a"), now, routed=routed_for(now, None), **common)
    assert unread is not None and "no reading has verified it" in unread
    assert (
        why_not_eligible(
            card(1, "a"), now, routed=routed_for(now, verified(now)), **common
        )
        is None
    )
    nobodys = routed_for(unmarked, None)
    assert nobodys.state == Routing.NEEDS_TRIAGE
    assert "nobody's yet" in nobodys.why
    assert why_not_eligible(card(3, "c"), unmarked, routed=nobodys, **common) == nobodys.why
    open_now = why_not_eligible(
        card(1, "a"), now, routed=routed_for(now, verified(now)), **{**common, "triage_open": True}
    )
    assert open_now == "a reading is verifying its mark now"


def test_a_reading_is_stricter_at_once_and_never_looser_than_the_corpus():
    now = suggestion("a", "**Kind:** defect\n**Fix:** now the rule already says it")
    his = suggestion("b", "**Kind:** defect\n**Fix:** his which of the two shapes")
    common = dict(last=None, lane=None, planning_open=False, triage_open=False, ran_before=False)

    # Stricter at once: a `his` reading on a `now` document closes the dial.
    stricter = routed_for(now, verified(now, TriageResult.HIS))
    assert stricter.state == Routing.TRIAGED_HIS
    assert why_not_eligible(card(1, "a"), now, routed=stricter, **common) == stricter.why

    # Never looser: a `now` reading on a `his` document authorises nothing.
    looser = routed_for(his, verified(his, TriageResult.NOW))
    assert looser.state == Routing.NEEDS_TRIAGE
    assert "never routes more freely than the corpus" in looser.why
    assert why_not_eligible(card(2, "b"), his, routed=looser, **common) == looser.why

    # A reading bound to text that has since changed is nobody's again.
    moved = verified(now, TriageResult.NOW).model_copy(update={"document_fingerprint": "gone"})
    stale = routed_for(now, moved)
    assert stale.state == Routing.STALE
    assert why_not_eligible(card(1, "a"), now, routed=stale, **common) == stale.why


def test_eligibility_is_the_documents_mark_plus_the_cards_latest_reading():
    now = suggestion("a", "**Kind:** defect\n**Fix:** now the rule already says it")
    when = suggestion(
        "d",
        "**Kind:** defect\n**Fix:** when a row exists — file docs/row.md by 2026-12-31",
    )
    bare_when = suggestion("e", "**Kind:** defect\n**Fix:** when")
    common = dict(last=None, lane=None, planning_open=False, triage_open=False, ran_before=False)
    ok = dict(routed=routed_for(now, verified(now)))
    when_ok = dict(routed=routed_for(when, verified(when, TriageResult.WHEN)))
    bare_ok = dict(routed=routed_for(bare_when, verified(bare_when, TriageResult.WHEN)))
    assert why_not_eligible(card(1, "a"), now, **ok, **common) is None
    assert why_not_eligible(card(4, "d"), when, **when_ok, **common) == (
        "marked when, and its trigger has not been read as delivered"
    )
    assert why_not_eligible(card(4, "d"), when, **when_ok, **{**common, "last": reading(False)}) == (
        "marked when, and its trigger last read not delivered"
    )
    assert why_not_eligible(card(4, "d"), when, **when_ok, **{**common, "last": reading(None)}) == (
        "marked when, and its trigger last read unreadable"
    )
    assert (
        why_not_eligible(card(4, "d"), when, **when_ok, **{**common, "last": reading(True)}) is None
    )
    assert why_not_eligible(card(5, "e"), bare_when, **bare_ok, **common) == (
        "marked when, and the line names no trigger"
    )
    # A lane on it, a planning session open, a fix lane already run, or a
    # question left for the owner: the dial leaves it where it is.
    lane = lane_for(card(7, "a"), facts(sessions=[session()]))
    assert lane.state == LaneState.WORKING
    assert why_not_eligible(card(7, "a"), now, **ok, **{**common, "lane": lane}) == (
        "a lane exists for it (working)"
    )
    assert why_not_eligible(card(1, "a"), now, **ok, **{**common, "planning_open": True}) == (
        "the dial is planning it now"
    )
    assert why_not_eligible(card(1, "a"), now, **ok, **{**common, "ran_before": True}) == (
        "the dial took it once already; it is the owner's from here"
    )
    asked = card(1, "a", rows=[Row(kind=RowKind.ASK, text="which of the two?")])
    assert why_not_eligible(asked, now, **ok, **common) == "it carries a question for the owner"


def fix(stage: FixStage, number: int = 1) -> FixLane:
    return FixLane(
        id=number,
        project="proj",
        card_number=number,
        stage=stage,
        planning_started_at=NOW,
        planned_at=None,
        started_at=None,
        ended_at=None,
        note=None,
        decision=None,
    )


def test_the_number_counts_a_fix_lane_from_its_planning_session_to_its_end():
    assert {FixStage.PLANNING, FixStage.PLANNED, FixStage.STARTED} == LIVE_STAGES
    assert running([fix(s) for s in FixStage]) == 3
    assert running([]) == 0


def test_an_open_reading_counts_against_the_number_like_a_planning_session():
    """A live session on a machine whose ceiling is memory (plan 59, item 3):
    without this a rail of forty untriaged defects opens forty readings under
    a dial set to one."""
    assert running([], triaging=2) == 2
    assert running([fix(FixStage.STARTED)], triaging=1) == 2


def test_a_planned_card_whose_start_is_closed_is_held_and_does_not_count():
    """The plan "as many lanes as the machine can hold", item 3: a planned
    card with a closed door is no process. The planning stage still counts."""
    lanes = [
        fix(FixStage.PLANNING, 1),
        fix(FixStage.PLANNED, 2),
        fix(FixStage.PLANNED, 3),
        fix(FixStage.PLANNED, 4),
        fix(FixStage.STARTED, 5),
        fix(FixStage.FOLDED, 6),
    ]
    doors = {2: False, 3: True}  # 4 is unread: None, which is closed

    held = held_lanes(lanes, lambda project, number: doors.get(number))
    assert [f.card_number for f in held] == [2, 4]
    assert running(lanes, held) == 3, "planning, the planned card whose door is open, started"
    assert running(lanes) == 5, "without the held list every live stage counts, as before"


def test_the_memory_floor_is_read_against_available_memory_and_free_swap():
    """The number is a ceiling the machine lowers, never raises (ruling 4)."""
    floor = 3 * 1024**3
    gb = 1024**3
    room = headroom(Meminfo(available=6 * gb, swap_total=8 * gb, swap_free=5 * gb), floor, NOW)
    assert not room.full and room.sentence is None
    full = headroom(Meminfo(available=2 * gb, swap_total=8 * gb, swap_free=5 * gb), floor, NOW)
    assert full.full
    assert full.sentence == "the machine is full: 2.0 GB available, 3 GB needed"
    swap = headroom(Meminfo(available=6 * gb, swap_total=8 * gb, swap_free=gb // 2), floor, NOW)
    assert swap.sentence == "the machine is full: 0.5 GB swap free, 3 GB needed"
    both = headroom(Meminfo(available=gb, swap_total=8 * gb, swap_free=gb), floor, NOW)
    assert both.sentence == "the machine is full: 1.0 GB available, 1.0 GB swap free, 3 GB needed"
    # A machine with no swap is judged on memory alone.
    no_swap = headroom(Meminfo(available=6 * gb, swap_total=0, swap_free=0), floor, NOW)
    assert not no_swap.full
    # A reading the runtime could not make is full, and says so.
    unread = headroom(None, floor, NOW)
    assert unread.full and unread.sentence == "the machine is full: its memory could not be read"
    assert MEMORY_FLOOR_BYTES == 5 * 1024**3, "the owner's 5 GB after #386's 4.7 GB kill"
    state = dial_state(
        Dial(on=True, lanes=4, changed_at=NOW, first_on_at=NOW),
        [fix(FixStage.PLANNED, n) for n in range(1, 5)],
        {},
        held=[fix(FixStage.PLANNED, n) for n in range(1, 5)],
        room=full,
    )
    assert (state.running, state.held, state.dial.lanes) == (0, 4, 4), "4 held, 0 running"
    assert state.full == "the machine is full: 2.0 GB available, 3 GB needed"


def test_quiet_is_no_lane_with_hands_on_any_project():
    working = lane_for(card(7, "a"), facts(sessions=[session()]))
    nothing = lane_for(card(2, "b"), facts(worktrees={}))
    assert is_quiet({"a": {2: nothing}, "b": {}})
    assert not is_quiet({"a": {2: nothing}, "b": {1: working}})
    state = dial_state(
        Dial(on=True, lanes=2, changed_at=NOW, first_on_at=NOW - timedelta(days=1)),
        [],
        {"b": {1: working}},
        held=[],
        room=None,
    )
    assert (state.running, state.held, state.full) == (0, 0, None)
    assert (state.quiet, state.dial.lanes) == (False, 2)
