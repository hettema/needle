"""Starting, moving and stopping sessions, each verified by positive evidence.

`claude --bg` exits 0 for a session that dies a second later, so a launch is
never trusted on its exit code. The verdict comes from the registry (the row
appears and stays), from /proc (the process is there and stays) and from the
wall detector's handoff file (a death on a limit, with its reason and the
rung the one rule chose next). A session that died on a wall is stopped and
the walk continues where the handoff names, up to a limit, so a launch never
loops. After a verified start the session's processes are put in a scope of
their own, so nothing the board does can end them.
"""

import re
import time
from dataclasses import dataclass
from pathlib import Path

from domain.gate import Gate
from domain.launch import Attempt, Launch, LaunchVerdict, Start, Stopped
from domain.session import Session, SessionKind, SessionSlot
from domain.slot import Handoff, Model, Placement, Rung, Slot
from infrastructure import clock
from infrastructure.store import Store
from runtime import handoffs, machine, registry, rule, slots

OBSERVATION_SECONDS = 5.0
"""How long a registered row must keep a live process before "registered"
reads "alive". A launch on a spent slot registered `working` at 0.5 s and
read `blocked` at 1.0 s (gmail, 2026-09-04 09:17); 0.1 saw a death at 1.6 s."""

VERIFY_SECONDS = 15.0
"""The deadline for a verdict either way; past it the answer is "unconfirmed"."""

HANDOFF_GRACE_SECONDS = 3.0
"""How long after the registry reads `blocked` the wall detector's file is
waited for, since the hook writes it a moment after the registry moves."""

POLL_SECONDS = 0.4

STOP_SECONDS = 8.0
"""`claude stop` ended a session in 1.6 s (2026-09-04); past eight it is a failure."""

SCOPE_SETTLE_SECONDS = 3.0
"""How long to let a queued scope adoption move the process before calling it
unverified; the move landed well under a second on 2026-09-04."""
SCOPE_POLL_SECONDS = 0.1

WALK_LIMIT = 4
"""Rungs a start may die on before it stops rather than loops; `claude-acct`
holds its supervisor to the same count."""

RESUME_SIZE_LIMIT = 8 * 1024 * 1024
"""Above this a move starts a fresh session with the brief instead of
resuming the transcript, and a look window names the transcript instead of
loading it. Measured 2026-09-04: the print-mode loader reads 14.6 MB in
1.9 s, but an interactive resume of a 15 MB transcript never registered a
process in 120 s, which is the hang 0.1 saw at 10 MB. Readiness below 15 MB
could not be observed from outside; the number is a belief with a loud loop,
because every resume is verified and a hang reads as unconfirmed, never as
alive."""

PROMPTS_SETTLED = ("--permission-mode", "bypassPermissions", "--strict-mcp-config")
"""What a windowless session needs so that it never stops at a prompt nobody
can answer (0.1's owner ruling, 2026-08-31)."""

CONTINUE = (
    "Continue where you stopped. The subscription you were running on ran out, "
    "so the runtime moved you to one that has headroom — nothing else changed."
)

DAEMON_UNIT_PREFIX = "claude-daemon-"
SESSION_UNIT_PREFIX = "needle-"

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_BACKGROUNDED = re.compile(r"backgrounded\s*[·:]?\s*([0-9a-f]{8})\b")


def short_id_in(output: str) -> str | None:
    """The id `claude --bg` prints: `backgrounded · <short> · <name>`."""
    match = _BACKGROUNDED.search(_ANSI.sub("", output))
    return match.group(1) if match else None


def argv_for(
    placement: Placement,
    *,
    effort: Gate | None,
    name: str | None,
    prompt: str,
    resume: str | None,
    worktree: str | None,
) -> list[str]:
    """The one argv for a background session. No `--session-id` (the CLI
    assigns its own under `--bg`) and no `--fallback-model` (a silent drop to
    a weaker model is what the rule exists to prevent)."""
    argv = [machine.which("claude"), "--bg", "--model", placement.model.value]
    if effort is not None:
        argv += ["--effort", effort.value]
    if worktree:
        argv += ["--worktree", worktree]
    if name:
        argv += ["-n", name]
    if resume:
        argv += ["--resume", resume]
    return [*argv, *PROMPTS_SETTLED, prompt]


