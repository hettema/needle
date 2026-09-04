"""A card's lane from the facts, the machine's moves, and the doors (plan 03,
items 1, 2, 3 and 4), pure over domain values."""

from datetime import UTC, datetime, timedelta

from board.lane import (
    LaneFacts,
    came_from,
    card_of_cwd,
    doors_for,
    exit_for,
    is_question,
    lane_for,
    should_enter_executing,
)
from board.signals import parse_watch
from domain.audit import AuditEntry, AuditKind
from domain.card import Actor, Card, CardOrigin, DocumentLink, Place
from domain.column import Column
from domain.document import DocumentKind
from domain.gate import Gate
from domain.hook import HookEvent, HookKind
from domain.lane import CollisionVerdict, Discussion, LaneRecord, LaneState
from domain.launch import Rescue
from domain.row import Row, RowKind
from domain.session import Session, SessionKind, SessionState
from domain.slot import Handoff, Model, Placement, Rung
from domain.window import Window, WindowKind

NOW = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)
PROJECT = "/srv/harbour"
LANE = f"{PROJECT}/.claude/worktrees/card-7-the-thing"
PLACEMENT = Placement(
    slot="alpha", model=Model.FABLE, config_dir="/x", why="Fable headroom on alpha"
)


def card(
    number: int = 7,
    *,
    column: Column = Column.UP_NEXT,
    rows: list[Row] | None = None,
    archived: bool = False,
    gate: Gate | None = Gate.HIGH,
) -> Card:
    return Card(
        number=number,
        project="proj",
        place=Place(column=column, group=None, position=0),
        title="The thing",
        gate=gate,
        tags=[],
        deep="",
        citations=["docs/plans/p.md"],
        link=DocumentLink(kind=DocumentKind.PLAN, stem="p", title="The thing", archived=archived),
        origin=CardOrigin.IMPORTED,
        born_at=NOW - timedelta(days=3),
        rows=rows or [],
    )


def session(
    *,
    pid: int | None = 4242,
    state: SessionState = SessionState.WORKING,
    recorded: str = "working",
    detail: str = "",
    kind: SessionKind = SessionKind.BACKGROUND,
    wall: Handoff | None = None,
    session_id: str = "aaaa0001-0000-4000-8000-000000000000",
    created: datetime = NOW - timedelta(minutes=12),
) -> Session:
    return Session(
        slot="alpha",
        config_dir="/x/alpha",
        short_id=session_id.split("-")[0],
        session_id=session_id,
        kind=kind,
        name="card-7-the-thing",
        cwd=LANE,
        worktree=LANE,
        state=state,
        recorded=recorded,
        detail=detail,
        pid=pid,
        scope="needle-card-7-the-thing.scope",
        model=Model.FABLE,
        effort=Gate.HIGH,
        stale=False,
        wall=wall,
        intent="the brief",
        created_at=created,
        updated_at=NOW - timedelta(minutes=1),
    )


def event(
    kind: HookKind, message: str | None = None, *, at: datetime = NOW, id: int = 1
) -> HookEvent:
    return HookEvent(
        id=id,
        kind=kind,
        session_id="aaaa0001-0000-4000-8000-000000000000",
        cwd=LANE,
        at=at,
        source=None,
        message=message,
        reason=None,
        error=None,
        transcript_path=None,
        project="proj",
        card_number=7,
    )


def facts(**changes) -> LaneFacts:
    base = dict(
        project_path=PROJECT,
        sessions=[],
        events=[],
        discussions=[],
        records=[],
        windows=[],
        rescues={},
        deaths={},
        worktrees={},
        now=NOW,
    )
    base.update(changes)
    return LaneFacts(**base)


def moved(
    from_column: Column, to_column: Column, actor: Actor, at: datetime, id: int = 1
) -> AuditEntry:
    return AuditEntry(
        id=id,
        at=at,
        actor=actor,
        kind=AuditKind.MOVED,
        card_number=7,
        from_place=Place(column=from_column, group=None, position=0),
        to_place=Place(column=to_column, group=None, position=0),
        detail="moved",
    )


def row_written(kind: RowKind, at: datetime, id: int = 2) -> AuditEntry:
    return AuditEntry(
        id=id,
        at=at,
        actor=Actor.SESSION,
        kind=AuditKind.ROW,
        card_number=7,
        from_place=None,
        to_place=None,
        detail=f"{kind.value} written: x",
    )


# ── reading the lane ───────────────────────────────────────────────────


