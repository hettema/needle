"""`needle`'s runtime verbs: the four jobs of the runtime from the command line.

needle sessions [--json]
needle where [--from SLOT] [--tried RUNG,...] [--live] [--json]
needle start REPO CARD "BRIEF" [--effort LEVEL] [--from SLOT] [--json]
needle move SHORT [--to SLOT] [--json]
needle stop SHORT [--json]
needle window SHORT [--as KIND] [--json]
needle rescues SHORT [--clear] [--json]

Each verb is a thin call into `runtime.service.Runtime`, answers in prose or
as the domain value's JSON, and exits 1 when the thing asked for did not
happen. The owner's terminal, the board and a script all read the same
answer.
"""

import argparse
import json
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from pydantic import BaseModel

from domain.gate import Gate
from domain.launch import Launch, LaunchVerdict, Start
from domain.session import Session
from domain.slot import Model, Rung
from domain.window import WindowKind
from infrastructure.paths import db_path
from infrastructure.store import Store
from runtime.service import NoSuchSession, Runtime
from runtime.windows import WindowRefused

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


def describe_session(session: Session) -> str:
    marks = []
    if session.stale:
        marks.append("stale copy")
    if session.wall is not None:
        marks.append(f"wall: {session.wall.reason} → {session.wall.account}")
    if session.scope:
        marks.append(session.scope)
    tail = f"  [{'; '.join(marks)}]" if marks else ""
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
    text = "\n".join(describe_session(s) for s in rows) or "no session in any registry"
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

    p_rescues = parser("rescues", "a session's rescue history in the runtime's ledger", rescues)
    p_rescues.add_argument("short")
    p_rescues.add_argument(
        "--clear", action="store_true", help="forget the history; the slot record stays"
    )