def fresh_brief(session: Session, size: int) -> str:
    path = machine.transcript_path(session.worktree or session.cwd, session.session_id)
    return (
        f"This is a fresh session for {session.name}. Its previous session "
        f"{session.short_id} moved subscription and its transcript ({size / 1048576:.1f} MB) "
        f"is above the {RESUME_SIZE_LIMIT // 1048576} MB the runtime resumes, so it was not "
        f"loaded. Read the end of it first: `tail -c 200000 {path}`. The original brief "
        f"follows.\n\n{session.intent}"
    )


def placement_from(handoff: Handoff) -> Placement | None:
    slot = slots.slot_named(handoff.account)
    if slot is None:
        return None
    return Placement(
        slot=slot.name,
        model=handoff.model or Model.FABLE,
        config_dir=slot.config_dir,
        why=handoff.reason,
    )


# ── verification ───────────────────────────────────────────────────────


@dataclass
class Verified:
    verdict: LaunchVerdict
    reason: str | None
    seconds: float
    session_id: str | None
    pid: int | None
    handoff: Handoff | None
    state: dict[str, object] | None


def verify(config_dir: Path, short_id: str, since: float) -> Verified:
    """Did the session we just started actually take? Positive evidence only."""
    deadline = since + VERIFY_SECONDS
    blocked_at: float | None = None
    seen_pid: int | None = None
    while True:
        now = time.time()
        state = registry.read_state(config_dir, short_id)
        sid = str(state["sessionId"]) if state and state.get("sessionId") else None
        wall = handoffs.read_handoffs().by_session.get(sid) if sid else None
        # A handoff older than this launch is the one a move is acting on, kept
        # on disk until the move is verified; only a newer one is a death here.
        if wall is not None and wall.at.timestamp() >= since:
            return Verified(
                LaunchVerdict.DEAD, wall.reason, now - since, sid, seen_pid or wall.pid, wall, state
            )
        pid = registry.live_pid(config_dir, sid) if sid else None
        if pid is not None:
            seen_pid = pid
        recorded = str(state.get("state") or "") if state else ""
        detail = str(state.get("detail") or "") if state else ""
        if recorded == "stopped" or (seen_pid is not None and pid is None):
            said = f": {detail}" if detail else ""
            return Verified(
                LaunchVerdict.DEAD,
                f"the session ended {now - since:.1f} s after the start{said}",
                now - since,
                sid,
                seen_pid,
                None,
                state,
            )
        if recorded == "blocked":
            blocked_at = blocked_at or now
            if now - blocked_at >= HANDOFF_GRACE_SECONDS:
                return Verified(
                    LaunchVerdict.DEAD,
                    f"blocked {blocked_at - since:.1f} s after the start and no handoff "
                    f"names it: {detail or 'no detail recorded'}",
                    now - since,
                    sid,
                    seen_pid,
                    None,
                    state,
                )
        elif pid is not None and now - since >= OBSERVATION_SECONDS:
            return Verified(LaunchVerdict.ALIVE, None, now - since, sid, pid, None, state)
        if now >= deadline:
            return Verified(
                LaunchVerdict.UNCONFIRMED,
                f"neither a live row nor a recorded death within {VERIFY_SECONDS:.0f} s",
                now - since,
                sid,
                seen_pid,
                None,
                state,
            )
        time.sleep(POLL_SECONDS)


def wait_gone(pid: int, seconds: float) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if machine.process_start(pid) is None:
            return True
        time.sleep(0.2)
    return machine.process_start(pid) is None


# ── scopes ─────────────────────────────────────────────────────────────


@dataclass
class Scoped:
    unit: str
    asked: bool
    verified: bool
    """The session's process reads the unit in /proc after the adoption."""
    words: str


