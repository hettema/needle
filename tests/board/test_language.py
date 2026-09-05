"""The colour language (plan 27): one function names every state, one word
in one meaning, with the one door that state allows. This table is the rule;
the page test renders each line of it and asserts the tokens."""

from datetime import date, timedelta

from board.assemble import claims_of, state_of, summarize
from board.lane import lane_for, nothing_read
from board.signals import parse_watch
from domain.board import Claim, FaceDoorName, LoopState, Meaning
from domain.card import Actor, DocumentLink
from domain.column import Column
from domain.corpus import CorpusIndex
from domain.document import DocumentKind, DocumentState
from domain.evidence import Evidence, EvidenceState, Standing
from domain.hook import HookKind
from domain.lane import Collision, CollisionVerdict, LaneRecord, LaneState, Wait
from domain.session import SessionState
from domain.signal import Reading, SessionWork, WindowlessSession
from domain.slot import Handoff
from tests.board.test_lane import LANE, NOW, PLACEMENT, card, doors, event, facts, session

TRUSTED = Standing(actor=Actor.OWNER, evidence=None, state=EvidenceState.TRUSTED, words=None)
DOUBTED = Standing(
    actor=Actor.MACHINE,
    evidence=Evidence.HANDS_ON,
    state=EvidenceState.DOUBTED,
    words="the board doubts this: no live session has hands on its worktree",
)
OWNER_SIGNAL = parse_watch(
    "the owner says the board reads without explanation — owner dennis by 2026-09-11"
)
SESSION_SIGNAL = parse_watch("no session re-grows the old doors — session hr by 2026-09-11")


def state(c, *, lane=None, standing=TRUSTED, document_state=DocumentState.PLAN, **facts_):
    """A card's state from explicit facts; the doors are the lane's doors as
    the loop would read them, with the rule finding alpha."""
    the_lane = lane if lane is not None else nothing_read(c, "/srv/harbour", NOW)[0]
    kw = dict(signal=None, signal_note=None, last=None, reading=None)
    kw.update(facts_)
    return state_of(
        c,
        document_state=document_state,
        document_path="docs/plans/p.md",
        doors=doors(c, the_lane, **kw.pop("doors", {})),
        lane=lane,
        standing=standing,
        now=NOW,
        **kw,
    )


def test_a_free_card_is_proven_and_its_one_door_is_start_filled():
    s = state(card())
    assert (s.word, s.meaning) == ("free to start", Meaning.PROVEN)
    assert s.door is not None and s.door.name == FaceDoorName.START and s.door.primary
    # The collapsed door is one word; where it would run is in its reason.
    assert s.door.label == "Start" and s.hint is None and s.loop is None
    assert s.door.why.startswith("Start · fable on alpha — ")


def test_shared_ground_before_start_is_proven_and_its_door_is_start():
    """Shared ground is shown, never waited on (INTENT.md lesson 4): the
    face reads *shares ground with #23*, never *waits*, and the door is the
    same filled Start a free card has, with the ground in its reason."""
    collision = Collision(
        verdict=CollisionVerdict.COLLIDES,
        sentence="Shares ground: #23's lane is editing a.py right now. The second to fold rebases.",
        files=["a.py", "b.py"],
        cards=[23],
    )
    s = state(card(), doors={"collision": collision})
    assert (s.word, s.meaning) == ("shares ground with #23", Meaning.PROVEN)
    assert s.door is not None and s.door.name == FaceDoorName.START and s.door.primary
    assert s.door.label == "Start" and s.hint is None
    assert s.door.why == (
        "Start · fable on alpha — shares 2 files with #23's lane; the second to fold rebases — "
        + collision.sentence
    )
    assert s.detail == collision.sentence


def test_a_plan_that_waits_on_a_named_card_is_quiet_and_says_which():
    waits = [
        Wait(label="#139", project="proj", number=139, column=Column.PLANNED, shipped=False),
        Wait(label="Needle #20", project="needle", number=20, column=None, shipped=False),
    ]
    s = state(card(), doors={"waits": waits})
    assert (s.word, s.meaning) == ("waits on #139, Needle #20", Meaning.QUIET)
    assert s.door is None and s.hint == "open to see"
    assert s.detail is not None and s.detail.startswith("Start waits on the plan's own word")


