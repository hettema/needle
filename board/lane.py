"""What a card's lane is doing, read from the facts the loop gathers, and
which doors the card offers. Pure: the runtime, the hooks and the store are
read by the caller and handed in as domain values.

Executing is a machine fact (INTENT.md lesson 2): a live session in the
card's worktree is hands on, and only that. A discussion session is never
hands on. A session with no process is never working, whatever the registry
says (the runtime already holds that; this module only reads its verdict).
"""

import re
from datetime import UTC, datetime, timedelta

from pydantic import BaseModel

from board.brief import lane_name, lane_path
from board.collision import drift
from domain.audit import AuditEntry, AuditKind
from domain.card import Actor, Card
from domain.column import Column
from domain.document import DocumentKind
from domain.evidence import Evidence
from domain.hook import HookEvent, HookKind
from domain.lane import (
    HANDS_ON,
    Collision,
    CollisionVerdict,
    Conversation,
    Discussion,
    Door,
    Doors,
    Lane,
    LaneRecord,
    LaneState,
    Readiness,
    StartState,
)
from domain.launch import Rescue
from domain.row import RowKind
from domain.session import Session, SessionKind, SessionState
from domain.signal import Signal
from domain.slot import Placement
from domain.window import Window, WindowKind

_LANE_DIR = re.compile(r"/\.claude/worktrees/card-(\d+)-[^/]*(?:/|$)")
HOOK_SLACK_SECONDS = 60.0
"""The registry stamps its row after the Stop hook has fired (verified live
2026-09-04: THANKS reached the board while the row still read the previous
turn's `blocked`, updated a moment later), so a Stop this close behind the
registry's stamp is the turn's end, not an older one."""
_QUESTION_TAIL = re.compile(r"\?\s*(?:\*+|_+|`+)?\s*$")


class LaneFacts(BaseModel):
    """Everything the lane derivation reads for one project, at one moment."""

    project_path: str
    sessions: list[Session]
    events: list[HookEvent]
    discussions: list[Discussion]
    records: list[LaneRecord]
    windows: list[Window]
    """Windows the runtime holds open."""
    rescues: dict[str, list[Rescue]]
    """By session id."""
    deaths: dict[str, str]
    """The machine's reason a session ended, by session id, when known."""
    worktrees: dict[str, str | None]
    """Worktree path → branch, from git."""
    now: datetime


def card_of_cwd(cwd: str, project_path: str) -> int | None:
    """The card whose lane a working directory is, when it is one."""
    root = project_path.rstrip("/")
    if not (cwd == root or cwd.startswith(root + "/")):
        return None
    match = _LANE_DIR.search(cwd)
    return int(match.group(1)) if match else None


def is_question(text: str | None) -> bool:
    """A message that ends on a question is a question for the owner."""
    if not text:
        return False
    tail = [line for line in text.strip().splitlines() if line.strip()]
    return bool(tail) and _QUESTION_TAIL.search(tail[-1]) is not None


def first_line(text: str | None, limit: int = 160) -> str | None:
    if not text:
        return None
    line = next((ln.strip() for ln in text.strip().splitlines() if ln.strip()), "")
    return line if len(line) <= limit else line[: limit - 1].rstrip() + "…"


def last_line(text: str | None, limit: int = 160) -> str | None:
    """The question is the last thing a session said before it stopped."""
    if not text:
        return None
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    line = lines[-1] if lines else ""
    return line if len(line) <= limit else "…" + line[-(limit - 1) :].lstrip()


def ago(then: datetime | None, now: datetime) -> str:
    if then is None:
        return "a while"
    seconds = max(0, int((now - then).total_seconds()))
    if seconds < 60:
        return f"{seconds} s"
    minutes = round(seconds / 60)
    if minutes < 90:
        return f"{minutes} min"
    hours = round(minutes / 60)
    if hours < 48:
        return f"{hours} h"
    return f"{round(hours / 24)} d"


def _sessions_in(path: str, name: str, facts: LaneFacts, discussing: set[str]) -> list[Session]:
    return [
        s
        for s in facts.sessions
        if not s.stale
        and s.session_id not in discussing
        and (s.worktree == path or s.cwd == path or s.name == name)
    ]