def scope_session(slot: Slot | Placement, config_dir: Path, pid: int, card: str) -> Scoped:
    """Put the slot's daemon in a scope of its own, and the session's pty host
    and process in one named after the card.

    A daemon is born in the cgroup of whoever first ran `claude --bg` under
    its directory, and every session is the daemon's child: on 2026-09-04
    both daemons and every lane sat in 0.1's service unit. Adopting the
    daemon is what makes "nothing the board does can end it" true; adopting
    the session is what makes `systemctl --user` show one unit per lane.
    """
    daemon_unit = machine.unit_name(
        DAEMON_UNIT_PREFIX, slot.slot if isinstance(slot, Placement) else slot.name
    )
    daemon_pid: int | None = None
    lock = registry.read_json(config_dir / "daemon.lock")
    if lock is not None and isinstance(lock.get("pid"), int):
        start = lock.get("procStart")
        candidate = int(lock["pid"])
        if machine.process_alive(candidate, str(start) if start is not None else None):
            daemon_pid = candidate
            if machine.cgroup_of(candidate) != daemon_unit:
                machine.adopt(daemon_unit, [candidate])
    unit = machine.unit_name(SESSION_UNIT_PREFIX, card)
    if machine.cgroup_of(pid) == unit:
        return Scoped(unit, False, True, "already there")
    pids: list[int] = []
    parent = machine.parent_of(pid)
    if parent is not None and parent > 1 and parent != daemon_pid:
        pids.append(parent)
    pids += [pid, *machine.descendants_of(pid)]
    try:
        asked, words = machine.adopt(unit, pids)
    except machine.CommandMissing as missing:
        return Scoped(unit, False, False, str(missing))
    # `StartTransientUnit` returns a queued job, so the move into the scope
    # lands a moment after busctl returns (verified 2026-09-04: the scope read
    # empty at once and held the process a moment later). Poll /proc for the
    # process to settle into the unit rather than declaring a real success
    # unverified.
    verified = asked and _in_scope(pid, unit)
    return Scoped(unit, asked, verified, words)


def _in_scope(pid: int, unit: str) -> bool:
    deadline = time.time() + SCOPE_SETTLE_SECONDS
    while True:
        if machine.cgroup_of(pid) == unit:
            return True
        if time.time() >= deadline:
            return False
        time.sleep(SCOPE_POLL_SECONDS)


# ── the verbs ──────────────────────────────────────────────────────────


def _rung(placement: Placement) -> Rung:
    return Rung(slot=placement.slot, model=placement.model)


def _row(placement: Placement, short_id: str) -> Session | None:
    slot = Slot(name=placement.slot, config_dir=placement.config_dir)
    walls = handoffs.read_handoffs().by_session
    return next((s for s in registry.read_registry(slot, walls) if s.short_id == short_id), None)


def dead(card: str, attempts: list[Attempt], reason: str, placement: Placement | None) -> Launch:
    return Launch(
        card=card,
        verdict=LaunchVerdict.DEAD,
        session=None,
        placement=placement,
        scope=None,
        attempts=attempts,
        reason=reason,
    )


def _launch(placement: Placement, argv: list[str], cwd: Path) -> tuple[str | None, str, float]:
    """Run `claude --bg`; the short id it printed, or None with its words."""
    env = machine.session_env(placement.config_dir, placement.slot)
    since = time.time()
    try:
        done = machine.run(argv, env=env, cwd=cwd, timeout=60)
    except (OSError, machine.Timeout) as error:
        return None, f"`claude --bg` could not run: {error}", since
    short = short_id_in(done.stdout)
    if short is None:
        said = (done.stderr or done.stdout).strip()[:300]
        return None, f"`claude --bg` exited {done.returncode} without a session id: {said}", since
    return short, done.stdout, since


def _stop_probe(placement: Placement, short_id: str, pid: int | None) -> None:
    """A launch that died on a wall still registers and its process stays;
    stopping it is what keeps the dead attempt off the one list."""
    env = machine.session_env(placement.config_dir, placement.slot)
    try:
        machine.run([machine.which("claude"), "stop", short_id], env=env, timeout=30)
    except (OSError, machine.Timeout, machine.CommandMissing):
        return
    if pid is not None:
        wait_gone(pid, STOP_SECONDS)


