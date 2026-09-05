"""`needle`'s runtime verbs: the four jobs of the runtime from the command line.

needle sessions [--json]
needle where [--from SLOT] [--tried RUNG,...] [--live] [--json]
needle start REPO CARD "BRIEF" [--effort LEVEL] [--from SLOT] [--json]
needle move SHORT [--to SLOT] [--json]
needle stop SHORT [--json]
needle window SHORT [--as KIND] [--json]
needle focus SHORT [--json]
needle rescues SHORT [--clear] [--json]
needle call WHO NOTE [--objective TEXT] [--answer PATH] [--json]
needle wait CALL [--ceiling SECONDS] [--json]

Each verb is a thin call into `runtime.service.Runtime`, answers in prose or
as the domain value's JSON, and exits 1 when the thing asked for did not
happen. The owner's terminal, the board and a script all read the same
answer.
"""

import argparse
import json
import os
import re
import sys
import time
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from domain.call import CallOutcome, CallVerdict
from domain.gate import Gate
from domain.launch import Launch, LaunchVerdict, Start
from domain.session import Session
from domain.slot import Model, Rung
from domain.window import WindowKind
from infrastructure import clock
from infrastructure.paths import db_path
from infrastructure.store import Store
from runtime import calls
from runtime.service import NoSuchSession, Runtime
from runtime.windows import WindowRefused

WAIT_CEILING_SECONDS = 600.0
"""How long `needle wait` waits by default: the slowest reply of the
baseline morning took twelve minutes, so ten is a ceiling a caller states
rather than the norm."""
WAIT_FILE_SECONDS = 0.25
"""How often the answer file is looked at: a note lands and the waiter
returns within a second (plan 17, item 2)."""
WAIT_LIST_SECONDS = 2.0
"""How often the one list is read while waiting: a colleague that is
blocked, moved or ended is reported within this, and reading every
registry more often buys nothing."""
_FROM = re.compile(r"^from-[A-Za-z0-9]+-")

Verb = Callable[[Runtime, argparse.Namespace], int]


def _with_runtime(verb: Verb) -> Callable[[argparse.Namespace], int]:
    def run(args: argparse.Namespace) -> int:
        store = Store(db_path())
        try:
            return verb(Runtime(store), args)
        except NoSuchSession as missing:
            print(str(missing), file=sys.stderr)
            return 1
        finally:
            store.close()

    return run


def _emit(args: argparse.Namespace, value: BaseModel | Sequence[BaseModel], text: str) -> None:
    if args.json:
        payload = (
            value.model_dump(mode="json")
            if isinstance(value, BaseModel)
            else [v.model_dump(mode="json") for v in value]
        )
        print(json.dumps(payload, indent=2))
    else:
        print(text)


def parse_rung(text: str) -> Rung:
    slot, _, model = text.partition(":")
    if model and model not in {m.value for m in Model}:
        raise argparse.ArgumentTypeError(
            f"{text!r}: the model must be one of {[m.value for m in Model]}"
        )
    return Rung(slot=slot, model=Model(model) if model else None)


# ── prose ──────────────────────────────────────────────────────────────


def ago(at: datetime, now: datetime) -> str:
    seconds = max(0, int((now - at).total_seconds()))
    if seconds < 60:
        return f"{seconds} s ago"
    if seconds < 3600:
        return f"{seconds // 60} m ago"
    return f"{seconds // 3600} h ago"


def doing_sentence(session: Session, now: datetime) -> str | None:
    """What the session is doing, in one line: its last step and its age,
    and its own summary of the work when the registry holds one (plan 17,
    item 3). None for a row with no process."""
    if session.pid is None:
        return None
    parts: list[str] = []
    if session.doing is not None:
        parts.append(f"{session.doing.step}, {ago(session.doing.at, now)}")
    if session.detail:
        parts.append(f'"{session.detail}"')
    return "; ".join(parts) or None


def describe_session(session: Session, now: datetime | None = None) -> str:
    marks = []
    if session.stale:
        marks.append("stale copy")
    if session.wall is not None:
        marks.append(f"wall: {session.wall.reason} → {session.wall.account}")
    if session.scope:
        marks.append(session.scope)
    tail = f"  [{'; '.join(marks)}]" if marks else ""
    doing = doing_sentence(session, now or clock.now())
    tail += f"\n{'':<9} {'':<8}  {doing}" if doing else ""
    where = session.worktree or session.cwd
    return (
        f"{session.slot:<9} {session.short_id}  {session.state.value:<8} "
        f"{session.kind.value:<11} {session.name}  {where}{tail}"
    )


