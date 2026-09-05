"""A card's lane from the facts, the machine's moves, and the doors (plan 03,
items 1, 2, 3 and 4), pure over domain values."""

from datetime import UTC, datetime, timedelta

from board.lane import (
    LaneFacts,
    came_from,
    card_of_cwd,
    doors_for,
    entered_executing_at,
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
from domain.lane import CollisionVerdict, Discussion, LaneRecord, LaneState, StartState, Wait
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
        # A live lane has its worktree on disk; a test about a card with no
        # trace, or a worktree that is gone, says `worktrees={}` itself.
        worktrees={LANE: "card-7-the-thing"},
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
    lane = lane_for(card(), facts(worktrees={}))
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


def test_a_stop_the_hook_pushed_wins_over_the_registrys_stale_word():
    """A resumed session's row keeps the previous life's `blocked` and detail
    for a while; the hook's Stop is the turn's end."""
    stale = session(state=SessionState.BLOCKED, recorded="blocked", detail="awaiting colour")
    stale = stale.model_copy(update={"updated_at": NOW})
    lane = lane_for(
        card(),
        facts(
            sessions=[stale],
            events=[event(HookKind.STOP, "THANKS", at=NOW - timedelta(seconds=20))],
        ),
    )
    assert lane.state == LaneState.STOPPED and lane.sentence.endswith(": THANKS")
    older = lane_for(
        card(),
        facts(
            sessions=[stale],
            events=[event(HookKind.STOP, "THANKS", at=NOW - timedelta(minutes=5))],
        ),
    )
    assert older.state == LaneState.BLOCKED, (
        "a Stop from an older turn does not outrank the registry"
    )


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
            worktrees={LANE: "card-7-the-thing"},
            rescues={"aaaa0001-0000-4000-8000-000000000000": [rescue]},
            windows=[window],
        ),
    )
    assert moved_lane.moved == "Moved to fable on beta, new window opened."
    assert moved_lane.sentence.startswith("Moved to fable on beta, new window opened. Working")
    assert moved_lane.window_open
    answered = rescue.model_copy(
        update={
            "to_rung": Rung(slot="alpha", model=Model.FABLE),
            "reason": "resumed with the owner's answer",
        }
    )
    stayed = lane_for(
        card(),
        facts(sessions=[session()], rescues={"aaaa0001-0000-4000-8000-000000000000": [answered]}),
    )
    assert stayed.moved is None, "an answer's resume stays on its rung and is not a move"