def _settle(
    store: Store,
    placement: Placement,
    short_id: str,
    verified: Verified,
    card: str,
    attempts: list[Attempt],
) -> Launch:
    assert verified.pid is not None and verified.session_id is not None
    scoped = scope_session(placement, Path(placement.config_dir), verified.pid, card)
    store.record_session_slot(
        SessionSlot(
            session_id=verified.session_id,
            slot=placement.slot,
            card=card,
            scope=scoped.unit,
            recorded_at=clock.now(),
        )
    )
    return Launch(
        card=card,
        verdict=LaunchVerdict.ALIVE,
        session=_row(placement, short_id),
        placement=placement,
        scope=scoped.unit if scoped.verified else None,
        attempts=attempts,
        reason=None if scoped.verified else f"running, but not in its own scope: {scoped.words}",
    )


def start(store: Store, request: Start) -> Launch:
    """Start a session for a card where the rule says, in a worktree of its
    own, and walk down the ladder when a rung dies on a wall."""
    repo = Path(request.repo)
    if not (repo / ".git").exists():
        return dead(
            request.card, [], f"{repo} is not a git repository; a lane needs a worktree", None
        )
    where = rule.where(request.from_slot, [], cached=False)
    if where.placement is None:
        return dead(request.card, [], where.reason, None)
    placement = where.placement
    attempts: list[Attempt] = []
    prompt, resume, worktree_flag, cwd = request.brief, None, request.card, repo
    while len(attempts) < WALK_LIMIT:
        argv = argv_for(
            placement,
            effort=request.effort,
            name=request.card,
            prompt=prompt,
            resume=resume,
            worktree=worktree_flag,
        )
        short, words, since = _launch(placement, argv, cwd)
        if short is None:
            attempts.append(
                Attempt(
                    rung=_rung(placement),
                    verdict=LaunchVerdict.DEAD,
                    short_id=None,
                    reason=words,
                    seconds=round(time.time() - since, 2),
                )
            )
            return dead(request.card, attempts, words, placement)
        verified = verify(Path(placement.config_dir), short, since)
        attempts.append(
            Attempt(
                rung=_rung(placement),
                verdict=verified.verdict,
                short_id=short,
                reason=verified.reason,
                seconds=round(verified.seconds, 2),
            )
        )
        if verified.verdict == LaunchVerdict.ALIVE:
            return _settle(store, placement, short, verified, request.card, attempts)
        if verified.verdict == LaunchVerdict.DEAD and verified.handoff is not None:
            wall = verified.handoff
            _stop_probe(placement, short, verified.pid)
            next_placement = placement_from(wall)
            if next_placement is None:
                return dead(
                    request.card,
                    attempts,
                    f"the handoff names {wall.account!r}, which accounts.json does not declare",
                    placement,
                )
            assert verified.session_id is not None
            store.record_rescue(
                verified.session_id,
                _rung(placement),
                _rung(next_placement),
                wall.reason,
                clock.now(),
            )
            handoffs.remove(wall)
            recorded_worktree = verified.state.get("worktreePath") if verified.state else None
            home = (
                str(recorded_worktree)
                if isinstance(recorded_worktree, str) and recorded_worktree
                else wall.worktree or wall.cwd or str(cwd)
            )
            placement, resume, prompt = next_placement, verified.session_id, wall.prompt or CONTINUE
            worktree_flag, cwd = None, Path(home)
            continue
        if verified.verdict == LaunchVerdict.DEAD:
            _stop_probe(placement, short, verified.pid)
            return dead(request.card, attempts, verified.reason or "died", placement)
        return Launch(
            card=request.card,
            verdict=LaunchVerdict.UNCONFIRMED,
            session=_row(placement, short),
            placement=placement,
            scope=None,
            attempts=attempts,
            reason=verified.reason,
        )
    return dead(
        request.card,
        attempts,
        f"{WALK_LIMIT} rungs died in a row; stopping rather than looping",
        placement,
    )