def describe_launch(launch: Launch) -> str:
    if launch.verdict == LaunchVerdict.ALIVE and launch.placement is not None:
        short = launch.session.short_id if launch.session else "?"
        head = (
            f"{short} is alive: {launch.card} on {launch.placement.slot} with "
            f"{launch.placement.model.value}"
        )
        head += f", in {launch.scope}" if launch.scope else ""
        head += f" ({launch.reason})" if launch.reason else ""
    elif launch.verdict == LaunchVerdict.UNCONFIRMED:
        head = f"unconfirmed: {launch.reason}"
    else:
        head = f"not running: {launch.reason}"
    lines = [head]
    for attempt in launch.attempts:
        rung = (
            f"{attempt.rung.slot}/{attempt.rung.model.value if attempt.rung.model else 'default'}"
        )
        line = f"  {rung}: {attempt.verdict.value}"
        line += f" ({attempt.short_id})" if attempt.short_id else ""
        line += f" after {attempt.seconds:.1f} s"
        line += f" — {attempt.reason}" if attempt.reason else ""
        lines.append(line)
    return "\n".join(lines)


# ── the verbs ──────────────────────────────────────────────────────────


def sessions(runtime: Runtime, args: argparse.Namespace) -> int:
    rows = runtime.sessions()
    now = clock.now()
    text = "\n".join(describe_session(s, now) for s in rows) or "no session in any registry"
    unreadable = runtime.handoffs().unreadable
    if unreadable and not args.json:
        text += "\n" + "\n".join(f"unreadable handoff file: {p}" for p in unreadable)
    _emit(args, rows, text)
    return 0


def where(runtime: Runtime, args: argparse.Namespace) -> int:
    answer = runtime.where(args.from_slot, args.tried or [], cached=not args.live)
    if answer.placement is None:
        _emit(args, answer, f"nowhere: {answer.reason}")
        return 1
    placement = answer.placement
    _emit(args, answer, f"{placement.model.value} on {placement.slot} — {placement.why}")
    return 0


def start(runtime: Runtime, args: argparse.Namespace) -> int:
    request = Start(
        repo=str(Path(args.repo).expanduser().resolve()),
        card=args.card,
        brief=args.brief,
        effort=Gate(args.effort),
        from_slot=args.from_slot,
    )
    launch = runtime.start(request)
    _emit(args, launch, describe_launch(launch))
    return 0 if launch.verdict == LaunchVerdict.ALIVE else 1


def move(runtime: Runtime, args: argparse.Namespace) -> int:
    launch = runtime.move(args.short, args.to)
    _emit(args, launch, describe_launch(launch))
    return 0 if launch.verdict == LaunchVerdict.ALIVE else 1


def stop(runtime: Runtime, args: argparse.Namespace) -> int:
    stopped = runtime.stop(args.short)
    state = "gone" if stopped.gone else "STILL RUNNING"
    _emit(
        args,
        stopped,
        f"{stopped.short_id} on {stopped.slot}: {state} after "
        f"{stopped.seconds:.1f} s — {stopped.words}",
    )
    return 0 if stopped.gone else 1


def window(runtime: Runtime, args: argparse.Namespace) -> int:
    kind = WindowKind(args.kind) if args.kind else None
    try:
        opened = runtime.window(args.short, kind)
    except WindowRefused as refusal:
        print(str(refusal), file=sys.stderr)
        return 1
    text = f"opened {opened.window.app_id} ({opened.window.address}) into {args.short}"
    if opened.fresh:
        text += f"\n  a fresh session, its first line: {opened.banner}"
    _emit(args, opened, text)
    return 0


def focus(runtime: Runtime, args: argparse.Namespace) -> int:
    try:
        focused = runtime.focus(args.short)
    except WindowRefused as refusal:
        print(str(refusal), file=sys.stderr)
        return 1
    _emit(
        args,
        focused,
        f"focused {focused.window.app_id} ({focused.window.address}); the compositor "
        f"reports {focused.app_id} active",
    )
    return 0


