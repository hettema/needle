"""What the dial may take, what counts against its number, and who filed
each defect (plan 11), pure over domain values."""

from datetime import UTC, datetime, timedelta

from board.dial import (
    LIVE_STAGES,
    SEAT_OPENS,
    TRIAGE_ATTEMPTS,
    Candidate,
    column_defects,
    defects_count,
    dial_state,
    filed_against,
    filed_by_the_card,
    filer_of,
    hands_off,
    held_lanes,
    is_quiet,
    mark_text,
    readings_spent,
    running,
    seat_opens,
    stopped_words,
    switch_was_on,
    text_of_mark,
    why_not_eligible,
)
from board.lane import lane_for
from board.parse import parse_document
from board.triage import routing_of
from domain.card import Actor, Card, CardOrigin, DocumentLink, Place
from domain.column import Column
from domain.corpus import CorpusIndex
from domain.dial import (
    MEMORY_FLOOR_BYTES,
    Dial,
    Filer,
    FixLane,
    FixStage,
    Meminfo,
    ScopeMemory,
    headroom,
)
from domain.document import DocumentKind
from domain.lane import LaneState
from domain.row import Row, RowKind
from domain.signal import Reading, SessionWork, WindowlessSession
from domain.triage import (
    COMMIT_BOUND,
    Breaks,
    Direction,
    Grade,
    Often,
    Reach,
    ReadingsSpent,
    Reason,
    Routing,
    Triage,
    TriageResult,
)
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
        place=Place(column=Column.DEFECTS, group=None, position=0),
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


def test_a_defect_the_cards_own_lane_filed_is_by_the_card_not_against_it():
    assert filed_by_the_card(54, "the lane on card #54 (docs/plans/x.md), in the walk")
    assert filed_by_the_card(59, "the lane on card #59 (x), at its own close")
    assert filed_by_the_card(27, "card #27's lane (the colour language), in the review's pass")
    assert filed_by_the_card(249, "the review of card #249 (`docs/reviews/x.md`, finding 1)")
    assert not filed_by_the_card(54, "the owner's session in Needle on 2026-09-07, counting #54")
    assert not filed_by_the_card(54, "the lane on card #540, in the review")
    assert not filed_by_the_card(3, "the reading on card #3")
    assert not filed_by_the_card(3, None)


def test_filed_against_counts_defects_only_and_the_archived_on_request(tmp_path):
    def doc(name: str, kind: str, archived: bool, found_by: str):
        folder = "docs/slice-suggestions/done" if archived else "docs/slice-suggestions"
        text = f"# T\n\n**Kind:** {kind}\n**Found by:** {found_by}\n\nbody\n"
        return parse_document(
            text,
            kind=DocumentKind.SUGGESTION,
            path=f"{folder}/{name}.md",
            archived=archived,
            read_at=datetime(2026, 9, 11, tzinfo=UTC),
        )

    documents = [
        doc("a", "defect", False, "the owner, reading #7's work"),
        doc("b", "idea", False, "the owner, thinking about #7"),
        doc("c", "defect", True, "#7's review, later"),
        doc("d", "defect", False, "the lane on card #70"),
    ]
    assert [d.stem for d in filed_against(7, "card-7-x", documents)] == ["a"]
    assert [d.stem for d in filed_against(7, "card-7-x", documents, live_only=False)] == [
        "a",
        "c",
    ]
    assert filer_of("the meter reconcile of 2026-08-29.") == Filer.UNKNOWN
    assert filer_of(None) == Filer.UNKNOWN