def _winner(sessions: list[Session]) -> Session | None:
    live = [s for s in sessions if s.pid is not None]
    if live:
        return sorted(live, key=lambda s: s.kind != SessionKind.BACKGROUND)[0]
    if not sessions:
        return None
    return max(sessions, key=lambda s: s.updated_at or datetime.min.replace(tzinfo=UTC))


def _last_words(events: list[HookEvent], session: Session | None) -> HookEvent | None:
    pool = [e for e in events if e.message]
    if session is not None:
        own = [e for e in pool if e.session_id == session.session_id]
        pool = own or []
    return max(pool, key=lambda e: e.id) if pool else None


def _moved_sentence(
    rescues: list[Rescue], windows: list[Window], chain: set[str], since: datetime | None
) -> str | None:
    """The rescue sentence for this life of the lane: a move that changed the
    rung, after the lane was last started. An Answer's resume is in the
    ledger too but stays on its rung, and a previous life's move is history
    (verified live 2026-09-04: a relaunched card said "Moved" for a resume
    two lives back)."""
    moves = [r for r in rescues if r.from_rung != r.to_rung and (since is None or r.at >= since)]
    if not moves:
        return None
    last = moves[-1]
    model = last.to_rung.model.value if last.to_rung.model else "fable"
    opened = any(w.session_id in chain and w.opened_at >= last.at for w in windows)
    said = f"Moved to {model} on {last.to_rung.slot}"
    return said + (", new window opened." if opened else ".")