def test_a_suggestion_has_no_plan_yet_and_its_door_creates_one_outlined():
    c = card(column=Column.BACKLOG, gate=None)
    s = state(
        c,
        document_state=DocumentState.SUGGESTION,
        doors={"suggestion_live": True, "gate_named": False},
    )
    assert (s.word, s.meaning) == ("no plan yet", Meaning.QUIET)
    assert s.door is not None and s.door.name == FaceDoorName.PLAN
    assert s.door.label == "Create plan" and not s.door.primary


def test_a_working_lane_is_live_with_its_time_and_place_and_watch_outlined():
    c = card(column=Column.EXECUTING)
    lane = lane_for(c, facts(sessions=[session(detail="Skimming the suites.")]))
    s = state(c, lane=lane)
    assert (s.word, s.meaning) == ("working · 12 min · fable on alpha", Meaning.LIVE)
    assert s.detail == "Skimming the suites."
    assert s.door is not None and s.door.name == FaceDoorName.WATCH
    assert s.door.label == "Watch" and not s.door.primary


def test_a_lane_asking_is_yours_with_the_question_and_answer_filled():
    said = "I built the parser.\n\nShould the gate default to high or medium?"
    c = card(column=Column.EXECUTING)
    lane = lane_for(
        c,
        facts(
            sessions=[session(state=SessionState.DONE, recorded="done")],
            events=[event(HookKind.SESSION_START, id=1), event(HookKind.STOP, said, id=2)],
        ),
    )
    s = state(c, lane=lane)
    assert (s.word, s.meaning) == ("asking you", Meaning.YOURS)
    assert s.detail == "“Should the gate default to high or medium?”"
    assert s.door is not None and (s.door.name, s.door.label, s.door.primary) == (
        FaceDoorName.OPEN,
        "Answer",
        True,
    )


def test_a_lane_that_stopped_or_is_blocked_is_yours_with_the_way_on():
    """Every state the WAITING_ON_YOU branch can name, and the door it allows."""
    c = card(column=Column.EXECUTING)
    stopped = lane_for(
        c,
        facts(
            sessions=[session(state=SessionState.DONE, recorded="done")],
            events=[event(HookKind.STOP, "The parser is in. Nothing else to do.")],
        ),
    )
    assert stopped.state == LaneState.STOPPED
    s = state(c, lane=stopped)
    assert (s.word, s.meaning) == ("stopped · fable on alpha", Meaning.YOURS)
    assert s.detail == "The parser is in. Nothing else to do."
    assert s.door is not None and s.door.label == "Answer"

    blocked = lane_for(
        c, facts(sessions=[session(state=SessionState.BLOCKED, detail="waiting on a permission")])
    )
    assert blocked.state == LaneState.BLOCKED
    b = state(c, lane=blocked)
    assert (b.word, b.meaning) == ("blocked · fable on alpha", Meaning.YOURS)
    assert b.detail == "waiting on a permission"


def test_a_lane_the_runtime_is_moving_is_live_and_says_where_it_went():
    c = card(column=Column.EXECUTING)
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
    moving = lane_for(c, facts(sessions=[session(state=SessionState.BLOCKED, wall=wall)]))
    assert moving.state == LaneState.MOVING
    s = state(c, lane=moving)
    assert (s.word, s.meaning) == ("moving · fable on alpha", Meaning.LIVE)