def test_a_session_with_no_process_is_an_ended_lane_with_the_machines_reason():
    record = LaneRecord(
        project="proj",
        card_number=7,
        name="card-7-the-thing",
        path=LANE,
        branch="card-7-the-thing",
        birth="000",
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
        kind=WindowKind.DISCUSS,
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
    lane = lane_for(card(), facts(sessions=[talking], discussions=[talk], worktrees={}))
    assert lane.state == LaneState.NONE and lane.discussing == ["dddd0001"]
    assert lane.sentence == "In discussion with you (dddd0001)."


def test_the_card_of_a_working_directory():
    assert card_of_cwd(LANE, PROJECT) == 7
    assert card_of_cwd(LANE + "/sub", PROJECT) == 7
    assert card_of_cwd(PROJECT, PROJECT) is None
    assert card_of_cwd("/elsewhere/.claude/worktrees/card-7-x", PROJECT) is None


# ── the machine's moves ────────────────────────────────────────────────


def test_hands_on_moves_a_card_into_executing_unless_the_owner_took_it_out():
    lane = lane_for(card(), facts(sessions=[session()], worktrees={LANE: "card-7-the-thing"}))
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


def test_the_owner_keeping_a_card_in_executing_is_neither_an_exit_nor_an_entry():
    """Accepting a verdict that stays on a doubted card re-places it by the
    owner's hand (plan 05); that row must not read as him taking the card
    out, nor as where the card came from."""
    since = NOW - timedelta(hours=2)
    kept = moved(Column.EXECUTING, Column.EXECUTING, Actor.OWNER, NOW - timedelta(minutes=5), id=3)
    history = [kept, moved(Column.PLANNED, Column.EXECUTING, Actor.MACHINE, since)]
    assert came_from(history) == Column.PLANNED
    lane = lane_for(card(), facts(sessions=[session()], worktrees={LANE: "card-7-the-thing"}))
    assert should_enter_executing(card(), lane, history) is not None
    back = exit_for(
        card(column=Column.EXECUTING), ended_lane(), history, folded=False, signal=None, since=since
    )
    assert back is not None and back.column == Column.PLANNED


def test_a_delivered_row_from_this_life_stays_and_a_stale_one_goes_to_decision_moment():
    """Two cards sat in Executing on 2026-09-04 with a DELIVERED row from 0.1's
    close days earlier and a lane that had ended: the old guard kept them
    there forever. A close still landing (DELIVERED in this life) waits; a
    stale one is the owner's to judge."""
    since = NOW - timedelta(hours=1)
    stale = [
        row_written(RowKind.DELIVERED, NOW - timedelta(days=2), id=1),
        moved(Column.UP_NEXT, Column.EXECUTING, Actor.MACHINE, since, id=2),
    ]
    delivered = card(
        column=Column.EXECUTING, archived=True, rows=[Row(kind=RowKind.DELIVERED, text="d")]
    )
    signal = parse_watch("x — file docs/plans/done/p.md by 2026-09-30")
    out = exit_for(delivered, ended_lane(), stale, folded=False, signal=signal, since=since)
    assert out is not None and out.column == Column.DECISION_MOMENT
    assert "previous life" in out.reason
    current = [
        moved(Column.UP_NEXT, Column.EXECUTING, Actor.MACHINE, since, id=1),
        row_written(RowKind.DELIVERED, NOW - timedelta(minutes=1), id=2),
    ]
    unarchived = card(column=Column.EXECUTING, rows=[Row(kind=RowKind.DELIVERED, text="d")])
    assert (
        exit_for(unarchived, ended_lane(), current, folded=False, signal=signal, since=since)
        is None
    )


def test_a_hand_placed_card_with_no_lane_stays():
    placed = card(column=Column.EXECUTING)
    lane = lane_for(placed, facts(worktrees={}))
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
        signal_evidence=None,
        suggestion_live=False,
        waits=[],
    )
    base.update(changes)
    return doors_for(c, lane, **base)


def wait(number: int, column: Column | None, *, label: str | None = None) -> Wait:
    return Wait(
        label=label or f"#{number}",
        project="proj",
        number=number,
        column=column,
        shipped=column in (Column.EXECUTED, Column.DONE),
    )


def test_start_says_the_slot_and_model_the_rule_named_and_refuses_by_name():
    fresh = lane_for(card(), facts(worktrees={}))
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


def test_shared_ground_opens_start_with_the_ground_in_its_label():
    """Shared ground is a cost the door shows, never a reason to close
    (INTENT.md lesson 4): the door opens with its placement and says in one
    clause what it shares; nothing is left to override."""
    from domain.lane import Collision

    collision = Collision(
        verdict=CollisionVerdict.COLLIDES,
        sentence="Shares ground: #9's lane is editing api/app.py right now. "
        "The second to fold rebases.",
        files=["api/app.py"],
        cards=[9],
    )
    fresh = lane_for(card(), facts(worktrees={}))
    offered = doors(card(), fresh, collision=collision)
    assert offered.start.offered
    assert offered.start.label == (
        "Start · fable on alpha — shares 1 file with #9's lane; the second to fold rebases"
    )
    assert offered.start.why == collision.sentence
    assert offered.readiness.state == StartState.SHARES
    assert offered.readiness.cards == [9] and offered.readiness.files == ["api/app.py"]
    assert not hasattr(offered, "start_anyway")
    # Every other reason to close still closes, whatever the ground.
    taken = doors(card(), lane_for(card(), facts()), collision=collision)
    assert not taken.start.offered and taken.readiness.state == StartState.TAKEN