def stop(session: Session) -> Stopped:
    """End a session through its own slot, and prove the process is gone."""
    env = machine.session_env(session.config_dir, session.slot)
    since = time.time()
    try:
        done = machine.run([machine.which("claude"), "stop", session.short_id], env=env, timeout=30)
        words = (done.stdout or done.stderr).strip()
    except (OSError, machine.Timeout, machine.CommandMissing) as error:
        words = f"`claude stop` could not run: {error}"
    gone = wait_gone(session.pid, STOP_SECONDS) if session.pid is not None else True
    return Stopped(
        short_id=session.short_id,
        session_id=session.session_id,
        slot=session.slot,
        gone=gone,
        seconds=round(time.time() - since, 2),
        words=words,
    )


def move(store: Store, session: Session, *, to: Placement | None, card: str) -> Launch:
    """Move a session to another slot: stop it where it runs, resume it where
    the handoff or the rule names, or start it fresh with its brief when the
    transcript is above the resume limit. One hop per call."""
    name = session.name
    if session.stale:
        return dead(
            name,
            [],
            f"{session.short_id} on {session.slot} is a stale copy; move the live one",
            None,
        )
    if session.kind == SessionKind.INTERACTIVE:
        return dead(
            name,
            [],
            f"{session.short_id} runs in a terminal of its own; the runtime does not move it",
            None,
        )
    wall = session.wall
    if to is None and wall is not None:
        to = placement_from(wall)
        if to is None:
            return dead(
                name,
                [],
                f"the handoff names {wall.account!r}, which accounts.json does not declare",
                None,
            )
    if to is None:
        where = rule.where(session.slot, [Rung(slot=session.slot, model=None)], cached=False)
        if where.placement is None:
            return dead(name, [], where.reason, None)
        to = where.placement
    attempts: list[Attempt] = []
    if session.pid is not None:
        stopped = stop(session)
        if not stopped.gone:
            return dead(
                name,
                attempts,
                f"could not stop {session.short_id} on {session.slot} within {STOP_SECONDS:.0f} s: "
                f"{stopped.words}",
                to,
            )
    home = session.worktree or session.cwd
    size = machine.transcript_size(home, session.session_id)
    fresh = size is not None and size > RESUME_SIZE_LIMIT
    if fresh:
        assert size is not None
        prompt, resume = fresh_brief(session, size), None
    else:
        prompt, resume = (wall.prompt if wall and wall.prompt else CONTINUE), session.session_id
    argv = argv_for(
        to, effort=session.effort, name=name, prompt=prompt, resume=resume, worktree=None
    )
    short, words, since = _launch(to, argv, Path(home))
    if short is None:
        attempts.append(
            Attempt(
                rung=_rung(to),
                verdict=LaunchVerdict.DEAD,
                short_id=None,
                reason=words,
                seconds=round(time.time() - since, 2),
            )
        )
        return dead(name, attempts, words, to)
    verified = verify(Path(to.config_dir), short, since)
    attempts.append(
        Attempt(
            rung=_rung(to),
            verdict=verified.verdict,
            short_id=short,
            reason=verified.reason,
            seconds=round(verified.seconds, 2),
        )
    )
    if verified.verdict != LaunchVerdict.ALIVE:
        if verified.verdict == LaunchVerdict.DEAD:
            _stop_probe(to, short, verified.pid)
        return Launch(
            card=name,
            verdict=verified.verdict,
            session=_row(to, short) if verified.verdict == LaunchVerdict.UNCONFIRMED else None,
            placement=to,
            scope=None,
            attempts=attempts,
            reason=verified.reason,
        )
    launch = _settle(store, to, short, verified, card, attempts)
    reason = wall.reason if wall else "moved by request"
    if fresh:
        assert size is not None and verified.session_id is not None
        reason += (
            f"; fresh session {verified.session_id} because the transcript is "
            f"{size / 1048576:.1f} MB, above the {RESUME_SIZE_LIMIT // 1048576} MB resume limit"
        )
    from_rung = Rung(slot=session.slot, model=session.model)
    store.record_rescue(session.session_id, from_rung, _rung(to), reason, clock.now())
    if wall is not None:
        handoffs.remove(wall)
    return launch
