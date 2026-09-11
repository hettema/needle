"""What a card's lane is doing, read from the facts the loop gathers, and
which doors the card offers. Pure: the runtime, the hooks and the store are
read by the caller and handed in as domain values.

Executing is a machine fact (INTENT.md lesson 2): a live session in the
card's worktree is hands on, and only that. A discussion session is never
hands on. A session with no process is never working, whatever the registry
says (the runtime already holds that; this module only reads its verdict).
"""

import re
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta

from pydantic import BaseModel

from board.brief import lane_name, lane_path
from board.collision import drift
from board.sequencing import holding, where
from board.title import hold_sentence
from domain.audit import AuditEntry, AuditKind
from domain.card import Actor, Card
from domain.column import Column
from domain.document import DocumentKind
from domain.ending import Cause, Death, Disposition, Park
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
    Progress,
    Readiness,
    StartState,
    Wait,
)
from domain.launch import Rescue
from domain.meaning import Meaning, say
from domain.row import RowKind
from domain.session import Session, SessionKind, SessionState
from domain.signal import Signal
from domain.slot import Make, Placement, rung_words
from domain.triage import Routed, Routing
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
    deaths: dict[str, Death]
    """Why a session's process is gone, by session id, as the board could
    establish it at the end (plan 68, item 1)."""
    parks: dict[int, Park] = {}
    """The park standing on each card's lane, by card number (plan 68, item 3)."""
    worktrees: dict[str, str | None]
    """Worktree path → branch, from git."""
    now: datetime
    many_machines: bool = False
    """The board knows more than one machine (card #83): only then does a
    lane say which machine its session runs on — on a one-machine board
    the word carries nothing, and the owner is not to know which machine
    ran a card unless he looks."""
    last_read: dict[str, datetime] = {}
    """Each machine whose reading is not this pass's, with when it last
    answered (card #123): a lane on one says so on its card, so an old
    reading is never mistaken for a live one."""


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


_ASKS_OWNER = re.compile(
    r"\bnothing (?:can move|moves|proceeds|happens) until you\b"
    r"|\b(?:waiting|waits|wait) (?:for|on) your (?:ruling|call|decision|word|answer)\b"
    r"|\byour (?:ruling|call|decision|answer) is needed\b"
    r"|\buntil you (?:rule|decide|answer|say|confirm)\b",
    re.I,
)


def asks_owner(text: str | None) -> bool:
    """Whether a session's whole last message puts a decision to the owner
    (plan 68, ruling 7). `is_question`'s test on the last line is the door's
    discriminator for a live session; a dead one is read whole: a question
    mark closing any line, or a sentence that says nothing moves until he
    rules — #452's "nothing can move until you rule" ended in no question
    mark and was read as mid-work."""
    if not text:
        return False
    if any(_QUESTION_TAIL.search(line) for line in text.strip().splitlines() if line.strip()):
        return True
    return _ASKS_OWNER.search(text) is not None


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


def where_of(session: Session) -> str:
    """Where a session runs, as the board says it: its model and slot when
    the row recorded a model, else the slot alone. The board used to say
    `fable` for a row with no model recorded, which was a guess for a
    terminal of the owner's and a false claim for a session of another
    make (plan 57); every face builds the words in one place now
    (`domain.slot.rung_words`, card #63) so none of them can start
    guessing again."""
    return rung_words(session.model, session.slot)


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
    opened = any(w.session_id in chain and w.opened_at >= last.at for w in windows)
    said = f"It moved to {rung_words(last.to_rung.model, last.to_rung.slot)}"
    return said + (", and a new window opened." if opened else ".")


def _asking(question: str, moved: str | None) -> str:
    return say(
        Meaning.YOURS,
        "answer its question",
        why=(f"{moved} " if moved else "") + f"the session on it stopped to ask: {question}",
        then="nothing moves until you do",
    )