def test_the_plans_own_word_is_the_one_hold_on_start():
    """A Sequencing line naming cards closes Start until they are in
    Executed or Done, and says which and where; a named card that shipped
    holds nothing (the plan "as many lanes as the machine can hold", item 2)."""
    fresh = lane_for(card(), facts(worktrees={}))
    held = doors(
        card(),
        fresh,
        waits=[
            wait(139, Column.DECISION_MOMENT),
            wait(20, Column.UP_NEXT, label="Needle #20"),
            wait(222, Column.DONE),
            wait(999, None),
        ],
    )
    assert not held.start.offered and held.readiness.state == StartState.WAITS
    assert held.start.why == (
        "Start waits on the plan's own word: its Sequencing names #139 (Decision moment), "
        "Needle #20 (Up next), #999 (not on the board); it opens by itself once every named "
        "card is in Executed or Done."
    )
    assert [w.number for w in held.readiness.waits] == [139, 20, 999]
    assert [w.number for w in held.waits] == [139, 20, 222, 999], "the open face lists them all"
    shipped = doors(card(), fresh, waits=[wait(222, Column.DONE), wait(235, Column.EXECUTED)])
    assert shipped.start.offered and shipped.readiness.state == StartState.FREE
    assert shipped.readiness.waits == [] and len(shipped.waits) == 2
    # The hold is judged before the ground: a plan that waits is not started
    # into shared ground, and the pill says waits, never shares.
    from domain.lane import Collision

    collision = Collision(
        verdict=CollisionVerdict.COLLIDES, sentence="Shares ground.", files=["a.py"], cards=[9]
    )
    both = doors(card(), fresh, waits=[wait(139, Column.PLANNED)], collision=collision)
    assert both.readiness.state == StartState.WAITS and both.readiness.cards == []


def test_a_live_lane_offers_watch_and_stop_and_answer_only_when_stopped():
    working = lane_for(
        card(column=Column.EXECUTING),
        facts(sessions=[session()], worktrees={LANE: "card-7-the-thing"}),
    )
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
    window = Window(
        id=1,
        session_id="aaaa0001-0000-4000-8000-000000000000",
        kind=WindowKind.WATCH,
        app_id="org.omarchy.board-watch-card-7-the-thing",
        address="0x1",
        opened_at=NOW,
        closed_at=None,
    )
    windowed = lane_for(
        card(column=Column.EXECUTING), facts(sessions=[session()], windows=[window])
    )
    focus = doors(card(column=Column.EXECUTING), windowed).watch
    assert focus.offered and focus.label == "Focus its window", (
        "a window that is open is a door too, never a closed Watch with a tooltip"
    )


def test_an_ended_lane_offers_look_and_resume_and_never_watch():
    ended = lane_for(
        card(column=Column.EXECUTING),
        facts(
            sessions=[session(pid=None, state=SessionState.ENDED, recorded="stopped")],
            worktrees={LANE: "card-7-the-thing"},
        ),
    )
    offered = doors(card(column=Column.EXECUTING), ended)
    assert offered.look.offered and offered.resume.offered
    assert not offered.watch.offered and not offered.stop.offered
    gone = lane_for(
        card(),
        facts(
            sessions=[session(pid=None, state=SessionState.ENDED, recorded="stopped")],
            worktrees={},
        ),
    )
    after_removal = doors(card(), gone)
    assert after_removal.start.offered, "a removed worktree is a lane that can start again"
    assert not after_removal.look.offered and "worktree is gone" in after_removal.look.why
    with_worktree = lane_for(card(), facts(worktrees={LANE: "card-7-the-thing"}))
    blocked = doors(card(), with_worktree)
    assert not blocked.start.offered and "already exists" in blocked.start.why


def test_the_owners_signal_question_opens_at_its_due_time():
    signal = parse_watch("the invoice reached his inbox — owner by 2026-09-04")
    executed = card(column=Column.EXECUTED)
    lane = lane_for(executed, facts())
    assert doors(executed, lane, signal=signal, signal_due_for_owner=True).signal.offered
    assert not doors(executed, lane, signal=signal, signal_due_for_owner=False).signal.offered


def test_a_session_whose_worktree_is_gone_is_an_ended_lane_whatever_proc_says():
    """Four cards sat in Executing on 2026-09-04: their sessions' spare
    processes were alive, their worktrees were not. The disk wins."""
    lane = lane_for(
        card(),
        facts(
            sessions=[session(pid=4242, state=SessionState.DONE, recorded="done")],
            worktrees={},
        ),
    )
    assert lane.state == LaneState.ENDED and lane.hands_on_since is None
    assert lane.died == "its worktree is gone from disk"