def test_a_card_with_no_trace_has_no_lane_and_a_closed_watch():
    lane = lane_for(card(), facts())
    assert lane.state == LaneState.NONE and lane.sentence == "" and lane.path is None


def test_a_live_session_in_the_worktree_is_hands_on_and_says_so():
    lane = lane_for(card(), facts(sessions=[session()], worktrees={LANE: "card-7-the-thing"}))
    assert lane.state == LaneState.WORKING and lane.path == LANE
    assert lane.sentence == "Working, fable on alpha, hands on for 12 min."
    assert lane.hands_on_since == NOW - timedelta(minutes=12)


def test_a_stop_with_a_question_is_asking_you_with_the_question():
    said = "I built the parser.\n\nShould the gate default to high or medium?"
    lane = lane_for(
        card(),
        facts(
            sessions=[session(state=SessionState.DONE, recorded="done")],
            events=[event(HookKind.SESSION_START, id=1), event(HookKind.STOP, said, id=2)],
        ),
    )
    assert lane.state == LaneState.ASKING and lane.question == said
    assert lane.sentence == "Asking you: Should the gate default to high or medium?"
    assert is_question("Done?") and not is_question("Done.") and not is_question(None)


def test_a_stop_without_a_question_is_stopped_with_its_words():
    lane = lane_for(
        card(),
        facts(
            sessions=[session(state=SessionState.DONE, recorded="done")],
            events=[event(HookKind.STOP, "Folded and closed.", at=NOW - timedelta(minutes=3))],
        ),
    )
    assert lane.state == LaneState.STOPPED
    assert lane.sentence == "Stopped 3 min ago, fable on alpha: Folded and closed."


def test_a_wall_reads_as_moving_and_a_rescue_is_said_on_the_card():
    wall = Handoff(
        session_id="aaaa0001-0000-4000-8000-000000000000",
        short_id="aaaa0001",
        from_slot="alpha",
        account="beta",
        model=None,
        prompt="carry on",
        reason="You've reached your Fable limit.",
        at=NOW,
        cwd=LANE,
        worktree=LANE,
        pid=4242,
        stopped=False,
        path="/h/x.json",
    )
    lane = lane_for(card(), facts(sessions=[session(state=SessionState.BLOCKED, wall=wall)]))
    assert lane.state == LaneState.MOVING
    assert (
        lane.sentence == "Hit a limit on alpha (You've reached your Fable limit.); moving to beta."
    )

    rescue = Rescue(
        id=1,
        session_id="aaaa0001-0000-4000-8000-000000000000",
        from_rung=Rung(slot="alpha", model=Model.FABLE),
        to_rung=Rung(slot="beta", model=Model.FABLE),
        reason="You've reached your Fable limit.",
        at=NOW - timedelta(minutes=2),
    )
    window = Window(
        id=1,
        session_id="aaaa0001-0000-4000-8000-000000000000",
        kind=WindowKind.LANE,
        app_id="org.omarchy.lane-card-7-the-thing",
        address="0x1",
        opened_at=NOW - timedelta(minutes=1),
        closed_at=None,
    )
    moved_lane = lane_for(
        card(),
        facts(
            sessions=[session()],
            rescues={"aaaa0001-0000-4000-8000-000000000000": [rescue]},
            windows=[window],
        ),
    )
    assert moved_lane.moved == "Moved to fable on beta, new window opened."
    assert moved_lane.sentence.startswith("Moved to fable on beta, new window opened. Working")
    assert moved_lane.window_open


def test_a_session_with_no_process_is_an_ended_lane_with_the_machines_reason():
    record = LaneRecord(
        project="proj",
        card_number=7,
        name="card-7-the-thing",
        path=LANE,
        branch="card-7-the-thing",
        tip="abc",
        first_seen=NOW - timedelta(hours=1),
        last_seen=NOW,
        gone_at=None,
        folded_at=NOW,
        trunk_synced_at=None,
        main_synced_at=None,
    )
    lane = lane_for(
        card(),
        facts(
            sessions=[session(pid=None, state=SessionState.ENDED, recorded="stopped")],
            records=[record],
            worktrees={LANE: "card-7-the-thing"},
            deaths={
                "aaaa0001-0000-4000-8000-000000000000": "the journal says: Killed process 4242"
            },
        ),
    )
    assert lane.state == LaneState.ENDED and lane.hands_on_since is None
    assert lane.died == "the journal says: Killed process 4242"
    assert lane.sentence == "Lane ended 1 min ago: the journal says: Killed process 4242. folded."
    assert lane.folded and not lane.trunk_synced