def rescues(runtime: Runtime, args: argparse.Namespace) -> int:
    if args.clear:
        count = runtime.clear_rescues(args.short)
        print(
            f"cleared {count} rescue row{'s' if count != 1 else ''} for {args.short}; "
            "its slot record is untouched"
        )
        return 0

    def rung(r: Rung | None) -> str:
        return "—" if r is None else f"{r.slot}/{r.model.value if r.model else 'default'}"

    rows = runtime.rescues(args.short)
    lines = [
        f"{r.at.isoformat()}  {rung(r.from_rung)} → {rung(r.to_rung)}  {r.reason}" for r in rows
    ]
    _emit(args, rows, "\n".join(lines) or f"no rescues recorded for {args.short}")
    return 0


def call_brief(note: str, answer: str, objective: str | None) -> str:
    """What a called colleague is told: the thread, the question, where the
    answer goes. The note is the record; the brief only points at it."""
    asked = f" {objective.strip()}" if objective and objective.strip() else ""
    return (
        f"A colleague calls you with a question. Read {note} first — it holds the thread "
        f"and the question.{asked} Answer in the record: write your reply to {answer} "
        "(create it, or append under a head of your own if it exists), and end your turn "
        "once it is written. The caller waits on that file, not on your words here."
    )


def answer_path(note: str, short_id: str) -> str:
    """Where a reply lands when the caller names nowhere: beside the note,
    named as a reply from the colleague, so two replies never collide on
    one filename (two did at 09:15 on 2026-09-05)."""
    given = Path(note)
    topic = _FROM.sub("", given.stem) or given.stem
    return str(given.parent / f"from-{short_id}-re-{topic}.md")


def call(runtime: Runtime, args: argparse.Namespace) -> int:
    note = str(Path(args.note).expanduser().resolve())
    if not Path(note).is_file():
        print(f"{note} is not a file; a call names the note that holds the thread", file=sys.stderr)
        return 1
    who = runtime.colleague(args.who)
    if who is None:
        print(
            f"no session {args.who!r} is in any registry on this machine, no slot is named so, "
            "and no transcript by that id exists",
            file=sys.stderr,
        )
        return 1
    if isinstance(who, tuple):
        session_id, name = who[0], f"call-{who[0].split('-')[0]}"
        short = session_id.split("-")[0]
    else:
        session_id, name, short = who.session_id, who.name, who.short_id
    answer = (
        str(Path(args.answer).expanduser().resolve()) if args.answer else answer_path(note, short)
    )
    brief = call_brief(note, answer, args.objective)
    launch = runtime.call(who, brief=brief, name=name)
    if launch.verdict != LaunchVerdict.ALIVE or launch.session is None:
        _emit(args, launch, describe_launch(launch))
        return 1
    record = runtime.store.record_call(
        session_id=launch.session.session_id,
        slot=launch.session.slot,
        name=launch.session.name,
        note=note,
        answer=answer,
        brief=brief,
        caller=os.getcwd(),
        at=clock.now(),
    )
    placement = launch.placement
    where = f"{placement.model.value} on {placement.slot}" if placement else launch.session.slot
    forked = f" (resumed from {short})" if launch.session.session_id != session_id else ""
    text = (
        f"call {record.id}: {launch.session.short_id}{forked} is working on {note}, {where}\n"
        f"  the answer lands in {answer}\n"
        f"  wait for it: needle wait {record.id}"
    )
    _emit(args, record, text)
    return 0


def _wait_text(verdict: CallVerdict) -> str:
    return f"{verdict.outcome.value}: {verdict.words}"