def _stopped(when: str, where: str, said: str | None, moved: str | None) -> str:
    return say(
        Meaning.YOURS,
        "read what it said and answer",
        why=(f"{moved} " if moved else "")
        + f"the session on it stopped {when} ago, {where}"
        + (f": {said}" if said else ", saying nothing"),
        then="it waits for your word",
    )


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
    cause: Cause | None = None
    park = facts.parks.get(card.number)
    parked = park.words if park is not None and park.lifted_at is None else None
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
        where = where_of(winner)
        if winner.wall is not None:
            state = LaneState.MOVING
            # The moving sentence reads the cause the handoff carries, never
            # the existence of a handoff (plan 68, item 3): the machine's
            # connection recovery and its switch-back write the same file.
            asks = winner.wall.cause
            if asks == Cause.RECOVERED:
                what = (
                    f"the session on it stopped on a dropped connection and the connection is "
                    f"back; it is being put back to work on {winner.wall.account}"
                )
            elif asks == Cause.STRONGER_MODEL:
                what = (
                    f"the stronger model is back for the session on it; it is being moved onto "
                    f"it on {winner.wall.account}"
                )
            else:
                what = (
                    f"the session on it ran out of allowance on {winner.slot} and is moving to "
                    f"{winner.wall.account}"
                )
            sentence = say(
                Meaning.LIVE,
                what,
                why=first_line(winner.wall.reason),
                then=parked or "it carries on by itself once it lands",
            )
        elif winner.state == SessionState.WORKING:
            state = LaneState.WORKING
            sentence = say(
                Meaning.LIVE,
                f"a session is working on it, {where}, for {ago(since, facts.now)}",
                why=moved,
                then=first_line(winner.detail) if winner.detail else None,
            )
        elif hook_stopped and is_question(said):
            state = LaneState.ASKING
            question = said
            sentence = _asking(last_line(said), moved)
        elif hook_stopped:
            state = LaneState.STOPPED
            sentence = _stopped(ago(said_at, facts.now), where, first_line(said), moved)
        elif winner.state == SessionState.BLOCKED:
            if is_question(winner.detail) or is_question(said):
                state = LaneState.ASKING
                question = said if is_question(said) else winner.detail
                sentence = _asking(last_line(question), moved)
            else:
                state = LaneState.BLOCKED
                sentence = say(
                    Meaning.YOURS,
                    "unblock it",
                    why=(f"{moved} " if moved else "")
                    + f"the session on it is stuck, {where}: "
                    + (first_line(winner.detail) or "it recorded no detail"),
                    then="nothing moves until you do",
                )
        elif winner.kind == SessionKind.INTERACTIVE:
            if winner.state == SessionState.WORKING:
                state = LaneState.WORKING
                sentence = say(
                    Meaning.LIVE,
                    f"your own terminal is working on it ({winner.short_id} on {winner.slot})",
                    why=moved,
                )
            else:
                state = LaneState.STOPPED
                sentence = say(
                    Meaning.YOURS,
                    "carry on in your own terminal",
                    why=f"it has hands on this card ({winner.short_id} on {winner.slot}) and "
                    "has stopped",
                    then="nothing moves until you type there",
                )
        elif is_question(said):
            state = LaneState.ASKING
            question = said
            sentence = _asking(last_line(said), moved)
        else:
            state = LaneState.STOPPED
            sentence = _stopped(
                ago(said_at or winner.updated_at, facts.now), where, first_line(said), moved
            )
    elif winner is not None or record is not None or events or on_disk:
        state = LaneState.ENDED
        session_id = winner.session_id if winner is not None else None
        death = facts.deaths.get(session_id) if session_id else None
        if death is not None:
            died, cause = death.words, death.cause
        if died is None and gone:
            died = "its own copy of the code is gone from disk"
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
        landed = [
            word
            for word, held in (
                ("its work landed on the shared branch", folded),
                ("the main checkout is level with it", trunk_synced),
                ("the stable branch is level with it", main_synced),
            )
            if held
        ]
        when = f"the session on it ended {ago(last_seen, facts.now)} ago"
        # Only a fold says the work landed; a level checkout beside an
        # unfolded lane says nothing about this card, and the face is red.
        # A lane that folded is finished, not dead: its sentence leads with
        # the fold and names no cause of death, and the `died` line under
        # the band is for a lane that died (plan 68, item 1). A parked lane
        # is the machine's: it says what it waits on and comes back by
        # itself, so nothing is asked of him and the face is quiet.
        if folded:
            died, cause = None, None
            sentence = say(
                Meaning.QUIET,
                f"its work landed on the shared branch and {when}",
                why="; ".join(landed[1:]) or None,
            )
        elif close_landed(card):
            # Finished work: the card's close landed, and the session's
            # ending is the normal end of it, not a death to show.
            died, cause = None, None
            sentence = say(Meaning.QUIET, f"its close landed and {when}")
        elif parked is not None:
            sentence = say(
                Meaning.QUIET,
                f"{when} and the board brings it back by itself",
                why=died,
                then=parked,
            )
        elif asks_owner(said):
            sentence = say(
                Meaning.YOURS,
                "decide what it asked and bring it back",
                why=f"{when} after putting a decision to you: {last_line(said)}",
                then="open the card to resume it once you have decided",
            )
        elif on_disk:
            sentence = say(
                Meaning.BROKEN,
                f"{when} with nothing landed",
                why=died,
                then="open the card to resume it or start again",
            )
        else:
            sentence = say(Meaning.BROKEN, when, why=died, then="open the card to start again")
    else:
        state = LaneState.NONE
        sentence = ""

    if discussing:
        talk = f"In discussion with you ({', '.join(discussing)})."
        # A discussion beside a lane is one more clause of its sentence; on
        # its own it is the sentence, live because the conversation is.
        sentence = f"{sentence} {talk}" if sentence else say(Meaning.LIVE, talk[:-1])

    if winner is not None and winner.machine in facts.last_read and sentence:
        # The machine has not answered since its last reading (card #123):
        # the lane stands as last read, and the card says how old that is.
        age = ago(facts.last_read[winner.machine], facts.now)
        sentence = (
            f"{sentence} As {winner.machine} last answered, {age} ago; "
            "it has not answered since."
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
        cause=cause,
        park=parked if state in (LaneState.ENDED, LaneState.MOVING, LaneState.BLOCKED) else None,
        moved=moved,
        folded=folded,
        trunk_synced=trunk_synced,
        main_synced=main_synced,
        edits=[],
        declared=[],
        colliding=None,
        machine=winner.machine if winner is not None and facts.many_machines else None,
    )