def test_entered_executing_at_reads_the_last_entry_into_executing():
    since = NOW - timedelta(hours=1)
    history = [
        moved(Column.UP_NEXT, Column.EXECUTING, Actor.MACHINE, since, id=2),
        moved(Column.EXECUTING, Column.UP_NEXT, Actor.MACHINE, NOW - timedelta(days=1), id=1),
    ]
    assert entered_executing_at(history) == since
    assert entered_executing_at([]) is None


# ── plan 06: the archived rule, the pill, the Plan door ────────────────


def test_a_card_the_machine_parked_goes_back_to_planned_once_a_live_plan_carries_it():
    """The plan "as many lanes as the machine can hold", item 5: the machine
    undoes its own park when the evidence for it is gone, and only its own."""
    from board.lane import unpark
    from domain.evidence import Evidence

    none = lane_for(card(), facts(worktrees={}))
    parked = moved(Column.BACKLOG, Column.DECISION_MOMENT, Actor.MACHINE, NOW, id=3).model_copy(
        update={"evidence": Evidence.DOCUMENT_ARCHIVED}
    )
    back = unpark(card(column=Column.DECISION_MOMENT), none, [parked])
    assert back is not None and back.column == Column.PLANNED
    assert back.evidence == Evidence.PLAN_LIVE
    assert back.reason == (
        "parked when its suggestion was archived, but a live plan carries it now "
        "(docs/plans/p.md): back to Planned"
    )
    # Still archived: stays parked. The owner's move: his. Hands on: the
    # lane loop's business. Another column: nothing to undo.
    assert unpark(card(column=Column.DECISION_MOMENT, archived=True), none, [parked]) is None
    his = moved(Column.BACKLOG, Column.DECISION_MOMENT, Actor.OWNER, NOW, id=4)
    assert unpark(card(column=Column.DECISION_MOMENT), none, [his, parked]) is None
    ended = moved(Column.EXECUTING, Column.DECISION_MOMENT, Actor.MACHINE, NOW, id=5).model_copy(
        update={"evidence": Evidence.LANE_ENDED}
    )
    assert unpark(card(column=Column.DECISION_MOMENT), none, [ended]) is None
    working = lane_for(card(column=Column.DECISION_MOMENT), facts(sessions=[session()]))
    assert unpark(card(column=Column.DECISION_MOMENT), working, [parked]) is None
    assert unpark(card(column=Column.PLANNED), none, [parked]) is None
    assert unpark(card(column=Column.DECISION_MOMENT), none, []) is None


def test_an_archived_document_moves_a_card_nobody_has_hands_on():
    from datetime import date

    from board.lane import after_archive
    from domain.evidence import Evidence
    from domain.signal import Signal, SignalKind

    none = lane_for(card(), facts(worktrees={}))
    assert after_archive(card(), none, None) is None, "a live document moves nothing"
    moved = after_archive(card(archived=True), none, None)
    assert moved is not None
    assert moved.column == Column.DECISION_MOMENT and moved.evidence == Evidence.DOCUMENT_ARCHIVED
    assert "its plan was archived (docs/plans/done/p.md)" in moved.reason
    assert "no session wrote it up on the board" in moved.reason
    signal = Signal(
        what="x",
        kind=SignalKind.FILE,
        target="a",
        expect=None,
        due=date(2026, 9, 10),
        every_hours=24,
    )
    written = card(
        archived=True,
        rows=[
            Row(kind=RowKind.DELIVERED, text="x"),
            Row(kind=RowKind.WATCH, text="x — file a by 2026-09-10"),
        ],
    )
    landed = after_archive(written, none, signal)
    assert landed is not None and landed.column == Column.EXECUTED
    assert landed.evidence == Evidence.CLOSE_LANDED
    unreadable = after_archive(written, none, None)
    assert unreadable is not None and unreadable.column == Column.DECISION_MOMENT
    assert "names no signal the board can read" in unreadable.reason
    # A live lane's close decides for itself.
    working = lane_for(card(column=Column.EXECUTING, archived=True), facts(sessions=[session()]))
    assert after_archive(card(column=Column.EXECUTING, archived=True), working, None) is None
    # Decision moment has the owner's eye, Not now is his ruling, Executed and Done are shipped.
    for column in (Column.DECISION_MOMENT, Column.NOT_NOW, Column.EXECUTED, Column.DONE):
        assert after_archive(card(column=column, archived=True), none, None) is None
    # A folded card follows its leader instead.
    folded = card(archived=True).model_copy(update={"folded_into": 3})
    assert after_archive(folded, none, None) is None
    # An Executing card with a lane that ended and an archived plan: the exit rule
    # runs first in the loop; this rule still answers for it.
    ended = lane_for(
        card(column=Column.EXECUTING, archived=True), facts(sessions=[session(pid=None)])
    )
    assert ended.state == LaneState.ENDED
    late = after_archive(card(column=Column.EXECUTING, archived=True), ended, None)
    assert late is not None and late.column == Column.DECISION_MOMENT