def lane_for(card: Card, facts: LaneFacts) -> Lane:
    name = lane_name(card.number, card.title)
    path = lane_path(facts.project_path, name)
    record = next((r for r in facts.records if r.card_number == card.number), None)
    if record is not None:
        name, path = record.name, record.path
    on_disk = path in facts.worktrees
    discussion_ids = {d.session_id for d in facts.discussions}
    here = _sessions_in(path, name, facts, discussion_ids)
    winner = _winner(here)
    events = [e for e in facts.events if e.card_number == card.number]
    words = _last_words(events, winner)
    said = words.message if words else None
    said_at = words.at if words else None
    discussing = [
        s.short_id
        for s in facts.sessions
        if s.pid is not None
        and not s.stale
        and any(
            d.session_id == s.session_id and d.card_number == card.number for d in facts.discussions
        )
    ]
    # A resume forks the session id (verified live 2026-09-04: `--bg --resume`
    # registers a new sessionId), so the lane's rescues and windows are read
    # across every session that has held this worktree, not the winner alone.
    chain = {s.session_id for s in here}
    window_open = winner is not None and any(
        w.session_id in chain and w.closed_at is None for w in facts.windows
    )
    chain_rescues = sorted(
        (r for sid in chain for r in facts.rescues.get(sid, [])), key=lambda r: r.at
    )
    moved = (
        _moved_sentence(chain_rescues, facts.windows, chain, record.first_seen if record else None)
        if winner is not None
        else None
    )
    folded = record is not None and record.folded_at is not None
    trunk_synced = record is not None and record.trunk_synced_at is not None
    main_synced = record is not None and record.main_synced_at is not None
    since = winner.created_at if winner is not None else None
    start_event = next(
        (
            e
            for e in sorted(events, key=lambda e: e.id)
            if winner is not None
            and e.session_id == winner.session_id
            and e.kind == HookKind.SESSION_START
        ),
        None,
    )
    if start_event is not None and (since is None or start_event.at < since):
        since = start_event.at

    question: str | None = None
    died: str | None = None
    # The registry's word goes stale across a resume (verified live
    # 2026-09-04: a resumed session read `blocked` with the previous life's
    # detail after its own turn had ended). A Stop the hook pushed after the
    # registry last moved is the truer word for a turn's end.
    hook_stopped = (
        words is not None
        and words.kind == HookKind.STOP
        and winner is not None
        and winner.pid is not None
        and (
            winner.updated_at is None
            or words.at >= winner.updated_at - timedelta(seconds=HOOK_SLACK_SECONDS)
        )
        and winner.state != SessionState.WORKING
    )
    # A session cannot have hands on a worktree that is not on disk. Four
    # cards sat in Executing on 2026-09-04 because their sessions' claimed
    # spare processes were still alive hours after 0.1 had torn the worktrees
    # down — the process record said "hands", the disk said "gone". The disk
    # wins: such a lane has ended, whatever /proc says about the process.
    gone = winner is not None and not on_disk
    if winner is not None and winner.pid is not None and not gone:
        where = f"{winner.model.value if winner.model else 'fable'} on {winner.slot}"
        if winner.wall is not None:
            state = LaneState.MOVING
            sentence = (
                f"Hit a limit on {winner.slot} ({first_line(winner.wall.reason)}); "
                f"moving to {winner.wall.account}."
            )
        elif winner.state == SessionState.WORKING:
            state = LaneState.WORKING
            sentence = f"Working, {where}, hands on for {ago(since, facts.now)}."
            if winner.detail:
                sentence += f" {first_line(winner.detail)}"
        elif hook_stopped and is_question(said):
            state = LaneState.ASKING
            question = said
            sentence = f"Asking you: {last_line(said)}"
        elif hook_stopped:
            state = LaneState.STOPPED
            sentence = f"Stopped {ago(said_at, facts.now)} ago, {where}: {first_line(said)}"
        elif winner.state == SessionState.BLOCKED:
            if is_question(winner.detail) or is_question(said):
                state = LaneState.ASKING
                question = said if is_question(said) else winner.detail
                sentence = f"Asking you: {last_line(question)}"
            else:
                state = LaneState.BLOCKED
                sentence = f"Blocked, {where}: {first_line(winner.detail) or 'no detail recorded'}"
        elif winner.kind == SessionKind.INTERACTIVE:
            state = LaneState.WORKING if winner.state == SessionState.WORKING else LaneState.STOPPED
            sentence = f"Your own terminal has hands on it ({winner.short_id} on {winner.slot})."
        elif is_question(said):
            state = LaneState.ASKING
            question = said
            sentence = f"Asking you: {last_line(said)}"
        else:
            state = LaneState.STOPPED
            sentence = f"Stopped {ago(said_at or winner.updated_at, facts.now)} ago, {where}" + (
                f": {first_line(said)}" if said else ", saying nothing."
            )
        if moved:
            sentence = f"{moved} {sentence}"
    elif winner is not None or record is not None or events or on_disk:
        state = LaneState.ENDED
        session_id = winner.session_id if winner is not None else None
        died = facts.deaths.get(session_id) if session_id else None
        if died is None and gone:
            died = "its worktree is gone from disk"
        if died is None:
            end = next(
                (
                    e
                    for e in sorted(events, key=lambda e: -e.id)
                    if e.kind == HookKind.SESSION_END
                    and (session_id is None or e.session_id == session_id)
                ),
                None,
            )
            died = f"the session ended ({end.reason})" if end is not None and end.reason else None
        last_seen = (winner.updated_at if winner is not None else None) or (
            record.last_seen if record is not None else None
        )
        parts = [f"Lane ended {ago(last_seen, facts.now)} ago"]
        if died:
            parts[0] += f": {died}"
        facts_said = [
            word
            for word, held in (
                ("folded", folded),
                ("trunk synced", trunk_synced),
                ("main synced", main_synced),
            )
            if held
        ]
        if facts_said:
            parts.append(", ".join(facts_said))
        elif on_disk:
            parts.append("nothing folded")
        sentence = ". ".join(parts) + "."
    else:
        state = LaneState.NONE
        sentence = ""

    if discussing:
        sentence = (sentence + " " if sentence else "") + (
            f"In discussion with you ({', '.join(discussing)})."
        )

    return Lane(
        card_number=card.number,
        name=name,
        path=path if on_disk else None,
        state=state,
        sentence=sentence.strip(),
        session=winner,
        question=question,
        said=said,
        said_at=said_at,
        discussing=discussing,
        window_open=window_open,
        hands_on_since=since if state in HANDS_ON else None,
        died=died,
        moved=moved,
        folded=folded,
        trunk_synced=trunk_synced,
        main_synced=main_synced,
        edits=[],
        declared=[],
        colliding=None,
    )