def with_footprints(
    lanes: dict[int, Lane],
    edits: dict[int, set[str]],
    declared: dict[int, set[str]],
    progress: dict[int, Progress | None] | None = None,
) -> dict[int, Lane]:
    """Every lane with its footprint read in, and each live lane's drift into
    another live lane's files named on both (plan 07, item 2). `edits` is
    what each live worktree has changed, read from git by the caller;
    `declared` is what each card's plan names; `progress` how far each
    live lane has come, from its own copy of the plan (plan 13)."""
    colliding = drift(edits)
    out: dict[int, Lane] = {}
    for number, lane in lanes.items():
        out[number] = lane.model_copy(
            update={
                "edits": sorted(edits.get(number, set())),
                "declared": sorted(declared.get(number, set())),
                "colliding": colliding.get(number),
                "progress": (progress or {}).get(number),
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
        if first.kind == WindowKind.FOCUS:
            what = "Focus"
        elif first.kind == WindowKind.IDEA or not numbers:
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
                kind=first.kind,
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


def owner_decision_outstanding(
    card: Card, history: list[AuditEntry], since: datetime | None
) -> str | None:
    """A decision of the owner's still standing on the card's rows: an ASK
    or a Q row, or a RULING with no RULED beneath it (plan 68, ruling 7),
    written in this life of the lane — a row from a previous life is a
    question already answered or overtaken, and `since` is None only for
    a card the board never saw start, whose rows all count."""
    for kind in (RowKind.ASK, RowKind.Q):
        row = next((r for r in card.rows if r.kind == kind), None)
        if row is not None and (since is None or _row_written_after(history, kind, since)):
            return f"the card carries a {kind.value} row: {first_line(row.text)}"
    ruling = next((r for r in card.rows if r.kind == RowKind.RULING), None)
    if (
        ruling is not None
        and (since is None or _row_written_after(history, RowKind.RULING, since))
        and not (
            has_row(card, RowKind.RULED)
            and (since is None or _row_written_after(history, RowKind.RULED, since))
        )
    ):
        return f"the card carries a RULING row nobody has ruled on: {first_line(ruling.text)}"
    return None


def disposition(
    card: Card, lane: Lane, history: list[AuditEntry], since: datetime | None
) -> tuple[Disposition, str]:
    """What the work stood at when the session stopped, read from the
    card's record before any recovery (plan 68, item 4 and ruling 7): a
    current close is finished work whatever the lane's row says; a
    question, an owner's row or his own move out of Executing is his; and
    only the rest is unfinished. `since` is this life of the lane, as the
    exit rule reads it. The registry's state and the transcript's last
    line are never read here: they say what the session was doing."""
    if close_landed(card) and close_is_current(card, history, since):
        return Disposition.CLOSED, "its close landed: the plan is archived and DELIVERED is written"
    if lane.state == LaneState.ASKING and lane.question:
        return Disposition.OWNERS, f"it asked you: {last_line(lane.question)}"
    if lane.state == LaneState.ENDED and asks_owner(lane.said):
        return Disposition.OWNERS, f"its last words put a decision to you: {last_line(lane.said)}"
    outstanding = owner_decision_outstanding(card, history, since)
    if outstanding is not None:
        return Disposition.OWNERS, outstanding
    if owner_moved_out_after(history, since):
        return Disposition.OWNERS, "you moved the card out of Executing yourself"
    if card.place.column == Column.NOT_NOW:
        return Disposition.OWNERS, "you put the card in Not now"
    if card.place.column == Column.DECISION_MOMENT:
        return Disposition.OWNERS, "the card sits in Decision moment, where only you move it"
    return Disposition.UNFINISHED, "no close landed and no question stands on the card"


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


def placement_from(history: list[AuditEntry]) -> AuditEntry | None:
    """The audit row that put the card where it is: the newest move, else its
    birth. `history` is newest first, as the store answers it."""
    for entry in history:
        if entry.kind in (AuditKind.MOVED, AuditKind.BORN) and entry.to_place is not None:
            return entry
    return None


def unpark(card: Card, lane: Lane, history: list[AuditEntry]) -> Exit | None:
    """The machine undoes its own park when the evidence for it is gone (the
    plan "as many lanes as the machine can hold", item 5): a card in
    Decision moment whose last move was the machine's *archived* move, and
    whose link is a live plan now, goes back to Planned. On a checkout the
    runtime levels by fast-forward, the watcher read Hello Revenue #384's
    suggestion rename ten seconds before its plan and parked the card; the
    one-read fix from plan 11 never applied, and no machine move left the
    column. A card whose link is still archived stays parked; a card the
    owner moved is his."""
    if card.folded_into is not None or card.place.column != Column.DECISION_MOMENT:
        return None
    if card.link is None or card.link.archived or card.link.kind != DocumentKind.PLAN:
        return None
    if lane.state in HANDS_ON:
        return None
    placement = placement_from(history)
    if (
        placement is None
        or placement.actor != Actor.MACHINE
        or placement.evidence != Evidence.DOCUMENT_ARCHIVED
    ):
        return None
    return Exit(
        column=Column.PLANNED,
        reason=(
            "parked when its suggestion was archived, but a live plan carries it now "
            f"({card.link.path()}): back to Planned"
        ),
        evidence=Evidence.PLAN_LIVE,
    )


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
        waits=[],
    )
    return lane, doors


def driver(placement: Placement) -> str:
    """Who will drive this card, as the Start door names it: the rung the
    rule chose, and the make beside it when the make is not the one every
    lane used to be (card #63). Naming the make on every rung would put
    "claude" on a board that has said `fable on eduard` since its first
    day; naming it only when it is news is what the owner reads."""
    words = rung_words(placement.model, placement.slot)
    if placement.make is not Make.CLAUDE:
        words = f"{words} ({placement.make.value})"
    # The machine is news only when the board knows more than one: the
    # loop blanks it otherwise (card #83), so a one-machine board reads as
    # it always has and a two-machine board says where the card would run.
    return f"{words} on {placement.machine}" if placement.machine else words


def why_this_driver(placement: Placement) -> str:
    """The rule's reason for this rung, and the owner's dated ruling behind
    it when the rule carried one. The tier is his and is dated on purpose:
    it is a ruling the evidence may move, not a fact the code asserts, so
    the date is on the face where he can see it going stale (card #63,
    item 4)."""
    tier = placement.tier
    if tier is None:
        return placement.why
    said = (
        f"{placement.why}; your ruling of {tier.ruled_on.isoformat()} puts it in tier {tier.rank}"
    )
    return f"{said} ({tier.why})" if tier.why else said


def _nowhere(label: str, placement_note: str) -> Door:
    """A door closed because the rule found nowhere to run: before the
    board's first read that is only the wait, after it the accounts."""
    if placement_note == UNREAD:
        return _closed(
            label,
            Meaning.QUIET,
            "the board has not read this project yet, so nothing can start",
            then="it reads within a minute and Start opens by itself",
        )
    return _closed(
        label,
        Meaning.QUIET,
        "nothing can start right now because no account has room to run it",
        why=placement_note,
        then="it starts by itself when one does",
    )


def _names(labels: Iterable[str]) -> str:
    names = list(labels)
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + f" and {names[-1]}"


def _closed(
    label: str, meaning: Meaning, what: str, *, why: str | None = None, then: str | None = None
) -> Door:
    """A door that does not open, with why in the shape of the meaning that
    closes it: quiet when nothing is asked of him, live when a session is on
    it, broken when two things disagree (card #75)."""
    return Door(offered=False, label=label, why=say(meaning, what, why=why, then=then))


def _open(label: str, what: str, *, why: str | None = None, then: str | None = None) -> Door:
    """A door that opens is his move by definition — only he presses it — so
    its reason opens with his part, whatever colour the face wears."""
    return Door(offered=True, label=label, why=say(Meaning.YOURS, what, why=why, then=then))


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
    waits: list[Wait],
    routed: Routed | None = None,
    ruled: str | None = None,
    title_hold: str | None = None,
) -> Doors:
    """`suggestion_live`: the card's document is a suggestion still in its
    live folder, so Plan may write the plan that carries it. `signal_evidence`
    is a reading session's cannot-tell in its words, when that is why the
    owner is asked (plan 09, item 4). `waits` is every card the plan's
    Sequencing line names, placed: the one hold on a Start that is another
    card's (`board/sequencing.py`). `routed` is where a defect routes right
    now and `ruled` his own answer to this reading when he has already given
    one: together they are what opens Answer on a card with no session at
    all, exactly once (plan 59, item 5). `title_hold` is why a cold reading
    could not place the card from its title, when the last one could not
    (card #74, item 3): the one hold that is the board's on every project's
    card, since Start is the one door every card goes through."""
    live = lane.session is not None and lane.session.pid is not None and lane.state in HANDS_ON
    background = live and lane.session is not None and lane.session.kind == SessionKind.BACKGROUND
    shares = collision is not None and collision.verdict == CollisionVerdict.COLLIDES
    held_by = holding(waits)

    # Start and the state word are one judgment: each branch names both.
    if not gate_named:
        start = _closed(
            "Start",
            Meaning.QUIET,
            "this cannot start because its plan names no effort level",
            then="Discuss it and a plan with one carries it",
        )
        state = StartState.NO_GATE
    elif live:
        start = _closed(
            "Start",
            Meaning.LIVE,
            "a session already has hands on it, so Start is closed",
            why=lane.sentence,
        )
        state = StartState.TAKEN
    elif lane.path is not None:
        start = _closed(
            "Start",
            Meaning.QUIET,
            "work on it began before and its own copy of the code is still on disk",
            why=f"at {lane.path}",
            then="open the card to resume that work or look at it; Start is closed while it stays",
        )
        state = StartState.TAKEN
    elif card.place.column not in STARTABLE_COLUMNS:
        start = _closed(
            "Start",
            Meaning.QUIET,
            f"a card starts from Up next or Planned, and this one is in {card.place.column}",
            then="move it there to start it",
        )
        state = StartState.ELSEWHERE
    elif title_hold is not None:
        # The owner ranks from the title alone; a card he cannot place is
        # not started until the writer has rewritten it and a reading with
        # no share of the writer's context has passed it (card #74, item 3).
        start = Door(offered=False, label="Start", why=hold_sentence(title_hold))
        state = StartState.TITLE_FAILS
    elif placement is None:
        start = _nowhere("Start", placement_note)
        state = StartState.UNREAD if placement_note == UNREAD else StartState.NOWHERE
    elif held_by:
        # The plan's own word is the one hold (ruling 3): it says which
        # cards it waits on, and the door opens by itself once they ship.
        start = _closed(
            "Start",
            Meaning.QUIET,
            f"this starts by itself once {_names(where(w) for w in held_by)} "
            f"{'ships' if len(held_by) == 1 else 'ship'}",
            then=f"move {_names(w.label for w in held_by)} up to have it sooner",
        )
        state = StartState.WAITS
    elif shares:
        # Shared ground is a cost the door shows, never a reason to close
        # (INTENT.md lesson 4): the label says what it shares, the reason
        # names the sessions and the files, and the fold settles it.
        assert collision is not None
        count = len(collision.files)
        start = _open(
            f"Start · {driver(placement)} — shares "
            f"{count} file{'' if count == 1 else 's'} with "
            + ", ".join(f"#{n}'s session" for n in collision.cards)
            + "; the second to finish catches up",
            f"press it and a session takes this card, {driver(placement)}",
            why=collision.sentence,
        )
        state = StartState.SHARES
    else:
        start = _open(
            f"Start · {driver(placement)}",
            f"press it and a session takes this card, {driver(placement)}",
            why=why_this_driver(placement),
        )
        state = StartState.FREE
    readiness = Readiness(
        state=state,
        why=start.why,
        cards=collision.cards if collision is not None and state == StartState.SHARES else [],
        files=collision.files if collision is not None and state == StartState.SHARES else [],
        waits=held_by if state == StartState.WAITS else [],
    )
    if background:
        if lane.window_open:
            # A window that is open is a door too (plan 04, item 2): the
            # owner looked for Watch on #387 and found it gone, its reason in
            # a tooltip nobody hovers.
            watch = _open(
                "Focus its window",
                "press it and the open window into this session comes forward",
            )
        else:
            watch = _open(
                "Watch",
                "press it and a window opens into the live session",
                then="closing that window ends nothing",
            )
    elif live:
        watch = _closed(
            "Watch",
            Meaning.QUIET,
            "the session runs in your own terminal, and that terminal is its window",
        )
    else:
        watch = _closed("Watch", Meaning.QUIET, "there is no live session to watch")
    if background and lane.state in {LaneState.ASKING, LaneState.STOPPED, LaneState.BLOCKED}:
        answer = _open(
            "Answer",
            "your sentence resumes the session with it",
            then="one live copy stays on the card",
        )
    elif background:
        answer = _closed(
            "Answer", Meaning.LIVE, "the session is working", then="answer it when it stops"
        )
    elif live:
        answer = _closed(
            "Answer",
            Meaning.QUIET,
            "the session runs in your own terminal",
            then="answer it there",
        )
    elif ruled is not None:
        answer = _closed("Answer", Meaning.QUIET, "you have ruled on this already", why=ruled)
    elif routed is not None and routed.state == Routing.TRIAGED_HIS:
        # The one card with no session that has a door (plan 59, item 5): a
        # defect an independent reading put on his pile. Before this it had
        # none, and the pile drained at zero for the board's whole life.
        answer = _open(
            "Answer",
            "rule on who fixes this",
            why="a second reading says the decision is yours",
            then="your sentence is the ruling, and a short session writes it into the "
            "document, citing your answer",
        )
    else:
        answer = _closed("Answer", Meaning.QUIET, "there is no live session to answer")
    discuss = (
        _open(
            "Discuss",
            "press it and a fresh conversation about this card opens",
            then="it never touches the card's own code",
        )
        if placement is not None
        else _nowhere("Discuss", placement_note)
    )
    # The door says what it does, and says it the same on both faces of the
    # card: "Create plan" collapsed and open (plan 27, item 2).
    if not suggestion_live:
        plan = _closed(
            "Create plan",
            Meaning.QUIET,
            "Create plan writes the plan for a suggestion, and this card is not behind a live one",
        )
    elif placement is None:
        plan = _nowhere("Create plan", placement_note)
    else:
        plan = _open(
            "Create plan",
            "press it and a plan-writing conversation opens for this suggestion",
            then="the plan it writes carries the card",
        )
    if lane.state == LaneState.ENDED and lane.session is not None and lane.path is None:
        gone = "the session's own copy of the code is gone"
        look = _closed("Look", Meaning.QUIET, gone, then="Start opens a fresh one")
        resume = _closed("Resume", Meaning.QUIET, gone, then="Start opens a fresh one")
    elif lane.state == LaneState.ENDED and lane.session is not None:
        look = (
            _open(
                "Look",
                "press it and a fresh session opens on the same copy of the code, reading "
                "the old one's transcript",
                then="its first line says so",
            )
            if placement is not None
            else _nowhere("Look", placement_note)
        )
        resume = (
            _open("Resume", "press it and the session picks up where it stopped")
            if placement is not None and lane.session.kind == SessionKind.BACKGROUND
            else _closed("Resume", Meaning.QUIET, "only a session nobody watches can be resumed")
        )
    else:
        if live:
            look = _closed("Look", Meaning.LIVE, "the session is live", then="watch it instead")
            resume = _closed("Resume", Meaning.LIVE, "the session is live", then="watch it instead")
        else:
            look = _closed("Look", Meaning.QUIET, "there is no session to look at")
            resume = _closed("Resume", Meaning.QUIET, "there is no session to look at")
    stop = (
        _open(
            "Stop",
            "press it and the session ends through its own account",
            then="the card says where it is then",
        )
        if background
        else _closed("Stop", Meaning.QUIET, "there is no session in the background to stop")
    )
    if signal is not None and signal_due_for_owner and signal_evidence is not None:
        signal_door = _open(
            "Delivered?",
            "say whether this signal delivered",
            why=f"a session read it and could not tell: {signal_evidence}",
        )
    elif signal is not None and signal_due_for_owner:
        signal_door = _open(
            "Delivered?",
            "say whether this signal delivered",
            why=f"only you can read it: {signal.what}, due {signal.due.isoformat()}",
        )
    else:
        signal_door = _closed("Delivered?", Meaning.QUIET, "no signal waits on your reading")
    return Doors(
        start=start,
        readiness=readiness,
        placement=placement,
        placement_note=placement_note,
        collision=collision,
        waits=waits,
        watch=watch,
        answer=answer,
        discuss=discuss,
        plan=plan,
        look=look,
        resume=resume,
        stop=stop,
        signal=signal_door,
    )