def test_a_discussion_is_never_hands_on_but_is_said():
    talk = Discussion(
        id=1,
        project="proj",
        card_number=7,
        session_id="dddd0001-0000-4000-8000-000000000000",
        slot="alpha",
        started_at=NOW,
    )
    talking = session(
        session_id="dddd0001-0000-4000-8000-000000000000", kind=SessionKind.INTERACTIVE
    )
    talking = talking.model_copy(update={"cwd": PROJECT, "worktree": None, "name": "x"})
    lane = lane_for(card(), facts(sessions=[talking], discussions=[talk]))
    assert lane.state == LaneState.NONE and lane.discussing == ["dddd0001"]
    assert lane.sentence == "In discussion with you (dddd0001)."


def test_the_card_of_a_working_directory():
    assert card_of_cwd(LANE, PROJECT) == 7
    assert card_of_cwd(LANE + "/sub", PROJECT) == 7
    assert card_of_cwd(PROJECT, PROJECT) is None
    assert card_of_cwd("/elsewhere/.claude/worktrees/card-7-x", PROJECT) is None


# ── the machine's moves ────────────────────────────────────────────────


def test_hands_on_moves_a_card_into_executing_unless_the_owner_took_it_out():
    lane = lane_for(card(), facts(sessions=[session()]))
    assert (
        should_enter_executing(card(), lane, [])
        == "hands on: aaaa0001 on alpha in card-7-the-thing"
    )
    assert should_enter_executing(card(column=Column.EXECUTING), lane, []) is None
    owner_took_it_out = [
        moved(Column.EXECUTING, Column.UP_NEXT, Actor.OWNER, NOW - timedelta(minutes=5))
    ]
    assert should_enter_executing(card(), lane, owner_took_it_out) is None
    before_this_life = [
        moved(Column.EXECUTING, Column.UP_NEXT, Actor.OWNER, NOW - timedelta(hours=2))
    ]
    assert should_enter_executing(card(), lane, before_this_life) is not None


def test_a_card_closing_under_its_own_session_is_not_dragged_back():
    lane = lane_for(card(), facts(sessions=[session()]))
    closing = card(column=Column.EXECUTED, rows=[Row(kind=RowKind.DELIVERED, text="d")])
    history = [row_written(RowKind.DELIVERED, NOW - timedelta(minutes=1))]
    assert should_enter_executing(closing, lane, history) is None


def ended_lane(**changes):
    return lane_for(
        card(column=Column.EXECUTING),
        facts(
            sessions=[session(pid=None, state=SessionState.ENDED, recorded="stopped")], **changes
        ),
    )


def test_a_close_that_landed_goes_to_executed_with_its_signal_else_decision_moment():
    since = NOW - timedelta(hours=1)
    history = [
        moved(Column.UP_NEXT, Column.EXECUTING, Actor.MACHINE, since, id=1),
        row_written(RowKind.DELIVERED, NOW - timedelta(minutes=5), id=2),
    ]
    signal = parse_watch("x — file docs/plans/done/p.md by 2026-09-30")
    closed = card(
        column=Column.EXECUTING,
        archived=True,
        rows=[Row(kind=RowKind.DELIVERED, text="d"), Row(kind=RowKind.WATCH, text="w")],
    )
    leaving = exit_for(closed, ended_lane(), history, folded=True, signal=signal, since=since)
    assert leaving is not None and leaving.column == Column.EXECUTED
    no_signal = exit_for(closed, ended_lane(), history, folded=True, signal=None, since=since)
    assert no_signal is not None and no_signal.column == Column.DECISION_MOMENT
    assert "names no signal" in no_signal.reason


def test_folded_but_unwritten_goes_to_decision_moment_and_nothing_folded_goes_back():
    since = NOW - timedelta(hours=1)
    history = [moved(Column.PLANNED, Column.EXECUTING, Actor.MACHINE, since)]
    unwritten = card(column=Column.EXECUTING)
    folded = exit_for(unwritten, ended_lane(), history, folded=True, signal=None, since=since)
    assert folded is not None and folded.column == Column.DECISION_MOMENT
    assert "no session wrote it up" in folded.reason
    back = exit_for(unwritten, ended_lane(), history, folded=False, signal=None, since=since)
    assert back is not None and back.column == Column.PLANNED and "nothing folded" in back.reason
    assert came_from([]) == Column.UP_NEXT