def with_footprints(
    lanes: dict[int, Lane], edits: dict[int, set[str]], declared: dict[int, set[str]]
) -> dict[int, Lane]:
    """Every lane with its footprint read in, and each live lane's drift into
    another live lane's files named on both (plan 07, item 2). `edits` is
    what each live worktree has changed, read from git by the caller;
    `declared` is what each card's plan names."""
    colliding = drift(edits)
    out: dict[int, Lane] = {}
    for number, lane in lanes.items():
        out[number] = lane.model_copy(
            update={
                "edits": sorted(edits.get(number, set())),
                "declared": sorted(declared.get(number, set())),
                "colliding": colliding.get(number),
            }
        )
    return out


def conversations_alive(
    sessions: list[Session], discussions: list[Discussion]
) -> list[Conversation]:
    """Every discussion whose session has a live process, for the rail. A
    plan-writing conversation for several cards is one row per card under
    one session, and one line on the rail."""
    by_id: dict[str, list[Discussion]] = {}
    for discussion in discussions:
        by_id.setdefault(discussion.session_id, []).append(discussion)
    alive: list[Conversation] = []
    for session in sessions:
        records = by_id.get(session.session_id)
        if not records or session.pid is None or session.stale:
            continue
        first = records[0]
        numbers = sorted({r.card_number for r in records if r.card_number is not None})
        if first.kind == WindowKind.IDEA or not numbers:
            what = "Idea"
        elif first.kind == WindowKind.PLAN:
            what = "Plan " + ", ".join(f"#{n}" for n in numbers)
        else:
            what = f"#{numbers[0]}"
        alive.append(
            Conversation(
                short_id=session.short_id,
                slot=session.slot,
                card_number=first.card_number,
                what=what,
                started_at=first.started_at,
            )
        )
    return sorted(alive, key=lambda c: c.started_at)


# ── the machine's moves ────────────────────────────────────────────────


def _row_written_after(history: list[AuditEntry], kind: RowKind, since: datetime | None) -> bool:
    for entry in history:
        if (
            entry.kind == AuditKind.ROW
            and entry.detail.startswith(f"{kind.value} ")
            and (since is None or entry.at >= since)
        ):
            return True
    return False


def has_row(card: Card, kind: RowKind) -> bool:
    return any(r.kind == kind for r in card.rows)


def owner_moved_out_after(history: list[AuditEntry], since: datetime | None) -> bool:
    """The owner took the card out of Executing after this life of the lane
    began; the machine never fights him."""
    if since is None:
        return False
    return any(
        e.kind == AuditKind.MOVED
        and e.actor == Actor.OWNER
        and e.from_place is not None
        and e.from_place.column == Column.EXECUTING
        and (e.to_place is None or e.to_place.column != Column.EXECUTING)
        and e.at >= since
        for e in history
    )


def should_enter_executing(card: Card, lane: Lane, history: list[AuditEntry]) -> str | None:
    """The one sentence that moves a card into Executing, or None to leave it."""
    if lane.state not in HANDS_ON or card.place.column == Column.EXECUTING:
        return None
    since = lane.hands_on_since
    if has_row(card, RowKind.DELIVERED) and (
        _row_written_after(history, RowKind.DELIVERED, since) or since is None
    ):
        return None
    if owner_moved_out_after(history, since):
        return None
    if lane.session is None:
        return None
    return f"hands on: {lane.session.short_id} on {lane.session.slot} in {lane.name}"


def came_from(history: list[AuditEntry]) -> Column:
    """Where the card was before it last entered Executing; Up next when the
    record does not say. A re-placement inside Executing (the owner keeping a
    doubted card where it is, plan 05) is not an entry and names no origin."""
    for entry in history:
        if (
            entry.kind == AuditKind.MOVED
            and entry.to_place is not None
            and entry.to_place.column == Column.EXECUTING
            and entry.from_place is not None
            and entry.from_place.column != Column.EXECUTING
        ):
            return entry.from_place.column
    return Column.UP_NEXT