def test_the_column_is_counted_by_filer_over_defects_standing_on_their_own():
    documents = [
        suggestion("a", "**Kind:** defect\n**Found by:** the owner"),
        suggestion("b", "**Kind:** defect\n**Found by:** the lane on card #3"),
        suggestion("c", "**Kind:** idea\n**Found by:** the owner"),
        suggestion("d", "**Kind:** defect\n**Found by:** the owner"),
    ]
    index = CorpusIndex(documents=documents, read_at=NOW)
    cards = [card(1, "a"), card(2, "b"), card(3, "c"), card(4, "d")]
    cards[3].folded_into = 1
    assert [c.number for c, _ in column_defects(cards, index)] == [1, 2]
    count = defects_count("proj", cards, index)
    assert count.total == 2
    assert count.counts == {Filer.OWNER: 1, Filer.FEATURE_LANE: 1}


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
        why_not_eligible(card(1, "a"), now, routed=routed_for(now, verified(now)), **common) is None
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
    not_yet = {**common, "last": reading(False)}
    assert why_not_eligible(card(4, "d"), when, **when_ok, **not_yet) == (
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

    held = held_lanes(lanes, lambda project, number: doors.get(number), lambda project: True)
    assert [f.card_number for f in held] == [2, 4]
    assert running(lanes, held) == 3, "planning, the planned card whose door is open, started"
    # A planned card whose board's switch is off is held too (card #80).
    off = held_lanes(lanes, lambda project, number: doors.get(number), lambda project: False)
    assert [f.card_number for f in off] == [2, 3, 4]
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
    # The lanes' scopes are read beside the machine (plan 53, item 1): a
    # scope holding as much as the floor is the lane the floor was set from,
    # again, and the head names it; short memory names the biggest lane.
    lanes = [
        ScopeMemory(unit="needle-card-7-x.scope", held=gb, project="proj", card_number=7),
        ScopeMemory(
            unit="needle-card-9-y.scope", held=3 * gb + gb // 2, project="proj", card_number=9
        ),
    ]
    grown = headroom(
        Meminfo(available=9 * gb, swap_total=8 * gb, swap_free=7 * gb), floor, NOW, scopes=lanes
    )
    assert grown.full
    assert grown.sentence == "the machine is full: proj #9's lane holds 3.5 GB, past the 3 GB floor"
    assert [s.card_number for s in grown.scopes] == [9, 7], "biggest first"
    quiet = headroom(
        Meminfo(available=9 * gb, swap_total=8 * gb, swap_free=7 * gb), floor, NOW, scopes=lanes[:1]
    )
    assert not quiet.full and quiet.sentence is None and quiet.scopes == lanes[:1]
    short = headroom(
        Meminfo(available=2 * gb, swap_total=8 * gb, swap_free=7 * gb), floor, NOW, scopes=lanes[:1]
    )
    assert short.sentence == (
        "the machine is full: 2.0 GB available, 3 GB needed; "
        "the biggest lane is proj #7's lane at 1.0 GB"
    )
    both = headroom(
        Meminfo(available=2 * gb, swap_total=8 * gb, swap_free=7 * gb), floor, NOW, scopes=lanes
    )
    assert both.sentence == (
        "the machine is full: 2.0 GB available, 3 GB needed; "
        "proj #9's lane holds 3.5 GB, past the 3 GB floor"
    )
    nameless = headroom(
        Meminfo(available=9 * gb, swap_total=0, swap_free=0),
        floor,
        NOW,
        scopes=[
            ScopeMemory(unit="needle-reading-1.scope", held=4 * gb, project=None, card_number=None)
        ],
    )
    assert (
        nameless.sentence
        == "the machine is full: needle-reading-1.scope holds 4.0 GB, past the 3 GB floor"
    )
    # Lanes there were and the reading could not be made: full, and said.
    unread_lanes = headroom(
        Meminfo(available=9 * gb, swap_total=0, swap_free=0), floor, NOW, scopes=None
    )
    assert unread_lanes.full
    assert unread_lanes.sentence == "the machine is full: what its lanes hold could not be read"
    assert MEMORY_FLOOR_BYTES == 5 * 1024**3, "the owner's 5 GB after #386's 4.7 GB kill"
    state = dial_state(
        Dial(project="a", on=True, lanes=4, changed_at=NOW, first_on_at=NOW),
        [],
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
    own = Dial(project="a", on=True, lanes=2, changed_at=NOW, first_on_at=NOW - timedelta(days=1))
    other = Dial(project="b", on=True, lanes=2, changed_at=NOW, first_on_at=NOW)
    state = dial_state(
        own,
        [own, other],
        [],
        {"b": {1: working}},
        held=[],
        room=None,
    )
    assert (state.running, state.held, state.full) == (0, 0, None)
    assert (state.quiet, state.dial.lanes) == (False, 2)
    # The head names the other boards that are on, never its own (card #80).
    assert state.others_on == ["b"]
    off = other.model_copy(update={"on": False})
    assert dial_state(own, [own, off], [], {}, held=[], room=None).others_on == []


def test_a_boards_switch_at_a_moment_is_read_from_the_audit_of_turns():
    """Card #80, item 3: the last turn at or before the moment that turned
    the board says; a turn from before the switch was per board (no
    project) turned every board; a change of the number turns nothing; no
    turn by then is off."""
    from domain.card import Actor
    from domain.dial import DialChange

    def turned(n: int, at, project, on, lanes=1):
        return DialChange(id=n, at=at, actor=Actor.OWNER, project=project, on=on, lanes=lanes)

    t = NOW
    changes = [
        turned(1, t, None, True),  # the one dial, on for every board
        turned(2, t + timedelta(hours=1), None, False),
        turned(3, t + timedelta(hours=2), "a", True),
        turned(4, t + timedelta(hours=3), None, None, lanes=4),  # the number alone
        turned(5, t + timedelta(hours=4), "b", True),
        turned(6, t + timedelta(hours=5), "a", False),
    ]
    assert not switch_was_on(changes, "a", t - timedelta(seconds=1))
    assert switch_was_on(changes, "a", t) and switch_was_on(changes, "b", t)
    assert not switch_was_on(changes, "b", t + timedelta(hours=1))
    assert switch_was_on(changes, "a", t + timedelta(hours=2))
    assert not switch_was_on(changes, "b", t + timedelta(hours=2))
    assert switch_was_on(changes, "a", t + timedelta(hours=3, minutes=30)), (
        "the number turns nothing"
    )
    assert switch_was_on(changes, "b", t + timedelta(hours=4))
    assert not switch_was_on(changes, "a", t + timedelta(hours=5))
    assert switch_was_on(changes, "b", t + timedelta(hours=9))


def test_who_is_home_follows_ancestry_and_names_strangers(monkeypatch):
    """Card #99: a session's children are its own wherever its pid sits,
    a process no live session started is a stranger named by its command's
    head, and a stale copy of a session owns nothing."""
    from board.dial import who_is_home
    from domain.dial import ScopeHeld
    from tests.board.test_who_drives import a_session

    live = a_session(short_id="9a7c49a7", pid=4242)
    stale = a_session(short_id="deadbeef", pid=5151, stale=True)
    held = [
        ScopeHeld(
            unit="needle-card-1-x.scope",
            pids=[7001, 7002],
            commands={7001: "/usr/bin/python3 run_batch.py", 7002: "sleep 20"},
            lineage={7001: [4242, 919], 7002: [7001, 4242, 919]},
        ),
        ScopeHeld(
            unit="needle-reading-card-2-y.scope",
            pids=[8001, 8002],
            commands={8001: "uv run uvicorn app:api --port 8000", 8002: "uvicorn app:api"},
            lineage={8001: [919], 8002: [8001, 919]},
        ),
        ScopeHeld(unit="needle-card-3-z.scope", pids=[], commands={}, lineage={}),
        ScopeHeld(unit="needle-card-4-w.scope", pids=[5151], commands={5151: "claude"}, lineage={}),
    ]
    states = {s.unit: s for s in who_is_home(held, [live, stale])}
    assert states["needle-card-1-x.scope"].home == ["9a7c49a7"]
    assert states["needle-card-1-x.scope"].strangers == []
    assert not states["needle-card-1-x.scope"].nobody_home
    assert states["needle-reading-card-2-y.scope"].home == []
    assert states["needle-reading-card-2-y.scope"].strangers == ["uv run", "uvicorn app:api"]
    assert states["needle-reading-card-2-y.scope"].nobody_home
    assert not states["needle-card-3-z.scope"].nobody_home, "an empty group is nobody's leftovers"
    assert states["needle-card-4-w.scope"].nobody_home, "a stale copy owns nothing"


def test_parked_cards_queue_behind_every_defect_and_title_oldest_park_first():
    """Card #82, ruling 9: a parked card's place in the reading queue is a
    leading rank, never its date against a defect's birth — a park older
    than a defect would otherwise jump it."""
    old_park = Candidate(
        project="proj",
        card=card(1, "a", born=NOW - timedelta(days=30)),
        document=None,
        parked_since=NOW - timedelta(days=20),
    )
    young_defect = Candidate(project="proj", card=card(2, "b", born=NOW), document=None)
    newer_park = Candidate(
        project="proj",
        card=card(3, "c", born=NOW - timedelta(days=40)),
        document=None,
        parked_since=NOW - timedelta(days=1),
    )
    ordered = sorted([newer_park, old_park, young_defect], key=lambda c: c.age_key)
    assert [c.card.number for c in ordered] == [2, 1, 3]


# ── card #138: the seat reads a text once, and stops at the cap ────────


GRADED = Grade(
    breaks=Breaks.COSTS,
    breaks_words="a step done by hand until it is fixed",
    reach=Reach.SESSION,
    reach_words="the office's own log is what it touches",
    often=Often.SOMETIMES,
    often_words="it bites on the nights the log is read",
)


def graded(document, result: TriageResult = TriageResult.NOW) -> Triage:
    """A reading as every reading since card #100 lands: with its grade."""
    return verified(document, result).model_copy(update={"grade": GRADED})


def every_branch_of_routing() -> dict[Reason, tuple]:
    """One (document, reading, source fingerprint today) per branch of
    `routing_of`, keyed by the reason the branch lands. A branch added to
    `routing_of` without a case here fails the test below, which is the
    point: the seat's stance table has to stance it first."""
    now = suggestion("a", "**Kind:** defect\n**Fix:** now the rule already says it")
    his = suggestion("b", "**Kind:** defect\n**Fix:** his which of the two shapes")
    when = suggestion(
        "d", "**Kind:** defect\n**Fix:** when a row exists — file docs/row.md by 2026-12-31"
    )
    sourced = graded(now).model_copy(
        update={"source_ref": "docs/plans/p.md", "source_fingerprint": "abc"}
    )
    return {
        Reason.NO_DOCUMENT: (None, None, None),
        Reason.UNREAD: (now, None, None),
        Reason.DOCUMENT_MOVED: (
            now,
            graded(now).model_copy(update={"document_fingerprint": "gone"}),
            None,
        ),
        Reason.SOURCE_MOVED: (now, sourced, "moved"),
        Reason.CANNOT_TELL: (now, graded(now, TriageResult.CANNOT_TELL), None),
        Reason.SPLIT: (now, graded(now, TriageResult.SPLIT), None),
        Reason.HIS: (now, graded(now, TriageResult.HIS), None),
        Reason.WHEN: (when, graded(when, TriageResult.WHEN), None),
        Reason.WHEN_OVER_MARK: (his, graded(his, TriageResult.WHEN), None),
        Reason.NOW: (now, graded(now), None),
        Reason.NOW_OVER_MARK: (his, graded(his), None),
    }


def test_the_seat_has_a_stance_on_every_branch_of_routing_and_opens_only_on_unverified_text():
    """Card #138, item 1: a reading opens only where nobody has verified
    today's text. Keyed to `routing_of`'s own reasons, so a new branch
    fails here until it is stanced — the hole 6efa8db's guard inferred its
    way around by reading `needs triage` with a graded row as commit-bound."""
    cases = every_branch_of_routing()
    assert set(cases) == set(Reason), "every reason has a case, and every case a reason"
    stances: dict[Reason, bool] = {}
    for reason, (document, triage, source_now) in cases.items():
        routed = routing_of(document, triage, source_fingerprint=source_now)
        assert routed.reason == reason, (reason, routed)
        stances[reason] = seat_opens(routed, triage)
    assert {r for r, opens in stances.items() if opens} == {
        Reason.UNREAD,
        Reason.DOCUMENT_MOVED,
        Reason.SOURCE_MOVED,
    }
    assert set(SEAT_OPENS) == set(Reason)
    # The three commit-bound branches are exactly the loop the card was for.
    assert {Reason.SPLIT, Reason.WHEN_OVER_MARK, Reason.NOW_OVER_MARK} == COMMIT_BOUND
    for reason in COMMIT_BOUND:
        assert not stances[reason]
    # A reading that landed no grade is read again whatever it landed: the
    # column has no order for the card without one (card #100).
    for document, triage, source_now in cases.values():
        if triage is None:
            continue
        ungraded = triage.model_copy(update={"grade": None})
        assert seat_opens(routing_of(document, ungraded, source_fingerprint=source_now), ungraded)


def test_the_commit_bound_sentences_say_when_it_was_read_and_that_a_commit_moves_it():
    cases = every_branch_of_routing()
    for reason in COMMIT_BOUND:
        document, triage, source_now = cases[reason]
        why = routing_of(document, triage, source_fingerprint=source_now).why
        assert f"read on {NOW.date().isoformat()}" in why, (reason, why)
        assert "the board does not read it again until" in why, (reason, why)
    assert (
        "never routes more freely than the corpus"
        in routing_of(*cases[Reason.NOW_OVER_MARK][:2], source_fingerprint=None).why
    )


def opened(number: int, text: str | None, *, ended: bool = True, hours_ago: float = 1.0):
    return WindowlessSession(
        id=number,
        project="proj",
        card_number=1,
        work=SessionWork.TRIAGE,
        session_id=f"s{number}",
        slot="alpha",
        started_at=NOW - timedelta(hours=hours_ago),
        ended_at=NOW - timedelta(hours=hours_ago) + timedelta(minutes=5) if ended else None,
        text_fingerprint=text,
    )


def test_readings_are_counted_per_text_once_each_landed_or_not_and_never_while_open():
    sessions = [
        opened(1, "t1", hours_ago=9),
        opened(2, "t1", hours_ago=8),
        opened(3, "t2", hours_ago=7),
        opened(4, "t1", hours_ago=6),
        opened(5, None, hours_ago=5),  # from before the column: bound to no text
        opened(6, "t1", hours_ago=1, ended=False),
    ]
    on_t1 = readings_spent(sessions, text="t1", since=None, parked=False, wanted=True)
    assert on_t1.opened == 3 and on_t1.stopped, (
        "three ended readings on t1; the open one is not spent"
    )
    on_t2 = readings_spent(sessions, text="t2", since=None, parked=False, wanted=True)
    assert on_t2.opened == 1 and not on_t2.stopped
    assert readings_spent(sessions, text="t3", since=None, parked=False, wanted=True).opened == 0, (
        "a changed text is a new count"
    )
    # A parked card's count is per park: the readings before the park are
    # the earlier park's (card #82, ruling 9).
    park = NOW - timedelta(hours=6, minutes=30)
    per_park = readings_spent(sessions, text="t1", since=park, parked=True, wanted=True)
    assert per_park.opened == 1 and not per_park.stopped
    assert TRIAGE_ATTEMPTS == 3


def spent(opened: int, *, parked: bool = False, wanted: bool = True) -> ReadingsSpent:
    return ReadingsSpent(text="t", opened=opened, cap=3, parked=parked, wanted=wanted)


def test_the_words_say_how_many_and_what_starts_the_readings_again():
    assert stopped_words(None) is None
    assert stopped_words(spent(2)) is None
    defect = stopped_words(spent(3))
    assert defect is not None
    assert "read this 3 times on this text" in defect and "nothing settled it" in defect
    assert "a change to the document or to the source its mark cites starts them again" in defect
    parked = stopped_words(spent(3, parked=True))
    assert parked is not None and "since it was parked or you last answered on it" in parked
    assert "your answer on it, a change to its document, or parking it again" in parked
    # The fuse's words only where the fuse is what holds the card: three
    # readings whose last one settled it are three readings, not a stop
    # (the review of #138, finding 1).
    assert stopped_words(spent(3, wanted=False)) is None
    assert stopped_words(spent(5, parked=True, wanted=False)) is None
    assert spent(3, wanted=False).stopped, "the seat still opens nothing on it"


def test_a_marks_text_is_the_document_and_its_source_together():
    now = suggestion("a", "**Kind:** defect\n**Fix:** now the rule already says it")
    assert mark_text(now, "abc") != mark_text(now, "abd"), "a moved source is a new text"
    assert mark_text(now, None) != mark_text(now, "abc")
    assert mark_text(now, "abc") == mark_text(now, "abc")
    assert mark_text(now, "abc") == text_of_mark(now.fingerprint, "abc"), (
        "the seat's count and the decisions line name one text"
    )


def test_hands_off_is_no_lane_at_all():
    assert hands_off(None)
    assert not hands_off(lane_for(card(7, "a"), facts(sessions=[session()])))