def test_a_delivered_row_without_a_provable_fold_stays_and_a_previous_life_does_not_count():
    since = NOW - timedelta(hours=1)
    history = [
        row_written(RowKind.DELIVERED, NOW - timedelta(days=2), id=1),
        moved(Column.UP_NEXT, Column.EXECUTING, Actor.MACHINE, since, id=2),
    ]
    delivered = card(
        column=Column.EXECUTING, archived=True, rows=[Row(kind=RowKind.DELIVERED, text="d")]
    )
    signal = parse_watch("x — file docs/plans/done/p.md by 2026-09-30")
    assert (
        exit_for(delivered, ended_lane(), history, folded=False, signal=signal, since=since) is None
    )


def test_a_hand_placed_card_with_no_lane_stays():
    placed = card(column=Column.EXECUTING)
    lane = lane_for(placed, facts())
    assert exit_for(placed, lane, [], folded=None, signal=None, since=None) is None


# ── the doors ──────────────────────────────────────────────────────────


def doors(c: Card, lane, **changes):
    base = dict(
        gate_named=True,
        placement=PLACEMENT,
        placement_note="",
        collision=None,
        signal=None,
        signal_due_for_owner=False,
    )
    base.update(changes)
    return doors_for(c, lane, **base)


def test_start_says_the_slot_and_model_the_rule_named_and_refuses_by_name():
    fresh = lane_for(card(), facts())
    offered = doors(card(), fresh)
    assert offered.start.offered and offered.start.label == "Start · fable on alpha"
    assert not offered.watch.offered and not offered.answer.offered and not offered.look.offered
    assert offered.discuss.offered
    gateless = doors(card(gate=None), fresh, gate_named=False)
    assert not gateless.start.offered and "names no effort gate" in gateless.start.why
    elsewhere = doors(card(column=Column.BACKLOG), fresh)
    assert "offered in Up next and Planned" in elsewhere.start.why
    nowhere = doors(card(), fresh, placement=None, placement_note="no account with headroom")
    assert not nowhere.start.offered and "nowhere to run" in nowhere.start.why
    assert not nowhere.discuss.offered


def test_a_collision_closes_start_and_opens_start_anyway_with_the_reason():
    from domain.lane import Collision

    collision = Collision(
        verdict=CollisionVerdict.COLLIDES,
        sentence="#9's lane is editing api/app.py right now.",
        files=["api/app.py"],
    )
    fresh = lane_for(card(), facts())
    offered = doors(card(), fresh, collision=collision)
    assert not offered.start.offered and offered.start.why.startswith("Lane collision")
    assert offered.start_anyway.offered and "#9's lane" in offered.start_anyway.why


def test_a_live_lane_offers_watch_and_stop_and_answer_only_when_stopped():
    working = lane_for(card(column=Column.EXECUTING), facts(sessions=[session()]))
    offered = doors(card(column=Column.EXECUTING), working)
    assert offered.watch.offered and offered.stop.offered and not offered.answer.offered
    assert not offered.start.offered and "hands on" in offered.start.why
    assert not offered.look.offered and "live" in offered.look.why
    asking = lane_for(
        card(column=Column.EXECUTING),
        facts(
            sessions=[session(state=SessionState.DONE, recorded="done")],
            events=[event(HookKind.STOP, "Which?")],
        ),
    )
    assert doors(card(column=Column.EXECUTING), asking).answer.offered


def test_an_ended_lane_offers_look_and_resume_and_never_watch():
    ended = lane_for(
        card(column=Column.EXECUTING),
        facts(sessions=[session(pid=None, state=SessionState.ENDED, recorded="stopped")]),
    )
    offered = doors(card(column=Column.EXECUTING), ended)
    assert offered.look.offered and offered.resume.offered
    assert not offered.watch.offered and not offered.stop.offered
    with_worktree = lane_for(card(), facts(worktrees={LANE: "card-7-the-thing"}))
    blocked = doors(card(), with_worktree)
    assert not blocked.start.offered and "already exists" in blocked.start.why


def test_the_owners_signal_question_opens_at_its_due_time():
    signal = parse_watch("the invoice reached his inbox — owner by 2026-09-04")
    executed = card(column=Column.EXECUTED)
    lane = lane_for(executed, facts())
    assert doors(executed, lane, signal=signal, signal_due_for_owner=True).signal.offered
    assert not doors(executed, lane, signal=signal, signal_due_for_owner=False).signal.offered