def test_a_lane_that_folded_is_finished_and_a_lane_that_lost_its_work_is_broken():
    """The discriminator is what the lane left behind, not that it ended. A
    folded lane's worktree on disk is quiet — Start says "lane exists". A lane
    that ended with nothing folded lost its work, and that is red."""
    c = card()
    record = LaneRecord(
        project="proj",
        card_number=7,
        name="card-7-the-thing",
        path=LANE,
        branch="card-7-the-thing",
        birth=None,
        tip=None,
        first_seen=NOW - timedelta(hours=2),
        last_seen=NOW - timedelta(minutes=30),
        gone_at=None,
        folded_at=NOW - timedelta(minutes=20),
        trunk_synced_at=NOW - timedelta(minutes=20),
        main_synced_at=None,
    )
    folded = lane_for(c, facts(records=[record]))
    assert folded.state == LaneState.ENDED and folded.folded
    s = state(c, lane=folded, doors={"placement": PLACEMENT})
    assert (s.word, s.meaning) == ("lane exists", Meaning.QUIET)
    assert s.detail is not None and LANE in s.detail
    assert Claim.LANE_ENDED not in claims_of(
        c,
        document_state=DocumentState.PLAN,
        lane=folded,
        standing=TRUSTED,
        signal=None,
        last=None,
        reading=None,
        verdict=None,
        now=NOW,
    )

    lost = lane_for(c, facts(records=[record.model_copy(update={"folded_at": None})]))
    assert lost.state == LaneState.ENDED and not lost.folded
    assert state(c, lane=lost).word == "lane ended"


def test_an_archived_plan_outside_the_shipped_columns_is_quiet():
    s = state(
        card(column=Column.BACKLOG, archived=True),
        document_state=DocumentState.ARCHIVED,
    )
    assert (s.word, s.meaning) == ("archived", Meaning.QUIET) and s.hint == "open ▸"
    planned = state(card(column=Column.PLANNED, gate=None), doors={"gate_named": False})
    assert planned.word == "no gate"


def test_two_lanes_in_one_file_is_broken_and_beats_live():
    c = card(column=Column.EXECUTING)
    lane = lane_for(c, facts(sessions=[session()]))
    lane = lane.model_copy(
        update={
            "colliding": Collision(
                verdict=CollisionVerdict.COLLIDES,
                sentence="#241's lane is also editing a.py.",
                files=["a.py"],
                cards=[241],
            )
        }
    )
    s = state(c, lane=lane)
    assert (s.word, s.meaning) == ("colliding with #241", Meaning.BROKEN)
    assert s.detail == "#241's lane is also editing a.py." and s.hint == "open to see"


def test_a_doubted_status_is_broken_with_the_doubt_in_the_essences_place():
    s = state(card(column=Column.DECISION_MOMENT), standing=DOUBTED)
    assert (s.word, s.meaning) == ("doubted", Meaning.BROKEN)
    assert s.detail == DOUBTED.words and s.hint == "open to decide" and s.door is None


def test_a_lane_that_died_before_the_fold_is_broken_but_after_it_is_the_loop():
    c = card(column=Column.DECISION_MOMENT)
    lane = lane_for(c, facts(sessions=[session(pid=None)], deaths={}))
    assert lane.state == LaneState.ENDED
    s = state(c, lane=lane)
    assert (s.word, s.meaning) == ("lane ended", Meaning.BROKEN) and s.hint == "open to resume"
    shipped = card(column=Column.EXECUTED, archived=True)
    s = state(
        shipped, lane=lane_for(shipped, facts(sessions=[session(pid=None)])), signal=OWNER_SIGNAL
    )
    assert s.word == "loop open · you read it 11 Sep" and s.meaning == Meaning.QUIET