def entered_executing_at(history: list[AuditEntry]) -> datetime | None:
    """When the card last entered Executing, from the record; None when it
    never did. The exit rule's "this life of the lane" starts here when the
    lane itself no longer says: an ended lane has no hands_on_since, which
    read a stale DELIVERED row as current and pinned card #147 on 2026-09-04."""
    for entry in history:
        if (
            entry.kind == AuditKind.MOVED
            and entry.to_place is not None
            and entry.to_place.column == Column.EXECUTING
        ):
            return entry.at
    return None


def close_landed(card: Card) -> bool:
    """A session said it shipped: the plan is archived and DELIVERED is written."""
    return card.link is not None and card.link.archived and has_row(card, RowKind.DELIVERED)


def close_is_current(card: Card, history: list[AuditEntry], since: datetime | None) -> bool:
    """The DELIVERED row belongs to this life of the lane, not a previous one."""
    if since is None:
        return True
    return _row_written_after(history, RowKind.DELIVERED, since)


class Exit(BaseModel):
    column: Column
    reason: str
    evidence: Evidence
    """The predicate the move satisfied, recorded on the audit row and re-tested on every read."""


def exit_for(
    card: Card,
    lane: Lane,
    history: list[AuditEntry],
    *,
    folded: bool | None,
    signal: Signal | None,
    since: datetime | None,
) -> Exit | None:
    """Where a card in Executing goes once no session has hands on it, or
    None to leave it where it is. Asked only of a lane that provably existed
    and ended; a card placed in Executing by hand with no lane stays."""
    if card.place.column != Column.EXECUTING or lane.state != LaneState.ENDED:
        return None
    if owner_moved_out_after(history, since):
        return None
    if close_landed(card) and close_is_current(card, history, since):
        if signal is not None:
            return Exit(
                column=Column.EXECUTED,
                reason="the close landed: the plan is archived and DELIVERED is written",
                evidence=Evidence.CLOSE_LANDED,
            )
        return Exit(
            column=Column.DECISION_MOMENT,
            reason="the close landed, but the WATCH row names no signal the board can read",
            evidence=Evidence.LANE_ENDED,
        )
    if folded:
        return Exit(
            column=Column.DECISION_MOMENT,
            reason="the work folded into origin/develop, but no session wrote it up",
            evidence=Evidence.LANE_ENDED,
        )
    if has_row(card, RowKind.DELIVERED):
        if close_is_current(card, history, since):
            return None  # a close still landing: DELIVERED is this life's word
        return Exit(
            column=Column.DECISION_MOMENT,
            reason="the lane ended; DELIVERED is from a previous life and the close never landed",
            evidence=Evidence.LANE_ENDED,
        )
    if folded is None and lane.session is None:
        return None
    return Exit(
        column=came_from(history),
        reason="the lane ended with nothing folded" + (f" ({lane.died})" if lane.died else ""),
        evidence=Evidence.LANE_ENDED,
    )


ARCHIVE_MOVES_FROM: frozenset[Column] = frozenset(
    {Column.BACKLOG, Column.PLANNED, Column.UP_NEXT, Column.EXECUTING}
)
"""The columns that call a card pending: an archived document there is
shipped work the board is still calling pending (plan 06, item 1). Decision
moment already has the owner's eye; Not now is his ruling; Executed and Done
are where the rule sends things."""


def after_archive(card: Card, lane: Lane, signal: Signal | None) -> Exit | None:
    """Where a card goes when its document is archived and no lane has hands
    on it, or None to leave it. Shipped means archived (INTENT.md): to
    Executed when the close was written up, to Decision moment when nobody
    wrote it up. A live lane's close decides for itself, and a card folded
    under another follows that one."""
    if card.folded_into is not None or card.place.column not in ARCHIVE_MOVES_FROM:
        return None
    if card.link is None or not card.link.archived or lane.state in HANDS_ON:
        return None
    what = f"its {card.link.kind.value} was archived ({card.link.path()})"
    if has_row(card, RowKind.DELIVERED):
        if signal is not None:
            return Exit(
                column=Column.EXECUTED,
                reason=f"{what} and DELIVERED is written: the close landed",
                evidence=Evidence.CLOSE_LANDED,
            )
        return Exit(
            column=Column.DECISION_MOMENT,
            reason=f"{what} and DELIVERED is written, but the WATCH row names no signal the "
            "board can read",
            evidence=Evidence.DOCUMENT_ARCHIVED,
        )
    return Exit(
        column=Column.DECISION_MOMENT,
        reason=f"{what}, but no session wrote it up on the board",
        evidence=Evidence.DOCUMENT_ARCHIVED,
    )