def test_the_pill_is_the_start_doors_verdict_in_one_word():
    from board.lane import UNREAD
    from domain.lane import Collision, StartState

    fresh = lane_for(card(), facts(worktrees={}))
    assert doors(card(), fresh).readiness.state == StartState.FREE
    assert doors(card(), fresh).readiness.why == PLACEMENT.why
    assert doors(card(gate=None), fresh, gate_named=False).readiness.state == StartState.NO_GATE
    assert doors(card(column=Column.BACKLOG), fresh).readiness.state == StartState.ELSEWHERE
    nowhere = doors(card(), fresh, placement=None, placement_note="every slot is spent")
    assert nowhere.readiness.state == StartState.NOWHERE and "spent" in nowhere.readiness.why
    unread = doors(card(), fresh, placement=None, placement_note=UNREAD)
    assert unread.readiness.state == StartState.UNREAD
    collision = Collision(
        verdict=CollisionVerdict.COLLIDES,
        sentence="Shares ground: #9's lane is editing api/app.py right now.",
        files=["api/app.py"],
        cards=[9],
    )
    shares = doors(card(), fresh, collision=collision).readiness
    assert shares.state == StartState.SHARES and shares.cards == [9]
    assert shares.files == ["api/app.py"] and shares.why.startswith("Shares ground")
    waits = doors(card(), fresh, waits=[wait(139, Column.PLANNED)]).readiness
    assert waits.state == StartState.WAITS and [w.number for w in waits.waits] == [139]
    on_disk = lane_for(card(), facts())
    assert doors(card(), on_disk).readiness.state == StartState.TAKEN
    working = lane_for(card(column=Column.EXECUTING), facts(sessions=[session()]))
    assert doors(card(column=Column.EXECUTING), working).readiness.state == StartState.TAKEN
    # One judgment: the pill's word and the door's state never disagree.
    open_states = {StartState.FREE, StartState.SHARES}
    for offered in (
        doors(card(), fresh),
        nowhere,
        unread,
        doors(card(), fresh, collision=collision),
        doors(card(), fresh, waits=[wait(139, Column.PLANNED)]),
    ):
        assert offered.start.offered == (offered.readiness.state in open_states)
        assert offered.readiness.why == offered.start.why


def test_plan_is_offered_on_a_live_suggestion_with_somewhere_to_run():
    fresh = lane_for(card(), facts(worktrees={}))
    closed = doors(card(), fresh).plan
    assert not closed.offered and "not behind a live suggestion" in closed.why
    assert doors(card(), fresh, suggestion_live=True).plan.offered
    nowhere = doors(card(), fresh, suggestion_live=True, placement=None, placement_note="spent")
    assert not nowhere.plan.offered and "nowhere to run" in nowhere.plan.why


def test_a_plan_conversation_for_several_cards_is_one_line_on_the_rail():
    from board.lane import conversations_alive

    sid = "aaaa0001-0000-4000-8000-000000000000"
    rows = [
        Discussion(
            id=1,
            project="proj",
            card_number=8,
            kind=WindowKind.PLAN,
            session_id=sid,
            slot="alpha",
            started_at=NOW,
        ),
        Discussion(
            id=2,
            project="proj",
            card_number=7,
            kind=WindowKind.PLAN,
            session_id=sid,
            slot="alpha",
            started_at=NOW,
        ),
    ]
    alive = conversations_alive([session()], rows)
    assert [(c.what, c.card_number) for c in alive] == [("Plan #7, #8", 8)]
    idea = [
        Discussion(
            id=3,
            project="proj",
            card_number=None,
            kind=WindowKind.IDEA,
            session_id=sid,
            slot="alpha",
            started_at=NOW,
        )
    ]
    assert [c.what for c in conversations_alive([session()], idea)] == ["Idea"]