def test_a_folded_lane_on_a_shipped_card_gives_way_to_the_loop():
    """Every card closes with its session's turn ending, so without this the
    board reads "stopped · <model> on <slot>" in amber on the very cards whose
    work is finished — asking the owner to act on what is already done."""
    shipped = card(column=Column.EXECUTED, archived=True)
    record = LaneRecord(
        project="proj",
        card_number=7,
        name="card-7-the-thing",
        path=LANE,
        branch="card-7-the-thing",
        birth=None,
        tip=None,
        first_seen=NOW - timedelta(hours=2),
        last_seen=NOW - timedelta(minutes=51),
        gone_at=None,
        folded_at=NOW - timedelta(minutes=51),
        trunk_synced_at=NOW - timedelta(minutes=51),
        main_synced_at=None,
    )
    stopped = lane_for(
        shipped,
        facts(
            records=[record],
            sessions=[session(state=SessionState.DONE, recorded="done")],
            events=[event(HookKind.STOP, "Nothing regressed; the lane is folded.")],
        ),
    )
    assert stopped.state == LaneState.STOPPED and stopped.folded
    s = state(shipped, lane=stopped, signal=SESSION_SIGNAL)
    assert s.word == "loop open · a session reads it 11 Sep" and s.loop is not None
    assert Claim.LANE_ASKING not in claims_of(
        shipped,
        document_state=DocumentState.ARCHIVED,
        lane=stopped,
        standing=TRUSTED,
        signal=SESSION_SIGNAL,
        last=None,
        reading=None,
        verdict=None,
        now=NOW,
    )
    # A lane that has not folded still asks, wherever its card sits.
    unfolded = lane_for(
        shipped,
        facts(
            records=[record.model_copy(update={"folded_at": None})],
            sessions=[session(state=SessionState.DONE, recorded="done")],
            events=[event(HookKind.STOP, "I could not push.")],
        ),
    )
    assert state(shipped, lane=unfolded, signal=SESSION_SIGNAL).word.startswith("stopped · ")


def test_a_document_nowhere_is_broken_before_anything_else():
    c = card(column=Column.DECISION_MOMENT)
    s = state(c, document_state=DocumentState.GONE, standing=DOUBTED)
    assert (s.word, s.meaning) == ("document nowhere", Meaning.BROKEN)
    assert s.detail == "cites docs/plans/p.md, and no such file exists in the project"


def test_a_decision_moment_card_is_your_move_and_decide_opens_it():
    s = state(card(column=Column.DECISION_MOMENT))
    assert (s.word, s.meaning) == ("your move", Meaning.YOURS)
    assert s.door is not None and (s.door.name, s.door.label, s.door.primary) == (
        FaceDoorName.OPEN,
        "Decide",
        True,
    )


def test_a_shipped_cards_state_is_its_loop():
    c = card(column=Column.EXECUTED, archived=True)
    open_loop = state(c, signal=SESSION_SIGNAL, document_state=DocumentState.ARCHIVED)
    assert open_loop.word == "loop open · a session reads it 11 Sep"
    # A card carrying a loop has said everything on its line; no hint beside it.
    assert open_loop.meaning == Meaning.QUIET and open_loop.hint is None
    assert open_loop.loop is not None and open_loop.loop.state == LoopState.OPEN
    assert not open_loop.loop.owner_only
    assert open_loop.detail == "Signal: no session re-grows the old doors — by 11 Sep"

    owner_ring = state(c, signal=OWNER_SIGNAL)
    assert owner_ring.loop is not None and owner_ring.loop.owner_only
    assert owner_ring.word == "loop open · you read it 11 Sep"

    due = state(c, signal=OWNER_SIGNAL.model_copy(update={"due": NOW.date()}))
    assert (due.word, due.meaning) == ("signal for you to read", Meaning.YOURS)
    assert due.loop is not None and due.loop.owner_only and due.loop.state == LoopState.OPEN
    assert due.door is not None and (due.door.name, due.door.label, due.door.primary) == (
        FaceDoorName.OPEN,
        "Read",
        True,
    )

    reading = WindowlessSession(
        id=1,
        project="proj",
        card_number=7,
        work=SessionWork.READING,
        session_id="bbbb0001-0000-4000-8000-000000000000",
        slot="beta",
        started_at=NOW - timedelta(minutes=2),
        ended_at=None,
    )
    live = state(c, signal=SESSION_SIGNAL, reading=reading)
    assert (live.word, live.meaning) == ("loop open · a session reads it now · beta", Meaning.LIVE)

    read_at = NOW - timedelta(hours=1)
    last = Reading(
        id=1,
        card_number=7,
        at=read_at,
        delivered=True,
        words="the doors stayed",
        actor=Actor.SESSION,
    )
    closed = state(card(column=Column.DONE, archived=True), signal=SESSION_SIGNAL, last=last)
    clock = read_at.astimezone().strftime("%H:%M")
    assert (closed.word, closed.meaning) == (
        f"loop closed · read {clock}, delivered",
        Meaning.PROVEN,
    )
    assert closed.loop is not None and closed.loop.state == LoopState.CLOSED

    unnamed = state(c, signal_note="No WATCH row names a signal.")
    assert (unnamed.word, unnamed.meaning) == ("no signal named", Meaning.QUIET)
    assert unnamed.detail == "No WATCH row names a signal." and unnamed.loop is None

    # A loop the board said it would close and has not is broken, and says so
    # on the head as well as on the card.
    late = state(c, signal=SESSION_SIGNAL.model_copy(update={"due": date(2026, 9, 1)}))
    assert (late.word, late.meaning) == ("loop open · 1 Sep passed, unread", Meaning.BROKEN)
    assert claims_of(
        c,
        document_state=DocumentState.ARCHIVED,
        lane=None,
        standing=TRUSTED,
        signal=SESSION_SIGNAL.model_copy(update={"due": date(2026, 9, 1)}),
        last=None,
        reading=None,
        verdict=None,
        now=NOW,
    ) == [Claim.SIGNAL_OVERDUE]