def wait(runtime: Runtime, args: argparse.Namespace) -> int:
    """Wait on one call until its answer lands or changes, the colleague is
    blocked, moved or ends without it, or the ceiling passes — and say
    which, in the runtime's words (plan 17, item 2). Never polls a
    terminal; looks at the file every quarter second and at the one list
    every two."""
    record = runtime.store.call(args.call)
    if record is None:
        print(f"no call {args.call} is recorded; needle call makes one", file=sys.stderr)
        return 1
    started = time.monotonic()
    next_list = started
    while True:
        landed = calls.answer_landed(record)
        if landed is not None:
            verdict = calls.judge(record, [], why_ended=None, moved_words=None)
            assert verdict is not None and verdict.outcome == CallOutcome.LANDED
            _emit(args, verdict, _wait_text(verdict))
            return 0
        now = time.monotonic()
        if now >= next_list:
            next_list = now + WAIT_LIST_SECONDS
            fresh = runtime.store.call(record.id)
            record = fresh if fresh is not None else record
            if record.ended_at is not None and record.words:
                verdict = CallVerdict(
                    outcome=CallOutcome.ENDED,
                    words=record.words,
                    session_id=record.session_id,
                    slot=record.slot,
                )
                _emit(args, verdict, _wait_text(verdict))
                return 1
            verdict = runtime.judge_call(record)
            if verdict is not None and verdict.outcome == CallOutcome.MOVED:
                runtime.store.move_call(record.id, verdict.session_id, verdict.slot, verdict.words)
            if verdict is not None:
                text = _wait_text(verdict)
                if verdict.outcome == CallOutcome.MOVED:
                    text += f"; wait again: needle wait {record.id}"
                _emit(args, verdict, text)
                return 1
        if now - started >= args.ceiling:
            session = next(
                (s for s in runtime.sessions() if s.session_id == record.session_id), None
            )
            doing = doing_sentence(session, clock.now()) if session is not None else None
            verdict = CallVerdict(
                outcome=CallOutcome.NOTHING,
                words=f"nothing in {args.ceiling:.0f} s; {record.name} is still at work"
                + (f" ({doing})" if doing else ""),
                session_id=record.session_id,
                slot=record.slot,
            )
            _emit(args, verdict, _wait_text(verdict))
            return 1
        time.sleep(WAIT_FILE_SECONDS)


def register(sub: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    def parser(name: str, help_text: str, verb: Verb) -> argparse.ArgumentParser:
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--json", action="store_true", help="answer as JSON")
        p.set_defaults(run=_with_runtime(verb))
        return p

    parser("sessions", "every session on this machine, across every slot, as one list", sessions)

    p_where = parser("where", "where work runs next, as claude-acct's one rule answers it", where)
    p_where.add_argument("--from", dest="from_slot", help="the slot to ask first")
    p_where.add_argument(
        "--tried",
        type=lambda text: [parse_rung(t) for t in text.split(",") if t],
        help="rungs already spent: slot or slot:model, comma-separated",
    )
    p_where.add_argument(
        "--live", action="store_true", help="probe the limits instead of reading the cache"
    )

    p_start = parser("start", "start a session for a card in its own worktree and scope", start)
    p_start.add_argument("repo")
    p_start.add_argument("card", help="the lane's name: worktree, scope and window carry it")
    p_start.add_argument("brief")
    p_start.add_argument("--effort", choices=[g.value for g in Gate], default=Gate.XHIGH.value)
    p_start.add_argument("--from", dest="from_slot", help="the slot to ask first")

    p_move = parser(
        "move",
        "move a session to another slot: stop where it runs, resume where the rule names",
        move,
    )
    p_move.add_argument("short")
    p_move.add_argument(
        "--to", help="the slot to move to; without it the handoff file or the rule decides"
    )

    p_stop = parser("stop", "end a session through its own slot and prove it gone", stop)
    p_stop.add_argument("short")

    p_window = parser("window", "open a window into a session, proved by the compositor", window)
    p_window.add_argument("short")
    p_window.add_argument(
        "--as",
        dest="kind",
        choices=[k.value for k in WindowKind],
        help="the window's kind; lane for a live session, board-look for one live nowhere",
    )

    p_focus = parser(
        "focus", "bring a session's open window forward, proved by the compositor", focus
    )
    p_focus.add_argument("short")

    p_rescues = parser("rescues", "a session's rescue history in the runtime's ledger", rescues)
    p_rescues.add_argument("short")
    p_rescues.add_argument(
        "--clear", action="store_true", help="forget the history; the slot record stays"
    )

    p_call = parser(
        "call",
        "call a running colleague warm with a note: resume its session through its lifecycle "
        "owner, the note as the brief, the answer in the record",
        call,
    )
    p_call.add_argument(
        "who", help="a session's short id or id, a slot's most recent, or a transcript's id"
    )
    p_call.add_argument("note", help="the file that holds the thread and the question")
    p_call.add_argument("--objective", help="one sentence on what the answer is for")
    p_call.add_argument("--answer", help="where the reply lands; beside the note if omitted")

    p_wait = parser(
        "wait",
        "wait on a call until the answer lands, or the colleague is blocked, moved or ends "
        "without it, or the ceiling passes; says which",
        wait,
    )
    p_wait.add_argument("call", type=int, help="the call's number, as needle call printed it")
    p_wait.add_argument(
        "--ceiling", type=float, default=WAIT_CEILING_SECONDS, help="seconds to wait at most"
    )