# ── the doors ──────────────────────────────────────────────────────────

STARTABLE_COLUMNS: frozenset[Column] = frozenset({Column.UP_NEXT, Column.PLANNED})
UNREAD = "the runtime has not read this board yet"


def nothing_read(card: Card, project_path: str, now: datetime) -> tuple[Lane, "Doors"]:
    """A card's lane and doors before the loop's first read: a lane derived
    from no facts, and every door closed for that reason."""
    lane = lane_for(
        card,
        LaneFacts(
            project_path=project_path,
            sessions=[],
            events=[],
            discussions=[],
            records=[],
            windows=[],
            rescues={},
            deaths={},
            worktrees={},
            now=now,
        ),
    )
    doors = doors_for(
        card,
        lane,
        gate_named=True,
        placement=None,
        placement_note=UNREAD,
        collision=None,
        signal=None,
        signal_due_for_owner=False,
        signal_evidence=None,
        suggestion_live=card.link is not None
        and card.link.kind == DocumentKind.SUGGESTION
        and not card.link.archived,
    )
    return lane, doors


def _closed(label: str, why: str) -> Door:
    return Door(offered=False, label=label, why=why)


def _open(label: str, why: str) -> Door:
    return Door(offered=True, label=label, why=why)


def doors_for(
    card: Card,
    lane: Lane,
    *,
    gate_named: bool,
    placement: Placement | None,
    placement_note: str,
    collision: Collision | None,
    signal: Signal | None,
    signal_due_for_owner: bool,
    signal_evidence: str | None,
    suggestion_live: bool,
) -> Doors:
    """`suggestion_live`: the card's document is a suggestion still in its
    live folder, so Plan may write the plan that carries it. `signal_evidence`
    is a reading session's cannot-tell in its words, when that is why the
    owner is asked (plan 09, item 4)."""
    live = lane.session is not None and lane.session.pid is not None and lane.state in HANDS_ON
    background = live and lane.session is not None and lane.session.kind == SessionKind.BACKGROUND
    collides = collision is not None and collision.verdict == CollisionVerdict.COLLIDES

    # Start and the pill are one judgment: each branch names both.
    if not gate_named:
        start = _closed(
            "Start", "This card names no effort gate; only a planned card is startable."
        )
        state = StartState.NO_GATE
    elif live:
        start = _closed("Start", f"A session already has hands on it: {lane.sentence}")
        state = StartState.TAKEN
    elif lane.path is not None:
        start = _closed(
            "Start",
            f"The lane {lane.name} already exists at {lane.path}; Resume or Look at it instead.",
        )
        state = StartState.TAKEN
    elif card.place.column not in STARTABLE_COLUMNS:
        start = _closed(
            "Start",
            f"Start is offered in Up next and Planned; this card is in {card.place.column}.",
        )
        state = StartState.ELSEWHERE
    elif placement is None:
        start = _closed("Start", f"The rule found nowhere to run: {placement_note}")
        state = StartState.UNREAD if placement_note == UNREAD else StartState.NOWHERE
    elif collides:
        assert collision is not None
        start = _closed("Start", f"Lane collision — {collision.sentence}")
        state = StartState.COLLIDES
    else:
        start = _open(
            f"Start · {placement.model.value} on {placement.slot}",
            placement.why,
        )
        state = StartState.FREE
    readiness = Readiness(
        state=state,
        why=start.why,
        cards=collision.cards if collision is not None and collides else [],
        files=collision.files if collision is not None and collides else [],
    )
    start_anyway = (
        _open(
            f"Start anyway · {placement.model.value} on {placement.slot}",
            f"Overrides the collision with its reason in front of you: {collision.sentence}",
        )
        if not start.offered
        and collision is not None
        and collision.verdict == CollisionVerdict.COLLIDES
        and placement is not None
        and gate_named
        and card.place.column in STARTABLE_COLUMNS
        and not live
        and lane.path is None
        else _closed("Start anyway", "There is no collision to override.")
    )
    if background:
        if lane.window_open:
            # A window that is open is a door too (plan 04, item 2): the
            # owner looked for Watch on #387 and found it gone, its reason in
            # a tooltip nobody hovers.
            watch = _open(
                "Focus its window",
                "Brings the open window into this session forward, through the compositor.",
            )
        else:
            watch = _open("Watch", "Opens a window into the live session; closing it ends nothing.")
    elif live:
        watch = _closed(
            "Watch", "The session runs in your own terminal; that terminal is its window."
        )
    else:
        watch = _closed("Watch", "No live session to watch.")
    if background and lane.state in {LaneState.ASKING, LaneState.STOPPED, LaneState.BLOCKED}:
        answer = _open("Answer", "Your sentence resumes the lane with it; one live copy stays.")
    elif background:
        answer = _closed("Answer", "The session is working; answer it when it stops.")
    elif live:
        answer = _closed("Answer", "The session runs in your own terminal; answer it there.")
    else:
        answer = _closed("Answer", "No live session to answer.")
    discuss = (
        _open("Discuss", "A fresh conversation about this card, never hands on its tree.")
        if placement is not None
        else _closed("Discuss", f"The rule found nowhere to run: {placement_note}")
    )
    # The door says what it does, and says it the same on both faces of the
    # card: "Create plan" collapsed and open (plan 27, item 2).
    if not suggestion_live:
        plan = _closed(
            "Create plan",
            "Plan writes the plan for a suggestion; this card is not behind a live suggestion.",
        )
    elif placement is None:
        plan = _closed("Create plan", f"The rule found nowhere to run: {placement_note}")
    else:
        plan = _open(
            "Create plan",
            "Opens a plan-writing conversation for this suggestion; the plan it writes "
            "carries the card.",
        )
    if lane.state == LaneState.ENDED and lane.session is not None and lane.path is None:
        gone = "The lane's worktree is gone; Start opens a fresh one."
        look, resume = _closed("Look", gone), _closed("Resume", gone)
    elif lane.state == LaneState.ENDED and lane.session is not None:
        look = (
            _open(
                "Look",
                "A fresh session in the worktree from the transcript; its first line says so.",
            )
            if placement is not None
            else _closed("Look", f"The rule found nowhere to run: {placement_note}")
        )
        resume = (
            _open("Resume", "Resumes the lane's session where the rule says.")
            if placement is not None and lane.session.kind == SessionKind.BACKGROUND
            else _closed("Resume", "Only a background session can be resumed.")
        )
    else:
        why = "The session is live; watch it instead." if live else "No session to look at."
        look = _closed("Look", why)
        resume = _closed("Resume", why)
    stop = (
        _open("Stop", "Ends the session through its own slot and says where the card is then.")
        if background
        else _closed("Stop", "No background session to stop.")
    )
    if signal is not None and signal_due_for_owner and signal_evidence is not None:
        signal_door = _open(
            "Delivered?",
            f"A session read this signal and could not tell — {signal_evidence}",
        )
    elif signal is not None and signal_due_for_owner:
        signal_door = _open(
            "Delivered?",
            f"Only you can read this signal: {signal.what} — due {signal.due.isoformat()}.",
        )
    else:
        signal_door = _closed("Delivered?", "No signal waits on your reading.")
    return Doors(
        start=start,
        start_anyway=start_anyway,
        readiness=readiness,
        placement=placement,
        placement_note=placement_note,
        collision=collision,
        watch=watch,
        answer=answer,
        discuss=discuss,
        plan=plan,
        look=look,
        resume=resume,
        stop=stop,
        signal=signal_door,
    )