def test_the_quiet_states_each_have_their_word():
    assert state(card(column=Column.NOT_NOW)).word == "not now"
    unread = state_of(
        card(),
        document_state=DocumentState.PLAN,
        document_path="docs/plans/p.md",
        doors=nothing_read(card(), "/srv/harbour", NOW)[1],
        lane=None,
        standing=TRUSTED,
        signal=None,
        signal_note=None,
        last=None,
        reading=None,
        now=NOW,
    )
    assert (unread.word, unread.meaning) == ("not read yet", Meaning.QUIET)
    assert (
        state(
            card(), doors={"placement": None, "placement_note": "every subscription is spent"}
        ).word
        == "nowhere to run"
    )
    assert state(card(gate=None), doors={"gate_named": False}).word == "no gate"
    assert state(card(column=Column.EXECUTING)).word == "no hands on it"
    assert (
        state(card(column=Column.BACKLOG), document_state=DocumentState.NOTE).word == "no document"
    )
    for s in (
        state(card(column=Column.NOT_NOW)),
        state(card(column=Column.EXECUTING)),
        state(card(column=Column.BACKLOG), document_state=DocumentState.NOTE),
    ):
        assert s.meaning == Meaning.QUIET and s.door is None and s.hint


def test_claims_count_every_hold_a_card_has_on_the_owner():
    said = "Done.\n\nHigh or medium?"
    c = card(column=Column.DECISION_MOMENT)
    lane = lane_for(
        c,
        facts(
            sessions=[session(state=SessionState.DONE, recorded="done")],
            events=[event(HookKind.STOP, said)],
        ),
    )
    claims = claims_of(
        c,
        document_state=DocumentState.PLAN,
        lane=lane,
        standing=DOUBTED,
        signal=None,
        last=None,
        reading=None,
        verdict=None,
        now=NOW,
    )
    assert claims == [Claim.LANE_ASKING, Claim.DECISION, Claim.DOUBTED]
    shipped = card(column=Column.EXECUTED, archived=True)
    due = OWNER_SIGNAL.model_copy(update={"due": NOW.date()})
    assert claims_of(
        shipped,
        document_state=DocumentState.ARCHIVED,
        lane=None,
        standing=TRUSTED,
        signal=due,
        last=None,
        reading=None,
        verdict=None,
        now=NOW,
    ) == [Claim.SIGNAL_ASKING]


def test_summarize_names_the_state_and_the_claims_from_the_same_facts():
    index = CorpusIndex(documents=[], read_at=NOW)
    c = card(column=Column.UP_NEXT)
    c.link = DocumentLink(kind=DocumentKind.PLAN, stem="nowhere", title="", archived=False)
    summary = summarize(c, index, NOW, project_path="/srv/harbour")
    assert summary.state.word == "document nowhere" and summary.claims == [Claim.DOCUMENT_GONE]
    assert PLACEMENT.slot == "alpha" and LANE.endswith("card-7-the-thing")
