"""`needle`'s runtime verbs: the four jobs of the runtime from the command line.

needle sessions [--json]
needle where [--from SLOT] [--tried RUNG,...] [--live] [--json]
needle start REPO CARD "BRIEF" [--effort LEVEL] [--from SLOT] [--json]
needle move SHORT [--to SLOT] [--json]
needle stop SHORT [--json]
needle window SHORT [--as KIND] [--json]
needle focus SHORT [--json]
needle show SLUG CARD [--json]
needle rescues SHORT [--clear] [--json]
needle call WHO NOTE [--objective TEXT] [--answer PATH] [--fresh [--effort LEVEL]] [--json]
needle wait CALL [--ceiling SECONDS] [--json]
needle machine add NAME [--host H] [--desktop] [--ground PATH] [--command LINE]
needle machine rm NAME
needle machine timing NAME WHAT SECONDS
needle machine host NAME HOST
needle machines [--json]
needle room [--hold] [--json]
needle board [NAME|here]
needle push --worktree PATH [--main] [--json]
needle level REPO [--json]

Since card #83 the board's runtime asks another machine's runtime for what
that machine holds, through these same verbs with `--json`: `sessions`,
`where`, `start`, `stop`, `move`, `resume`, `rescope`, `room`, `scopes`,
`cause`, `ended`, `boots`, `limits`, `expire-handoff`, `show`, `tell`,
`push` and `level`. Each answers the domain value the façade answers, so
the wire is the same typed edge the terminal reads. The other way round,
`needle board NAME` on a machine makes every verb that opens the board's
store run on NAME over the same wire (item 3), so a lane there writes the
one board and never a copy.

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

from board.dial import who_is_home
from domain.board import Beat
from domain.call import Answer, CallOutcome, CallVerdict
from domain.dial import ScopePids, ScopeState, ScopeStop
from domain.ending import Ended, Sighting
from domain.gate import Gate
from domain.lane import Checkouts, Edited
from domain.launch import Launch, LaunchVerdict, Start, WindowlessStart
from domain.machine import Ask, BoardMachine, Machine, MachineRoom, Timing
from domain.notice import Notice, Said
from domain.session import Session, TranscriptSize
from domain.slot import Expired, LimitsRead, Rung, rung_words
from domain.window import WindowKind
from infrastructure import clock
from infrastructure.paths import data_dir, db_path
from infrastructure.store import Store, StoreRefusal
from runtime import calls, codex, git, machine
from runtime.notice import NoBoardEntry
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
    """`slot` or `slot:model`, as the rule's own `--tried` argument spells a
    rung. The model is not checked against a list here: the ladder is the
    machine's data and not this command's knowledge (card #63), so a name
    this runtime has never seen is passed on to the rule, which is the one
    thing that knows the ladder."""
    slot, _, model = text.partition(":")
    if not slot:
        raise argparse.ArgumentTypeError(f"{text!r}: a rung names a slot, optionally `slot:model`")
    return Rung(slot=slot, model=model or None)


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
    if session.machine:
        marks.append(f"on {session.machine}")
    tail = f"  [{'; '.join(marks)}]" if marks else ""
    doing = doing_sentence(session, now or clock.now())
    tail += f"\n{'':<9} {'':<8}  {doing}" if doing else ""
    where = session.worktree or session.cwd
    return (
        f"{session.slot:<9} {session.short_id}  {session.state.value:<8} "
        f"{session.kind.value:<11} {session.name}  {where}{tail}"
    )


def describe_launch(launch: Launch) -> str:
    if launch.verdict == LaunchVerdict.ALIVE:
        short = launch.session.short_id if launch.session else "?"
        # A Codex worker is alive on no placement: the rule placed nothing,
        # it runs where its rollout says (plan 57).
        where = (
            f"on {rung_words(launch.placement.model, launch.placement.slot)}"
            if launch.placement is not None
            else f"on {launch.session.slot}"
            if launch.session is not None
            else "nowhere the rule placed"
        )
        head = f"{short} is alive: {launch.card} {where}"
        head += f", in {launch.scope}" if launch.scope else ""
        head += f" ({launch.reason})" if launch.reason else ""
    elif launch.verdict == LaunchVerdict.UNCONFIRMED:
        head = f"unconfirmed: {launch.reason}"
    else:
        head = f"not running: {launch.reason}"
    lines = [head]
    for attempt in launch.attempts:
        rung = f"{attempt.rung.slot}/{attempt.rung.model or 'default'}"
        line = f"  {rung}: {attempt.verdict.value}"
        line += f" ({attempt.short_id})" if attempt.short_id else ""
        line += f" after {attempt.seconds:.1f} s"
        line += f" — {attempt.reason}" if attempt.reason else ""
        lines.append(line)
    return "\n".join(lines)


# ── the verbs ──────────────────────────────────────────────────────────


def sessions(runtime: Runtime, args: argparse.Namespace) -> int:
    rows = runtime.sessions()
    if args.lean:
        # The brief a session opened with is what the machine that resumes
        # it reads, never the board over the wire: 474 rows carried 3.6 MB
        # of it on the first live move (2026-09-10).
        rows = [r.model_copy(update={"intent": ""}) for r in rows]
    now = clock.now()
    text = "\n".join(describe_session(s, now) for s in rows) or "no session in any registry"
    unreadable = runtime.handoffs().unreadable
    if unreadable and not args.json:
        text += "\n" + "\n".join(f"unreadable handoff file: {p}" for p in unreadable)
    _emit(args, rows, text)
    return 0


def describe_scope(state: ScopeState) -> str:
    who = ", ".join(state.home) if state.home else "nobody home"
    count = len(state.pids)
    held = f"{count} process{'es' if count != 1 else ''}"
    heads = ", ".join(sorted(set(state.strangers))[:3])
    return f"{state.unit}  {who}  {held}" + (f" ({heads})" if heads else "")


def scopes(runtime: Runtime, args: argparse.Namespace) -> int:
    """Every process group of ours and who is home in it (card #99): the
    reading behind the beat's sweep, and the loop's own reader. `--held`,
    `--pids` and `--stop` are the wire's forms (card #83): what another
    board asks this machine for, answered raw."""
    if args.stop_unit:
        taken, words = runtime.stop_scope(args.stop_unit)
        _emit(args, ScopeStop(unit=args.stop_unit, taken=taken, words=words), words or "asked")
        return 0 if taken else 1
    if args.pids_unit:
        pids = runtime.scope_pids(args.pids_unit)
        if pids is None:
            print("the user manager could not be asked", file=sys.stderr)
            return 1
        _emit(args, ScopePids(unit=args.pids_unit, pids=pids), " ".join(map(str, pids)))
        return 0
    held = runtime.scopes()
    if held is None:
        print("the user manager could not be asked", file=sys.stderr)
        return 1
    if args.held:
        _emit(args, held, "\n".join(f"{h.unit}  {len(h.pids)} pids" for h in held) or "none")
        return 0
    states = who_is_home(held, runtime.sessions())
    if args.stray:
        states = [s for s in states if s.nobody_home]
    if args.count:
        print(len(states))
        return 0
    empty = "no group nobody is home in" if args.stray else "no group of ours"
    _emit(args, states, "\n".join(describe_scope(s) for s in states) or empty)
    return 0


def _gb(byte_count: int) -> str:
    return f"{byte_count / 1024**3:.1f} GB"


def high_water_line(reading: MachineRoom) -> str:
    """The plan's loop line for one machine: the most memory the board saw
    used on it over the window, and the day."""
    mark = reading.high_water
    if mark is None:
        return f"{reading.machine.name}: no memory reading yet"
    return (
        f"{reading.machine.name}: high-water {_gb(mark.used)} used of {_gb(mark.total)} "
        f"on {mark.day.isoformat()} ({_gb(mark.least_available)} was the least available)"
    )


def where(runtime: Runtime, args: argparse.Namespace) -> int:
    if args.high_water:
        rooms = runtime.rooms()
        reading = next((r for r in rooms if r.machine.name == args.high_water), None)
        if reading is None:
            print(f"no machine named {args.high_water!r} is on the board", file=sys.stderr)
            return 1
        _emit(args, reading, high_water_line(reading))
        return 0
    repo = str(Path(args.repo).expanduser().resolve()) if args.repo else None
    answer = runtime.where(args.from_slot, args.tried or [], cached=not args.live, repo=repo)
    if answer.placement is None:
        _emit(args, answer, f"nowhere: {answer.reason}")
        return 1
    placement = answer.placement
    on = f" on {placement.machine}" if placement.machine and repo else ""
    _emit(args, answer, f"{rung_words(placement.model, placement.slot)}{on} — {placement.why}")
    return 0


def start(runtime: Runtime, args: argparse.Namespace) -> int:
    repo = str(Path(args.repo).expanduser().resolve())
    if args.windowless:
        launch = runtime.start_windowless(
            WindowlessStart(repo=repo, card=args.card, brief=args.brief, effort=Gate(args.effort))
        )
    else:
        launch = runtime.start(
            Start(
                repo=repo,
                card=args.card,
                brief=args.brief,
                effort=Gate(args.effort),
                from_slot=args.from_slot,
            )
        )
    _emit(args, launch, describe_launch(launch))
    return 0 if launch.verdict == LaunchVerdict.ALIVE else 1


def move(runtime: Runtime, args: argparse.Namespace) -> int:
    launch = runtime.move(args.short, args.to)
    _emit(args, launch, describe_launch(launch))
    return 0 if launch.verdict == LaunchVerdict.ALIVE else 1


def resume(runtime: Runtime, args: argparse.Namespace) -> int:
    """Resume a session where the rule says, with the words given (card
    #83): the wire's form of what the board's doors and loops do."""
    placement = None
    if args.to:
        asked = runtime.where(args.to, [], cached=False)
        if asked.placement is None or asked.placement.slot != args.to:
            print(f"the rule would not place it on {args.to}: {asked.reason}", file=sys.stderr)
            return 1
        placement = asked.placement
    launch = runtime.resume(
        args.short, prompt=args.prompt, card=args.card, placement=placement, reason=args.reason
    )
    _emit(args, launch, describe_launch(launch))
    return 0 if launch.verdict == LaunchVerdict.ALIVE else 1


def rescope(runtime: Runtime, args: argparse.Namespace) -> int:
    """Put a session back in its lane's scope (plan 53, item 2), on this
    machine: the wire's form."""
    done = runtime.rescope(runtime.session(args.short), args.card)
    _emit(args, done, f"{done.unit}: {'verified' if done.verified else done.words}")
    return 0 if done.verified else 1


def stop(runtime: Runtime, args: argparse.Namespace) -> int:
    stopped = runtime.stop(args.short, keep_handoff=args.keep_handoff)
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


def show(runtime: Runtime, args: argparse.Namespace) -> int:
    """What the notification's button runs (card #41): the card in front of
    him, on that project's board."""
    try:
        said = runtime.show(args.slug, args.number)
    except (NoBoardEntry, WindowRefused) as refused:
        print(f"Could not show #{args.number} on {args.slug}: {refused}", file=sys.stderr)
        return 1
    _emit(args, Said(said=said), said)
    return 0


def tell(runtime: Runtime, args: argparse.Namespace) -> int:
    """Raise a notice on this machine's screen (card #41), as the board on
    another machine asks the desktop to (card #83): the ledger of how it
    was answered is kept beside this machine's own store."""
    notice = Notice.model_validate_json(args.notice)
    told = runtime.tell(notice, args.opens or [], data_dir() / "told.log")
    _emit(args, told, told.words)
    return 0 if told.raised else 1


# ── the wire's readers (card #83) ──────────────────────────────────────


def cause(runtime: Runtime, args: argparse.Namespace) -> int:
    """What took a session's process, from this machine's own evidence: the
    reader the board on another machine asks for a session that ran here."""
    session = runtime.session(args.short)
    sighting = Sighting.model_validate_json(args.sighting) if args.sighting else None
    named = runtime.cause_of(
        session,
        units=args.units or [],
        sighting=sighting,
        boots_seen=runtime.boots(),
        now=clock.now(),
    )
    _emit(args, named, f"{named.cause.value}: {named.words}")
    return 0


def ended(runtime: Runtime, args: argparse.Namespace) -> int:
    session = runtime.session(args.short)
    why = runtime.why_ended(session)
    _emit(args, Ended(why=why), why or "nothing on this machine says")
    return 0


def boots(runtime: Runtime, args: argparse.Namespace) -> int:
    listed = runtime.boots()
    _emit(
        args,
        listed,
        "\n".join(f"{b.index:>3} {b.boot_id} {b.first_entry:%Y-%m-%d %H:%M}" for b in listed)
        or "no boot listed",
    )
    return 0


def limits_read(runtime: Runtime, args: argparse.Namespace) -> int:
    reading = runtime.limits(args.slot)
    text = (
        "no reading"
        if reading is None
        else ", ".join(f"{label} {share:.0%}" for label, share in reading.spent.items())
    )
    _emit(args, LimitsRead(limits=reading), text)
    return 0


def expire_handoff(runtime: Runtime, args: argparse.Namespace) -> int:
    found = runtime.handoffs().by_session.get(args.session_id)
    if found is not None:
        runtime.expire_handoff(found)
    _emit(
        args,
        Expired(session_id=args.session_id, removed=found is not None),
        "removed" if found is not None else "no handoff named it",
    )
    return 0


def room(runtime: Runtime, args: argparse.Namespace) -> int:
    """This machine against the floor, by the one rule the head uses."""
    owners: dict[str, tuple[str, int]] = {}
    for spec in args.owners or []:
        unit, _, card = spec.partition("=")
        slug, _, number = card.rpartition(":")
        if unit and slug and number.isdigit():
            owners[unit] = (slug, int(number))
    reading = runtime.room(hold=args.hold, owners=owners or None)
    text = reading.sentence or (
        f"room: {_gb(reading.available)} available, {_gb(reading.swap_free)} swap free, "
        f"floor {_gb(reading.floor)}"
    )
    if reading.marked:
        text += f"; held at the floor: {', '.join(reading.marked)}"
    _emit(args, reading, text)
    return 0


def worktrees(runtime: Runtime, args: argparse.Namespace) -> int:
    """Every checkout of a repository on this machine: the wire's read of
    where a lane's worktree is (card #83)."""
    found = runtime.worktrees(str(Path(args.repo).expanduser().resolve()))
    _emit(
        args,
        Checkouts(checkouts=found),
        "\n".join(f"{path}  {branch or '(detached)'}" for path, branch in found.items())
        or "no checkout",
    )
    return 0


def tip(runtime: Runtime, args: argparse.Namespace) -> int:
    found = runtime.lane_tip(
        str(Path(args.repo).expanduser().resolve()), args.branch, path=args.repo
    )
    _emit(args, found, f"{found.tip or 'no tip'} born at {found.birth or 'unknown'}")
    return 0


def push(runtime: Runtime, args: argparse.Namespace) -> int:
    """The git half of a fold, run on the machine that holds the lane: the
    board asks it over the wire when the lane is not on its own machine
    (card #83, item 3). Exit 1 with the value when nothing was pushed."""
    worktree = str(Path(args.worktree).expanduser().resolve())
    folded = runtime.fold(worktree, promote_main=args.main)
    _emit(args, folded, folded.words)
    return 0 if folded.pushed else 1


def level(runtime: Runtime, args: argparse.Namespace) -> int:
    """This machine's clone of a project brought level with the trunk: what
    the board asks of every machine at each pass (card #83, item 3)."""
    repo = str(Path(args.repo).expanduser().resolve())
    if not runtime.is_repository(repo):
        levelled = git.Levelled(
            level=None,
            behind=0,
            note=f"{repo} is not a git repository on this machine",
            fetched=False,
            main_updated=False,
        )
    else:
        levelled = runtime.level(repo)
    said = "level with origin/develop" if levelled.level else levelled.note or "not level"
    _emit(args, levelled, said)
    return 0 if levelled.level else 1


def board(runtime: Runtime, args: argparse.Namespace) -> int:
    """Which machine the board serves from (card #83, item 3). With a name:
    that machine's row becomes this machine's answer for every board verb,
    and `needle serve` here refuses. `here` forgets it. The row is read from
    this machine's own store, which is the board's until the move and its
    ledger after, so the name is one the board knew when it was here."""
    if args.name is None:
        current = machine.board_elsewhere()
        if current is None:
            print("the board serves from this machine: every verb opens the store here")
        else:
            print(
                f"the board serves from {current.name} ({current.host}): every board verb "
                f"runs there over ssh, as `{current.command}`"
            )
        return 0
    if args.name == "here":
        machine.set_board(None)
        print("the board serves from this machine: every verb opens the store here")
        return 0
    # The rows in the store here, not the runtime's list: on a machine that
    # already hands its verbs away the runtime answers for itself alone,
    # and the file is rewritten from what this store recorded of the board
    # before the move — the last board this machine was.
    row = next((m for m in runtime.store.machines() if m.name == args.name), None)
    if row is None:
        print(f"no machine named {args.name!r} is on the board", file=sys.stderr)
        return 1
    if runtime.is_here(row):
        print(f"{args.name} is this machine; `needle board here` says so", file=sys.stderr)
        return 1
    if not row.host:
        print(f"{args.name} has no host this machine reaches it by", file=sys.stderr)
        return 1
    machine.set_board(BoardMachine(name=row.name, host=row.host, command=row.command))
    print(
        f"the board serves from {row.name} ({row.host}): every board verb runs there over "
        "ssh, and `needle serve` here refuses until `needle board here`"
    )
    return 0


def machine_host(runtime: Runtime, args: argparse.Namespace) -> int:
    """How the board reaches a machine, rewritten after the board moved:
    the host is proved to be that machine by its own machine id before the
    row changes, as `machine add` proves it (card #83, item 3)."""
    # A registered row only: the runtime names this machine from its
    # hostname when no row is it, and that name has nothing to rewrite
    # (Codex's eighth pass on card #83).
    row = next((m for m in runtime.store.machines() if m.name == args.name), None)
    if row is None:
        print(f"no machine named {args.name!r} is on the board", file=sys.stderr)
        return 1
    try:
        done = machine.run(["cat", str(machine.MACHINE_ID_FILE)], host=args.host, timeout=20)
    except (machine.Unreachable, machine.CommandMissing, machine.Timeout, OSError) as error:
        print(f"could not reach {args.host}: {error}", file=sys.stderr)
        return 1
    identity = done.stdout.strip()
    if identity != row.machine_id:
        print(
            f"{args.host} is not {args.name}: its machine id is {identity or 'unreadable'}, "
            f"and {args.name}'s is {row.machine_id}",
            file=sys.stderr,
        )
        return 1
    if not runtime.store.set_machine_host(args.name, args.host):
        print(f"no machine named {args.name!r} is on the board", file=sys.stderr)
        return 1
    print(f"{args.name}: reached as {args.host}")
    return 0


def edits(runtime: Runtime, args: argparse.Namespace) -> int:
    checkout = str(Path(args.checkout).expanduser().resolve())
    if args.lane:
        files = runtime.lane_files(checkout, birth=args.birth, tip=args.tip)
    else:
        files = runtime.edits(checkout)
    _emit(args, Edited(files=sorted(files)), "\n".join(sorted(files)) or "nothing changed")
    return 0


def lane_docs(runtime: Runtime, args: argparse.Namespace) -> int:
    docs = runtime.lane_docs(
        str(Path(args.checkout).expanduser().resolve()), args.plans or [], reviews=args.reviews
    )
    _emit(
        args,
        docs,
        f"plan: {'found' if docs.plan is not None else 'none'}; {len(docs.reviews)} review records",
    )
    return 0


def dispatches(runtime: Runtime, args: argparse.Namespace) -> int:
    found = runtime.dispatches(str(Path(args.cwd).expanduser().resolve()))
    if found is None:
        print("null" if args.json else "no transcript ran there")
        return 0
    _emit(args, found, "\n".join(f"{d.role}  {d.session_id[:8]}" for d in found) or "none")
    return 0


def transcript_size(runtime: Runtime, args: argparse.Namespace) -> int:
    size = runtime.transcript_size(runtime.session(args.short))
    _emit(args, TranscriptSize(size=size), str(size) if size is not None else "no transcript")
    return 0


# ── the one question a pass, and the beat's measure (card #123) ────────


def observe(runtime: Runtime, args: argparse.Namespace) -> int:
    """Everything a board asks this machine on one pass, answered once:
    the wire's form of every read the pass made one verb at a time before
    card #123. The ask is the board's `Ask` as JSON; none is the empty ask
    (this machine's sessions, boots, room, groups and rule alone)."""
    text = sys.stdin.read() if args.ask == "-" else args.ask
    try:
        ask = Ask.model_validate_json(text) if text else Ask()
    except ValueError as wrong:
        print(f"--ask is not an Ask: {wrong}", file=sys.stderr)
        return 2
    observation = runtime.observe_here(ask)
    _emit(
        args,
        observation,
        f"{len(observation.sessions)} sessions, {len(observation.boots)} boots, "
        f"{len(observation.lanes)} lanes read in {observation.seconds:.1f} s",
    )
    return 0


def beat_line(beat: Beat) -> str:
    """One pass's four times in one line, ending in the word the plan's loop
    reads — `answered` when the pass's first click was answered within a
    second, wait and effect together."""
    collected = ", ".join(f"{name} {seconds:.1f} s" for name, seconds in beat.collection.items())
    line = (
        f"{beat.at:%Y-%m-%d %H:%M:%S}Z  collection: {collected or 'nothing'} · "
        f"lock held {beat.lock_seconds:.2f} s"
    )
    if beat.door is None:
        return line + " · no click during the pass"
    wait = beat.door_wait or 0.0
    took = beat.door_seconds or 0.0
    if beat.answered:
        return line + f" · click: {beat.door} answered in {wait + took:.2f} s"
    return line + f" · click: {beat.door} waited {wait:.2f} s and took {took:.2f} s"


def beats(runtime: Runtime, args: argparse.Namespace) -> int:
    """The last passes as the board timed them (card #123, item 4); `--last`
    prints the newest alone, which the plan's loop reads for `answered`."""
    listed = runtime.store.beats(limit=1 if args.last else args.count)
    if not listed:
        print("no pass has been timed yet" if not args.json else "[]")
        return 1
    text = "\n".join(beat_line(b) for b in listed)
    if args.last and listed[0].door is None:
        # Most passes have no click; the loop reads the last one that did.
        clicked = runtime.store.last_clicked_beat()
        text += (
            "\nlast click: "
            + beat_line(clicked).split(" · click: ", 1)[-1]
            + f" at {clicked.at:%Y-%m-%d %H:%M:%S}Z"
            if clicked is not None
            else "\nno click in the last day"
        )
    _emit(args, listed, text)
    return 0


# ── machines (card #83) ────────────────────────────────────────────────


def describe_room(reading: MachineRoom) -> str:
    where = " (here)" if reading.here else ""
    what = "desktop" if reading.machine.desktop else "horsepower"
    if reading.room is None:
        state = f"did not answer: {reading.why}"
    elif reading.room.full:
        state = reading.room.sentence or "full"
    else:
        state = f"{_gb(reading.room.available)} available"
    if reading.room is not None and reading.why and reading.observed_at is not None:
        # A reading that stands from an earlier pass (card #123).
        age = int((clock.now() - reading.observed_at).total_seconds())
        state = f"as last read {age} s ago ({reading.why}): {state}"
    mark = reading.high_water
    marks = f", high-water {_gb(mark.used)} used" if mark is not None else ""
    clones = f"; clone not level — {', '.join(reading.clones)}" if reading.clones else ""
    behind = "; its needle is behind, read one verb at a time" if reading.behind else ""
    return (
        f"{reading.machine.name}{where}  {what}  {state}{marks}, "
        f"{reading.killed} killed today{clones}{behind}"
    )


def machines(runtime: Runtime, args: argparse.Namespace) -> int:
    rooms = runtime.rooms()
    _emit(args, rooms, "\n".join(describe_room(r) for r in rooms))
    return 0


def machine_add(runtime: Runtime, args: argparse.Namespace) -> int:
    """Register a machine. Its identity is read from the machine itself —
    here when no host is named, over `ssh` when one is — so a row is never
    written for a machine the board cannot reach at the door."""
    try:
        if args.host:
            done = machine.run(["cat", str(machine.MACHINE_ID_FILE)], host=args.host, timeout=20)
            if done.returncode != 0 or not done.stdout.strip():
                print(
                    f"{args.host} did not give its machine id: "
                    f"{(done.stderr or done.stdout).strip()[:200]}",
                    file=sys.stderr,
                )
                return 1
            identity = done.stdout.strip()
        else:
            identity = machine.machine_id()
    except (machine.Unreachable, machine.CommandMissing, machine.Timeout, OSError) as error:
        print(f"could not reach {args.host}: {error}", file=sys.stderr)
        return 1
    if not identity:
        print("this machine has no readable machine id", file=sys.stderr)
        return 1
    ground = str(Path(args.ground).expanduser().resolve()) if args.ground else None
    row = Machine(
        name=args.name,
        machine_id=identity,
        host=args.host,
        desktop=args.desktop,
        ground=ground,
        command=args.needle_command or machine.needle_command(),
        added_at=clock.now(),
    )
    try:
        runtime.store.add_machine(row)
    except StoreRefusal as refused:
        print(str(refused), file=sys.stderr)
        return 1
    _emit(
        args,
        row,
        f"Registered {row.name} ({identity[:8]}…)"
        + (f", reached as {row.host}" if row.host else ", this machine")
        + (", the desktop" if row.desktop else "")
        + (f", the ground of {ground}" if ground else ""),
    )
    return 0


def machine_rm(runtime: Runtime, args: argparse.Namespace) -> int:
    """Forget a machine — only when the one list shows nothing live on it
    (a lane, a reading, a conversation: any row with a process) and it
    answered the read, since an unread machine may hold anything; the
    store's own guards (a lane still there, a session started today) hold
    beneath this (Codex's fourth and fifth passes)."""
    live = [s for s in runtime.sessions() if s.machine == args.name and s.pid is not None]
    if args.name in runtime.unread:
        print(
            f"{args.name} did not answer ({runtime.unread[args.name]}); a machine whose sessions "
            "cannot be read is not forgotten",
            file=sys.stderr,
        )
        return 1
    if live:
        names = ", ".join(f"{s.short_id} ({s.name})" for s in live[:3])
        print(f"{args.name} still runs {len(live)} session(s): {names}", file=sys.stderr)
        return 1
    try:
        forgotten = runtime.store.remove_machine(args.name)
    except StoreRefusal as refused:
        print(str(refused), file=sys.stderr)
        return 1
    if forgotten:
        print(f"Forgot {args.name}; its readings stay under its name.")
        return 0
    print(f"no machine named {args.name!r} is on the board", file=sys.stderr)
    return 1


def machine_timing(runtime: Runtime, args: argparse.Namespace) -> int:
    """Write one measured build time for a machine (the plan's item 5)."""
    if not any(m.name == args.name for m in runtime.machines()):
        print(f"no machine named {args.name!r} is on the board", file=sys.stderr)
        return 1
    timing = Timing(machine=args.name, what=args.what, seconds=args.seconds, at=clock.now())
    runtime.store.record_timing(timing)
    print(f"{args.name}: {args.what} {args.seconds:.1f} s, recorded")
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
        return "—" if r is None else f"{r.slot}/{r.model or 'default'}"

    rows = runtime.rescues(args.short)
    lines = [
        f"{r.at.isoformat()}  {rung(r.from_rung)} → {rung(r.to_rung)}  {r.reason}" for r in rows
    ]
    _emit(args, rows, "\n".join(lines) or f"no rescues recorded for {args.short}")
    return 0


def call_brief(note: str, answer: str, objective: str | None, *, by_message: bool = False) -> str:
    """What a called colleague is told: the thread, the question, where the
    answer goes, and the shape to answer in — `domain.call.Answer`, the
    same for both makes so `runtime.calls.read_answer` is the one reader
    (card #73). The note is the record; the brief only points at it. A
    Codex worker answers by its last message, which Codex writes to the
    file itself (`by_message`, plan 57) and holds to the shape's schema:
    its own shell runs in a sandbox that refused the shared record on
    2026-09-05, so it is told not to try. A Claude colleague writes the
    file and is asked for the shape in words; prose still lands, read by
    its first line."""
    asked = f" {objective.strip()}" if objective and objective.strip() else ""
    if by_message:
        return (
            f"A colleague calls you with a question. Read {note} first — it holds the thread "
            f"and the question.{asked} Answer as your final message, in the shape the output "
            "schema asks: `answer` (your reply), `how_known` (checked, recalled or inferred) "
            "and `sources` (what you stood on). The runtime writes your last message to "
            f"{answer}, where the caller waits on it. Do not write that file yourself — your "
            "sandbox may refuse it, and only the message the runtime writes reaches the caller."
        )
    return (
        f"A colleague calls you with a question. Read {note} first — it holds the thread "
        f"and the question.{asked} Answer in the record: write your reply to {answer} "
        "(create it, or overwrite it — the note holds the thread) as one JSON object "
        "with `answer` (your reply), `how_known` (checked, recalled or inferred) and "
        "`sources` (what you stood on, as a list), and end your turn once it is written. "
        "The caller waits on that file, not on your words here."
    )


def answer_path(note: str, short_id: str) -> str:
    """Where a reply lands when the caller names nowhere: beside the note,
    named as a reply from the colleague, so two replies never collide on
    one filename (two did at 09:15 on 2026-09-05)."""
    given = Path(note)
    topic = _FROM.sub("", given.stem) or given.stem
    return str(given.parent / f"from-{short_id}-re-{topic}.md")


def picked_line(who: Session) -> str:
    """What a bare-name call says first (card #110, item 5): which session
    it picked by recency, at what effort and in what sandbox — so a caller
    who needs judgment at high effort, or a probe the sandbox allows, can
    choose another session or a fresh thread before the minutes are
    spent. The carried defect's evidence: a call to the bare name landed
    on a lane at effort none and then on a probe in a read-only sandbox,
    and the caller learned which only from the answer that never came."""
    # What is said is what was read — the latest turn's settings from the
    # rollout — and not a prediction of the next turn's, which is Codex's
    # to resolve when the resume runs (the cold read of round five: "do not
    # replace the scanner with another predictor and call the prediction
    # checked").
    effort = who.effort.value if who.effort is not None else "unknown"
    return (
        f"picked {who.short_id}, the most recent {who.slot} worker; its latest turn ran at "
        f"effort {effort} in sandbox {who.sandbox or 'unknown'} — name a session id to choose "
        "another, or --fresh for a new thread at the effort you name"
    )


def call(runtime: Runtime, args: argparse.Namespace) -> int:
    note = str(Path(args.note).expanduser().resolve())
    if not Path(note).is_file():
        print(f"{note} is not a file; a call names the note that holds the thread", file=sys.stderr)
        return 1
    if args.fresh:
        if args.who != codex.SLOT:
            print(
                f"--fresh starts a new thread of the other make; call {codex.SLOT} --fresh",
                file=sys.stderr,
            )
            return 1
        return _call_fresh(runtime, args, note)
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
    if args.who == codex.SLOT and isinstance(who, Session) and not args.json:
        print(picked_line(who))
    answer = (
        str(Path(args.answer).expanduser().resolve()) if args.answer else answer_path(note, short)
    )
    by_message = isinstance(who, Session) and who.slot == codex.SLOT
    brief = call_brief(note, answer, args.objective, by_message=by_message)
    # The call's time is before the launch, not after: a worker that answers
    # inside the launch's own observation window (a Codex worker can) would
    # otherwise have landed its answer before the call it answers.
    called_at = clock.now()
    launch = runtime.call(who, brief=brief, name=name, answer=answer)
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
        at=called_at,
    )
    placement = launch.placement
    where = rung_words(placement.model, placement.slot) if placement else launch.session.slot
    forked = f" (resumed from {short})" if launch.session.session_id != session_id else ""
    text = (
        f"call {record.id}: {launch.session.short_id}{forked} is working on {note}, {where}\n"
        f"  the answer lands in {answer}\n"
        f"  wait for it: needle wait {record.id}"
    )
    _emit(args, record, text)
    return 0


def _call_fresh(runtime: Runtime, args: argparse.Namespace, note: str) -> int:
    """A call to a fresh colleague of the other make (card #110, item 5):
    no earlier thread, the effort the caller names — high by default,
    where the doctrine puts judgment — a read-only sandbox in the caller's
    own directory so the reading can run a probe over the files, and the
    row every call leaves, so `needle wait` follows it and the close can
    check it. The one sibling of the warm call: `Runtime.ask` is the
    launch card #87's focus loop already uses, so a fresh reading is one
    thing however it is asked for."""
    given = Path(note)
    topic = _FROM.sub("", given.stem) or given.stem
    # To the microsecond, so two fresh calls on one note in one second never
    # share an answer, a schema or a log (pass two's reader).
    stamp = clock.now().strftime("%H%M%S%f")
    answer = (
        str(Path(args.answer).expanduser().resolve())
        if args.answer
        else str(given.parent / f"from-{codex.SLOT}-fresh-{stamp}-re-{topic}.md")
    )
    brief = call_brief(note, answer, args.objective, by_message=True)
    schema = codex.schema_path(answer)
    try:
        schema.parent.mkdir(parents=True, exist_ok=True)
        schema.write_text(json.dumps(Answer.model_json_schema(), indent=1), encoding="utf-8")
    except OSError as error:
        print(f"the answer's schema could not be written beside it: {error}", file=sys.stderr)
        return 1
    called_at = clock.now()
    launch = runtime.ask(
        cwd=os.getcwd(),
        name=f"call-fresh-{topic}",
        brief=brief,
        answer=answer,
        schema=str(schema),
        effort=Gate(args.effort),
    )
    if launch.verdict != LaunchVerdict.ALIVE:
        _emit(args, launch, describe_launch(launch))
        return 1
    session = launch.session
    record = runtime.store.record_call(
        session_id=session.session_id if session is not None else "unknown",
        slot=codex.SLOT,
        name=session.name if session is not None else f"{codex.SLOT}-fresh",
        note=note,
        answer=answer,
        brief=brief,
        caller=os.getcwd(),
        at=called_at,
    )
    who = f" {session.short_id}" if session is not None else ""
    text = (
        f"call {record.id}: a fresh {codex.SLOT} thread{who} is working on {note}, effort "
        f"{args.effort}, sandbox read-only, in {os.getcwd()}\n"
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
            # The row holds the answer's words from the moment anyone saw
            # it land, not from the loop's next beat: a close that quotes
            # the verdict can follow the wait at once (the cold read of
            # round eleven). Idempotent with the loop's own ending.
            runtime.store.end_call(record.id, clock.now(), verdict.words)
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

    p_sessions = parser(
        "sessions", "every session on this machine, across every slot, as one list", sessions
    )
    p_sessions.add_argument(
        "--lean", action="store_true", help="without each session's brief: what the wire asks"
    )
    p_scopes = parser(
        "scopes", "every process group of ours, who is home in it, and what else it holds", scopes
    )
    p_scopes.add_argument("--stray", action="store_true", help="only the groups nobody is home in")
    p_scopes.add_argument("--count", action="store_true", help="print how many, nothing else")
    p_scopes.add_argument("--held", action="store_true", help="the groups raw, as the wire asks")
    p_scopes.add_argument("--pids", dest="pids_unit", help="what one group holds, by unit")
    p_scopes.add_argument("--stop", dest="stop_unit", help="ask the manager to end one group")

    p_where = parser("where", "where work runs next, as claude-acct's one rule answers it", where)
    # `where` answers for this machine and the board asks it over the wire
    # (never with --repo); a placement across machines (--repo) and the
    # high-water reading are the board's own questions (Codex's ninth pass).
    p_where.set_defaults(board=lambda a: bool(a.high_water or a.repo))
    p_where.add_argument("--from", dest="from_slot", help="the slot to ask first")
    p_where.add_argument(
        "--repo", help="the project the card is in: picks the machine first (card #83)"
    )
    p_where.add_argument(
        "--high-water", dest="high_water", help="a machine's memory high-water mark, for the loop"
    )
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
    p_start.add_argument(
        "--windowless",
        action="store_true",
        help="a session in the checkout with no worktree and no window (a reading, a planning)",
    )

    p_resume = parser(
        "resume", "resume a session where the rule says, with the words given", resume
    )
    p_resume.add_argument("short")
    p_resume.add_argument("--prompt", help="what the resumed session is told")
    p_resume.add_argument("--card", help="the lane's name, when the record does not say")
    p_resume.add_argument("--to", help="the slot to resume on; the rule decides otherwise")
    p_resume.add_argument("--reason", help="what the ledger records for the move")

    p_rescope = parser("rescope", "put a session back in its lane's scope", rescope)
    p_rescope.add_argument("short")
    p_rescope.add_argument("card", help="the lane's name: the scope carries it")

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
    p_stop.add_argument(
        "--keep-handoff",
        dest="keep_handoff",
        action="store_true",
        help="the board's own stop of a walled session that waits for room (card #107)",
    )

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

    p_show = parser(
        "show",
        "put a card in front of the owner: the board's page opens it and its window comes "
        "forward, or opens",
        show,
    )
    p_show.add_argument("slug")
    p_show.add_argument("number", type=int)

    p_tell = parser("tell", "raise a notice on this machine's screen, as the board asks", tell)
    p_tell.add_argument("--notice", required=True, help="the notice as JSON")
    p_tell.add_argument(
        "--open", dest="opens", action="append", help="a word of the button's command"
    )

    p_cause = parser("cause", "what took a session's process, from this machine's evidence", cause)
    p_cause.add_argument("short")
    p_cause.add_argument("--unit", dest="units", action="append", help="a space it may have run in")
    p_cause.add_argument("--sighting", help="the board's last sighting of it, as JSON")

    p_ended = parser("ended", "why a session with no lane ended, in one line", ended)
    p_ended.add_argument("short")

    parser("boots", "this machine's boots, newest first", boots)

    p_worktrees = parser("worktrees", "every checkout of a repository on this machine", worktrees)
    p_worktrees.add_argument("repo")
    p_tip = parser("tip", "a lane branch's tip and birth on this machine", tip)
    p_tip.add_argument("repo")
    p_tip.add_argument("branch")
    p_push = parser("push", "the git half of a fold, on the machine that holds the lane", push)
    p_push.add_argument("--worktree", required=True, help="the lane's worktree")
    p_push.add_argument("--main", action="store_true", help="promote main from the same commit")
    p_level = parser("level", "this machine's clone of a project, level with the trunk", level)
    p_level.add_argument("repo")
    p_board = sub.add_parser("board", help="which machine the board serves from")
    p_board.add_argument("name", nargs="?", help="a machine's name, or here; none to ask")
    p_board.set_defaults(run=_with_runtime(board))
    p_edits = parser("edits", "what a checkout on this machine has changed", edits)
    p_edits.add_argument("checkout")
    p_edits.add_argument("--lane", action="store_true", help="from the lane's birth to its tip")
    p_edits.add_argument("--birth", help="the commit the lane was born at")
    p_edits.add_argument("--tip", help="the lane's tip")
    p_docs = parser("lane-docs", "a lane's own plan and review records", lane_docs)
    p_docs.add_argument("checkout")
    p_docs.add_argument("--plan", dest="plans", action="append", help="a candidate plan path")
    p_docs.add_argument("--reviews", action="store_true", help="the review records too")
    p_dispatches = parser("dispatches", "what the sessions in a directory handed out", dispatches)
    p_dispatches.add_argument("cwd")
    p_size = parser("transcript-size", "how large a session's transcript is here", transcript_size)
    p_size.add_argument("short")

    p_limits = parser("limits", "a slot's last limits reading on this machine", limits_read)
    p_limits.add_argument("slot")

    p_expire = parser("expire-handoff", "remove a handoff nothing will act on", expire_handoff)
    p_expire.add_argument("session_id")

    p_room = parser("room", "this machine against the floor: memory, swap, every group", room)
    p_room.add_argument(
        "--hold", action="store_true", help="give every group without it the floor as its high mark"
    )
    p_room.add_argument(
        "--owner",
        dest="owners",
        action="append",
        help="unit=slug:number — the card a group is, so the reading names it (the wire's form)",
    )

    p_observe = parser(
        "observe", "everything a board asks this machine on one pass, in one answer", observe
    )
    p_observe.add_argument(
        "--ask", help="the board's Ask as JSON, or - to read it on stdin; none is the empty ask"
    )
    p_beats = parser("beats", "the last passes as the board timed them", beats)
    p_beats.add_argument("--last", action="store_true", help="the newest pass alone")
    p_beats.add_argument("--count", type=int, default=10, help="how many passes, newest first")
    p_beats.set_defaults(board=True)

    p_machines = parser("machines", "every machine the board knows, with what each holds", machines)
    # The registry and its measurements are the board's (Codex's eighth
    # pass on card #83): on a machine that is not the board's these run
    # there, like every verb that opens the board's store.
    p_machines.set_defaults(board=True)
    p_machine = sub.add_parser("machine", help="register or forget a machine, or write a timing")
    machine_sub = p_machine.add_subparsers(dest="machine_verb", required=True)
    p_add = machine_sub.add_parser("add", help="register a machine on the board")
    p_add.add_argument("name", help="the word the board uses for it: laptop, rented")
    p_add.add_argument("--host", help="the ssh name the board reaches it by; none for this one")
    p_add.add_argument("--desktop", action="store_true", help="it holds the owner's screen")
    p_add.add_argument("--ground", help="the project that is its own record; its cards run there")
    # Its own dest: `command` is the top-level verb's, and an option under
    # a nested verb with the same dest overwrote it (Codex's tenth pass).
    p_add.add_argument(
        "--command", dest="needle_command", help="how needle runs there, as a shell line"
    )
    p_add.add_argument("--json", action="store_true", help="answer as JSON")
    p_add.set_defaults(board=True, run=_with_runtime(machine_add))
    p_rm = machine_sub.add_parser("rm", help="forget a machine")
    p_rm.add_argument("name")
    p_rm.add_argument("--json", action="store_true", help="answer as JSON")
    p_rm.set_defaults(board=True, run=_with_runtime(machine_rm))
    p_timing = machine_sub.add_parser("timing", help="write one measured build time for a machine")
    p_timing.add_argument("name")
    p_timing.add_argument("what", help="npm ci, vitest, pytest")
    p_timing.add_argument("seconds", type=float)
    p_timing.add_argument("--json", action="store_true", help="answer as JSON")
    p_timing.set_defaults(board=True, run=_with_runtime(machine_timing))
    p_host = machine_sub.add_parser("host", help="how the board reaches a machine, by its id")
    p_host.add_argument("name")
    p_host.add_argument("host", help="the ssh name")
    p_host.add_argument("--json", action="store_true", help="answer as JSON")
    p_host.set_defaults(board=True, run=_with_runtime(machine_host))

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
    p_call.add_argument(
        "--fresh",
        action="store_true",
        help="a new thread of the other make with no earlier context (`call codex --fresh`), "
        "read-only in the current directory, recorded as a row like any call",
    )
    p_call.add_argument(
        "--effort",
        choices=[g.value for g in Gate],
        default=Gate.HIGH.value,
        help="the reasoning effort of a fresh thread; high unless said",
    )

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
