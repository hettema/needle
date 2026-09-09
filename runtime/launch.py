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

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path

from domain.call import Answer
from domain.dial import MEMORY_FLOOR_BYTES
from domain.gate import Gate
from domain.launch import Attempt, Launch, LaunchVerdict, Rescue, Start, Stopped, WindowlessStart
from domain.session import Session, SessionKind, SessionSlot, SessionState
from domain.slot import Handoff, Make, Placement, Rung, Slot
from infrastructure import clock, paths
from infrastructure.store import Store
from runtime import codex, git, handoffs, machine, registry, rule, slots

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

MOVED_BY_REQUEST = "moved by request"
RESUMED_WITH_ANSWER = "resumed with the owner's answer"
"""The ledger's reasons for a move nobody's wall caused: `needle move`, and a
resume with a brief (the Answer door, a call). A wall's move carries the
wall's own words instead."""


def on_a_wall(rescue: Rescue) -> bool:
    """Whether a rescue in the ledger was a wall's move. The park rule — one
    automatic retry per run-out, a second wall within the hour parks —
    counts only these: a resume by request is in the same ledger, and
    counting it parked a called colleague on its first wall (plan 17,
    review pass 1) and would park a lane walled within an hour of the
    owner's answer."""
    return not rescue.reason.startswith((MOVED_BY_REQUEST, RESUMED_WITH_ANSWER))


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
    """The one argv for a background Claude session. No `--session-id` (the
    CLI assigns its own under `--bg`) and no `--fallback-model` (a silent
    drop to a weaker model is what the rule exists to prevent).

    A placement with no model named runs the slot's own top rung, with no
    `--model` flag: the rule answers `model: null` for exactly that, and the
    runtime used to turn it into the word `fable`, which was Needle
    asserting the ladder it does not own (card #63)."""
    argv = [machine.which("claude"), "--bg"]
    if placement.model:
        argv += ["--model", placement.model]
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
        make=Make.CLAUDE,
        model=handoff.model,
        config_dir=slot.config_dir,
        why=handoff.reason,
        tier=None,
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


def lane_unit(card: str) -> str:
    """The one scope a card's sessions run in, named after the lane as at
    Start: what `systemctl --user` shows per lane, what the memory reading
    asks for, and where a session that came back is put (plan 53)."""
    return machine.unit_name(SESSION_UNIT_PREFIX, card)


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
    unit = lane_unit(card)
    if machine.cgroup_of(pid) == unit:
        return Scoped(unit, False, True, "already there")
    pids: list[int] = []
    parent = machine.parent_of(pid)
    if parent is not None and parent > 1 and parent != daemon_pid:
        pids.append(parent)
    pids += [pid, *machine.descendants_of(pid)]
    try:
        asked, words = machine.adopt(unit, pids, memory_high=MEMORY_FLOOR_BYTES)
    except machine.CommandMissing as missing:
        return Scoped(unit, False, False, str(missing))
    # `StartTransientUnit` returns a queued job, so the move into the scope
    # lands a moment after busctl returns (verified 2026-09-04: the scope read
    # empty at once and held the process a moment later). Poll /proc for the
    # process to settle into the unit rather than declaring a real success
    # unverified.
    verified = asked and _in_scope(pid, unit)
    return Scoped(unit, asked, verified, words)


def rescope(store: Store, session: Session, card: str) -> Scoped:
    """Put a session that has hands on a lane back in the lane's scope,
    whoever put it elsewhere (plan 53, item 2): the machine's recover unit
    after an oom-kill, or a hand `claude --bg --resume`, both of which land
    the session in the subscription's daemon scope, where the next kill
    takes every lane on that subscription at once (2026-09-05, 17:59Z: four
    Hello Revenue lanes in one second). The same act as at Start, recorded
    the same way, so the reason for a later death is read from the lane's
    own journal."""
    assert session.pid is not None
    slot = Slot(name=session.slot, config_dir=session.config_dir)
    scoped = scope_session(slot, Path(session.config_dir), session.pid, card)
    if scoped.asked or scoped.verified:
        store.record_session_slot(
            SessionSlot(
                session_id=session.session_id,
                slot=session.slot,
                card=card,
                scope=scoped.unit,
                recorded_at=clock.now(),
            )
        )
    return scoped


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
    rescued_from: tuple[Rung, str] | None = None,
) -> Launch:
    """Record where the verified session runs and, when it is the far end of
    a move, the rescue that brought it here. A resume forks the session id
    (verified live 2026-09-04), so the ledger is written under the id that
    lives and `Runtime.rescues` of the dead id answers nothing."""
    assert verified.pid is not None and verified.session_id is not None
    if rescued_from is not None:
        from_rung, reason = rescued_from
        store.record_rescue(verified.session_id, from_rung, _rung(placement), reason, clock.now())
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
        reason=None
        if scoped.verified
        else f"running, but not in its own space on the machine: {scoped.words}",
    )


def start(store: Store, request: Start) -> Launch:
    """Start a session for a card where the rule says, in a worktree of its
    own, and walk down the ladder when a rung dies on a wall. The rule may
    name a make of its own choosing (card #63): every make lands in the same
    place with the same brief at the same effort, and each is launched by
    its own launcher, because only Claude's ladder has rungs to walk."""
    repo = Path(request.repo)
    if not (repo / ".git").exists():
        return dead(
            request.card, [], f"{repo} is not a git repository; a lane needs a worktree", None
        )
    where = rule.where(request.from_slot, [], cached=False)
    if where.placement is None:
        return dead(request.card, [], where.reason, None)
    if where.placement.make is Make.CODEX:
        return codex_lane(store, where.placement, request)
    return _walk(
        store,
        placement=where.placement,
        card=request.card,
        brief=request.brief,
        effort=request.effort,
        cwd=repo,
        worktree=request.card,
    )


def windowless(store: Store, request: WindowlessStart) -> Launch:
    """Start a session in the repository's own checkout with no worktree — a
    reading of a signal (plan 09, item 1) or the planning of a defect under
    the dial (plan 11, item 4): the same walk as a lane's, so the board never
    reads it as hands on a tree.

    Asked of the rule with the Codex rung already spent, so the answer is a
    Claude one. A windowless session works in the project's own checkout,
    and the one thing this card gave the other make is a lane sandboxed to a
    worktree; running it here would either hand it the main checkout or
    invent a second shape of Codex session for a reading. Neither is this
    card's (`docs/plans/…-drives-the-card-claude-or-codex.md`, item 1), so
    the reading stays Claude's until a card gives the other make one, and
    `--tried` is how the rule is told, not a make of our own choosing.
    """
    where = rule.where(None, [CODEX_RUNG], cached=False)
    if where.placement is None:
        return dead(request.card, [], where.reason, None)
    if where.placement.make is not Make.CLAUDE:
        return dead(
            request.card,
            [],
            f"the rule answered {where.placement.make.value} even with that make's rung spent, "
            "and a session with no window runs in the project's own checkout, which this "
            "runtime gives no make but Claude",
            where.placement,
        )
    return _walk(
        store,
        placement=where.placement,
        card=request.card,
        brief=request.brief,
        effort=request.effort,
        cwd=Path(request.repo),
        worktree=None,
    )


def _walk(
    store: Store,
    *,
    placement: Placement,
    card: str,
    brief: str,
    effort: Gate | None,
    cwd: Path,
    worktree: str | None,
) -> Launch:
    """Launch where the rule said and walk down the ladder when a rung dies
    on a wall; one verified session or a named death. Claude's, because a
    wall, a handoff and a rung below are Claude's ladder and no other make
    on this machine has one."""
    attempts: list[Attempt] = []
    prompt, resume, worktree_flag = brief, None, worktree
    rescued_from: tuple[Rung, str] | None = None
    while len(attempts) < WALK_LIMIT:
        argv = argv_for(
            placement,
            effort=effort,
            name=card,
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
            return dead(card, attempts, words, placement)
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
            return _settle(store, placement, short, verified, card, attempts, rescued_from)
        if verified.verdict == LaunchVerdict.DEAD and verified.handoff is not None:
            wall = verified.handoff
            _stop_probe(placement, short, verified.pid)
            next_placement = placement_from(wall)
            if next_placement is None:
                return dead(
                    card,
                    attempts,
                    f"the handoff names {wall.account!r}, which accounts.json does not declare",
                    placement,
                )
            assert verified.session_id is not None
            rescued_from = (_rung(placement), wall.reason)
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
            return dead(card, attempts, verified.reason or "died", placement)
        return Launch(
            card=card,
            verdict=LaunchVerdict.UNCONFIRMED,
            session=_row(placement, short),
            placement=placement,
            scope=None,
            attempts=attempts,
            reason=verified.reason,
        )
    return dead(
        card,
        attempts,
        f"{WALK_LIMIT} rungs died in a row; stopping rather than looping",
        placement,
    )


def stop(session: Session) -> Stopped:
    """End a session through its own slot, and prove the process is gone.
    A Codex worker has no slot to go through: it is asked to end by
    signal, and the same proof is read (plan 57)."""
    since = time.time()
    if session.slot == codex.SLOT:
        if session.pid is not None:
            machine.terminate(session.pid)
        gone = wait_gone(session.pid, STOP_SECONDS) if session.pid is not None else True
        return Stopped(
            short_id=session.short_id,
            session_id=session.session_id,
            slot=session.slot,
            gone=gone,
            seconds=round(time.time() - since, 2),
            words="asked to end by signal" if session.pid is not None else "no process",
        )
    env = machine.session_env(session.config_dir, session.slot)
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


def move(
    store: Store,
    session: Session,
    *,
    to: Placement | None,
    card: str,
    prompt: str | None = None,
    spent: bool = True,
    reason: str | None = None,
) -> Launch:
    """Move a session to another slot: stop it where it runs, resume it where
    the handoff or the rule names, or start it fresh with its brief when the
    transcript is above the resume limit. One hop per call.

    `prompt` is what the resumed session is told (the owner's answer, from
    the Answer door); without it the handoff's words or CONTINUE — and
    CONTINUE says the subscription ran out, which is true of a wall alone,
    so a resume after a death the machine named passes the cause's own
    words as the prompt (plan 68, item 1). `spent` says whether the slot it
    ran on is used up: a move on a wall rules the slot out, a resume after
    an answer or a death prefers to stay put. `reason` is what the ledger
    records for the move when the caller knows better than the wall or the
    two request words: the cause the board resumed after."""
    name = session.name
    if session.slot == codex.SLOT:
        return dead(
            name,
            [],
            f"{session.short_id} is a Codex session: it runs on no subscription slot and has "
            "no wall to move away from; the runtime does not move it (plan 57)",
            None,
        )
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
        tried = [Rung(slot=session.slot, model=None)] if spent else []
        where = rule.where(session.slot, tried, cached=False)
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
        told = fresh_brief(session, size) + (f"\n\nThe owner says: {prompt}" if prompt else "")
        resume = None
    else:
        told = prompt or (wall.prompt if wall and wall.prompt else CONTINUE)
        resume = session.session_id
    argv = argv_for(to, effort=session.effort, name=name, prompt=told, resume=resume, worktree=None)
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
    if reason is None:
        reason = wall.reason if wall else (RESUMED_WITH_ANSWER if prompt else MOVED_BY_REQUEST)
    if fresh:
        assert size is not None and verified.session_id is not None
        reason += (
            f"; fresh session {verified.session_id} because the transcript is "
            f"{size / 1048576:.1f} MB, above the {RESUME_SIZE_LIMIT // 1048576} MB resume limit"
        )
    from_rung = Rung(slot=session.slot, model=session.model)
    launch = _settle(store, to, short, verified, card, attempts, (from_rung, reason))
    if wall is not None:
        handoffs.remove(wall)
    return launch


def call(store: Store, session: Session, *, brief: str, name: str, answer: str) -> Launch:
    """Resume a colleague's session with a caller's brief (plan 17, item 1):
    the Answer door's shape, bound to no card. A session in a terminal of
    its own is refused, not resumed beside itself; one mid-turn is refused
    too, since the stop that precedes a resume would end the turn it is on,
    and a lane hears the note as its word instead. A call whose brief is
    empty is refused before anything runs: the by-hand form of 2026-09-05
    started a session whose prompt never arrived, and that is the refusal
    the CLI printed ("Provide a prompt"), made ours. The same refusals hold
    for a colleague of the other make (plan 57, item 1); past them a Codex
    row is resumed as a worker of its own kind, with `answer` as the file
    Codex writes its last message to."""
    if not brief.strip():
        return dead(name, [], "an empty brief calls nobody; provide a note or an objective", None)
    if (
        session.slot == codex.SLOT
        and session.kind == SessionKind.INTERACTIVE
        and session.recorded != codex.TERMINAL_SOURCE
    ):
        return dead(
            name,
            [],
            f"{session.short_id} is a Codex session of source {session.recorded!r}, which this "
            f"runtime does not know as a worker; only an `exec` rollout is called",
            None,
        )
    if session.kind == SessionKind.INTERACTIVE:
        return dead(
            name,
            [],
            f"{session.short_id} runs in a terminal of its own; it is not resumed beside "
            "itself — write the note and it hears it as its word if it is a lane",
            None,
        )
    if session.pid is not None and session.state == SessionState.WORKING:
        return dead(
            name,
            [],
            f"{session.short_id} is working on its turn; a resume would end it — "
            "call again when its turn is done, or a lane hears the note as its word",
            None,
        )
    if session.slot == codex.SLOT:
        return call_codex(store, session, brief=brief, name=name, answer=answer)
    return move(store, session, to=None, card=name, prompt=brief, spent=False)


CODEX_RUNG = Rung(slot=codex.SLOT, model=None)
"""What a Codex attempt is recorded under: the make's name, no model rung —
the rungs are Claude's subscription ladder and a worker of the other make
never stands on one."""

CODEX_LANE_SECONDS = 8.0
"""How long a Codex lane's process must live before the launch is called
alive. Longer than a Claude session's five, because a Claude launch is
verified against a registry row that appears in under a second while a Codex
one is verified against /proc and its own rollout file, which the CLI writes
after it has authenticated and loaded the project's doctrine chain — 3.1 s
on the fastest of the probe runs of 2026-09-08."""


def codex_lane(store: Store, placement: Placement, request: Start) -> Launch:
    """Give a card's lane to a worker of the other make (card #63, item 1).

    The shape a Claude lane gets, built from the parts this make has: the
    worktree laid here because `codex exec` has no `--worktree` of its own,
    the brief as the prompt, the plan's effort as the reasoning level, the
    process detached so nothing the board does ends it, and the same scope
    named after the card. What it does not get is a walk: a wall, a handoff
    and a rung below are Claude's ladder, and this make has none of the
    three (plan 57's ruling), so a launch that dies is a death with the
    log's last words and not a step down.

    A death takes the worktree back with it. A lane the board can see but no
    session ever held is the worst of both — the card reads as taken and
    Start is closed on it — so a launch that never came alive leaves nothing
    behind, which is what a failed `claude --bg` leaves too.
    """
    repo = Path(request.repo)
    name = request.card
    path = repo / ".claude" / "worktrees" / name
    log = paths.data_dir() / "lanes" / f"{name}.log"
    ours = not path.exists()
    if ours:
        laid = git.add_worktree(repo, path, name)
        if laid is not None:
            return dead(
                name, [], f"the lane's own copy of the code could not be laid: {laid}", placement
            )
    argv = codex.lane_argv(
        path,
        model=placement.model,
        effort=request.effort,
        prompt=request.brief,
        roots=codex.lane_roots(repo, name, machine.package_cache()),
    )
    since = time.time()
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
        pid = machine.detach(argv, cwd=path, log=log)
    except (OSError, machine.CommandMissing) as error:
        return _codex_died(
            name,
            path if ours else None,
            repo,
            placement,
            since,
            f"`codex exec` could not run: {error}",
        )
    born = machine.process_start(pid)
    while True:
        elapsed = time.time() - since
        if not machine.process_alive(pid, born):
            words = _last_words(log)
            return _codex_died(
                name,
                path if ours else None,
                repo,
                placement,
                since,
                f"the lane ended {elapsed:.1f} s after the start" + (f": {words}" if words else ""),
            )
        if elapsed >= CODEX_LANE_SECONDS:
            break
        time.sleep(POLL_SECONDS)
    session = _codex_lane_row(pid, str(path))
    if session is None:
        return _codex_died(
            name,
            path if ours else None,
            repo,
            placement,
            since,
            f"the process lived {time.time() - since:.1f} s but wrote no session of its own "
            f"in {machine.codex_sessions_root()}, so the board has nothing to follow",
        )
    unit = lane_unit(name)
    try:
        asked, words = machine.adopt(
            unit, [pid, *machine.descendants_of(pid)], memory_high=MEMORY_FLOOR_BYTES
        )
    except machine.CommandMissing as missing:
        asked, words = False, str(missing)
    scoped = asked and _in_scope(pid, unit)
    store.record_session_slot(
        SessionSlot(
            session_id=session.session_id,
            slot=codex.SLOT,
            card=name,
            scope=unit,
            recorded_at=clock.now(),
        )
    )
    return Launch(
        card=name,
        verdict=LaunchVerdict.ALIVE,
        session=session,
        placement=placement,
        scope=unit if scoped else None,
        attempts=[
            Attempt(
                rung=Rung(slot=placement.slot, model=placement.model),
                verdict=LaunchVerdict.ALIVE,
                short_id=session.short_id,
                reason=None,
                seconds=round(time.time() - since, 2),
            )
        ],
        reason=None if scoped else f"running, but not in its own space on the machine: {words}",
    )


def _codex_lane_row(pid: int, path: str) -> Session | None:
    """The row the board will follow: the rollout this process holds, which
    is how every Codex row is found (`runtime.codex.processes`). Read after
    the observation window, so the CLI has written its head."""
    for session_id, held in codex.processes().items():
        if held != pid:
            continue
        rows = codex.find(session_id)
        if rows:
            return rows[0].model_copy(update={"worktree": path})
    return None


def _codex_died(
    name: str, path: Path | None, repo: Path, placement: Placement, since: float, reason: str
) -> Launch:
    """A Codex lane that never came alive, with the worktree taken back —
    but only one this call laid. A worktree that was already there is a
    previous life's, with its commits in it; removing it because a fresh
    launch failed would destroy work no launch of ours wrote."""
    if path is not None and path.exists():
        git.remove_worktree(repo, path, name)
    return Launch(
        card=name,
        verdict=LaunchVerdict.DEAD,
        session=None,
        placement=placement,
        scope=None,
        attempts=[
            Attempt(
                rung=Rung(slot=placement.slot, model=placement.model),
                verdict=LaunchVerdict.DEAD,
                short_id=None,
                reason=reason,
                seconds=round(time.time() - since, 2),
            )
        ],
        reason=reason,
    )


def call_codex(store: Store, session: Session, *, brief: str, name: str, answer: str) -> Launch:
    """Resume a Codex worker with the brief (plan 57, item 2): `codex exec
    resume` detached, its output in a log beside the answer, verified the
    way a Claude launch is — the process is there past the observation
    window, or it ended and said why. An exit within the window is a
    verdict too: with the answer written it is a fast reply and the call
    is alive in the sense that matters (the record it lands in); without
    one it is a death with the log's last words. A verified worker is put
    in a scope named for the call, so the one list shows it as a unit of
    its own and its death has a journal."""
    log = codex.log_path(answer)
    schema = codex.schema_path(answer)
    try:
        schema.parent.mkdir(parents=True, exist_ok=True)
        schema.write_text(json.dumps(Answer.model_json_schema(), indent=1), encoding="utf-8")
    except OSError as error:
        return dead(name, [], f"the answer's schema could not be written beside it: {error}", None)
    try:
        argv = codex.resume_argv(session.session_id, brief=brief, answer=answer, schema=str(schema))
    except machine.CommandMissing as missing:
        return dead(name, [], str(missing), None)
    since = time.time()
    try:
        pid = machine.detach(argv, cwd=session.cwd or ".", log=log)
    except OSError as error:
        return dead(name, [], f"`codex exec resume` could not run: {error}", None)
    born = machine.process_start(pid)
    while True:
        elapsed = time.time() - since
        if not machine.process_alive(pid, born):
            if _answered(answer, since):
                attempt = Attempt(
                    rung=CODEX_RUNG,
                    verdict=LaunchVerdict.ALIVE,
                    short_id=session.short_id,
                    reason=f"answered within {elapsed:.1f} s",
                    seconds=round(elapsed, 2),
                )
                return Launch(
                    card=name,
                    verdict=LaunchVerdict.ALIVE,
                    session=_codex_row(session),
                    placement=None,
                    scope=None,
                    attempts=[attempt],
                    reason=f"already answered, {elapsed:.1f} s after the call",
                )
            words = _last_words(log)
            reason = (
                f"`codex exec resume` ended {elapsed:.1f} s after the call without an answer"
                + (f": {words}" if words else "")
            )
            attempt = Attempt(
                rung=CODEX_RUNG,
                verdict=LaunchVerdict.DEAD,
                short_id=session.short_id,
                reason=reason,
                seconds=round(elapsed, 2),
            )
            return dead(name, [attempt], reason, None)
        if elapsed >= OBSERVATION_SECONDS:
            break
        time.sleep(POLL_SECONDS)
    unit = lane_unit(name)
    try:
        asked, words = machine.adopt(
            unit, [pid, *machine.descendants_of(pid)], memory_high=MEMORY_FLOOR_BYTES
        )
    except machine.CommandMissing as missing:
        asked, words = False, str(missing)
    scoped = asked and _in_scope(pid, unit)
    store.record_session_slot(
        SessionSlot(
            session_id=session.session_id,
            slot=codex.SLOT,
            card=name,
            scope=unit,
            recorded_at=clock.now(),
        )
    )
    attempt = Attempt(
        rung=CODEX_RUNG,
        verdict=LaunchVerdict.ALIVE,
        short_id=session.short_id,
        reason=None,
        seconds=round(time.time() - since, 2),
    )
    return Launch(
        card=name,
        verdict=LaunchVerdict.ALIVE,
        session=_codex_row(session),
        placement=None,
        scope=unit if scoped else None,
        attempts=[attempt],
        reason=None if scoped else f"running, but not in its own space on the machine: {words}",
    )


ASK_SECONDS = CODEX_LANE_SECONDS
"""How long a fresh Codex thread's process must live before the ask is
called alive: the lane's window, for the lane's reason — a fresh `codex
exec` writes its rollout after it has authenticated and loaded the
doctrine chain."""


def ask_codex(
    store: Store,
    *,
    cwd: str,
    name: str,
    brief: str,
    answer: str,
    schema: str,
    effort: Gate,
) -> Launch:
    """Ask a colleague of the other make in a fresh thread (card #87): a
    cold reading with no share of any earlier thread's context, held to
    the answer's own schema, sandboxed read-only in the project's
    checkout, and verified the way a called worker is — the process is
    there past the observation window, or it ended and said why, or it
    ended with the answer written, which is a fast reply.

    Why a fresh thread and not `call`: a call resumes the slot's most
    recent thread (`call_codex`), which is the right shape for a colleague
    with the thread in its head and the wrong one for a reading whose
    worth is its independence (the plan's ruling of 2026-09-09). `schema`
    is the JSON schema Codex holds the last message to, written by the
    caller beside the answer."""
    if not brief.strip():
        return dead(name, [], "an empty brief asks nobody", None)
    log = codex.log_path(answer)
    try:
        argv = codex.ask_argv(cwd, brief=brief, answer=answer, schema=schema, effort=effort)
    except machine.CommandMissing as missing:
        return dead(name, [], str(missing), None)
    since = time.time()
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
        pid = machine.detach(argv, cwd=cwd, log=log)
    except OSError as error:
        return dead(name, [], f"`codex exec` could not run: {error}", None)
    born = machine.process_start(pid)
    while True:
        elapsed = time.time() - since
        if not machine.process_alive(pid, born):
            session = codex.fresh_since(cwd, since)
            if _answered(answer, since):
                attempt = Attempt(
                    rung=CODEX_RUNG,
                    verdict=LaunchVerdict.ALIVE,
                    short_id=session.short_id if session else None,
                    reason=f"answered within {elapsed:.1f} s",
                    seconds=round(elapsed, 2),
                )
                return Launch(
                    card=name,
                    verdict=LaunchVerdict.ALIVE,
                    session=session,
                    placement=None,
                    scope=None,
                    attempts=[attempt],
                    reason=f"already answered, {elapsed:.1f} s after the ask",
                )
            words = _last_words(log)
            reason = f"`codex exec` ended {elapsed:.1f} s after the ask without an answer" + (
                f": {words}" if words else ""
            )
            attempt = Attempt(
                rung=CODEX_RUNG,
                verdict=LaunchVerdict.DEAD,
                short_id=session.short_id if session else None,
                reason=reason,
                seconds=round(elapsed, 2),
            )
            return dead(name, [attempt], reason, None)
        if elapsed >= ASK_SECONDS:
            break
        time.sleep(POLL_SECONDS)
    session = _codex_lane_row(pid, cwd) or codex.fresh_since(cwd, since)
    if session is None:
        machine.terminate(pid)
        return dead(
            name,
            [],
            f"the process lived {time.time() - since:.1f} s but wrote no session of its own in "
            f"{machine.codex_sessions_root()}, so the board has nothing to follow",
            None,
        )
    unit = lane_unit(name)
    try:
        asked, words = machine.adopt(unit, [pid, *machine.descendants_of(pid)])
    except machine.CommandMissing as missing:
        asked, words = False, str(missing)
    scoped = asked and _in_scope(pid, unit)
    store.record_session_slot(
        SessionSlot(
            session_id=session.session_id,
            slot=codex.SLOT,
            card=name,
            scope=unit,
            recorded_at=clock.now(),
        )
    )
    attempt = Attempt(
        rung=CODEX_RUNG,
        verdict=LaunchVerdict.ALIVE,
        short_id=session.short_id,
        reason=None,
        seconds=round(time.time() - since, 2),
    )
    return Launch(
        card=name,
        verdict=LaunchVerdict.ALIVE,
        session=session,
        placement=None,
        scope=unit if scoped else None,
        attempts=[attempt],
        reason=None if scoped else f"running, but not in its own space on the machine: {words}",
    )


def _codex_row(session: Session) -> Session:
    """The worker's row as the one list reads it now, with its process."""
    rows = codex.find(session.session_id)
    return rows[0] if rows else session


def _answered(answer: str, since: float) -> bool:
    try:
        stat = Path(answer).stat()
    except OSError:
        return False
    return stat.st_size > 0 and stat.st_mtime >= since


def _last_words(log: Path) -> str:
    try:
        lines = [
            line.strip()
            for line in log.read_text(encoding="utf-8", errors="replace").splitlines()
            if line.strip()
        ]
    except OSError:
        return ""
    return _ANSI.sub("", lines[-1])[:300] if lines else ""


def resume_transcript(store: Store, session_id: str, cwd: str, *, brief: str, name: str) -> Launch:
    """Resume a session no registry holds any more, from its transcript by
    id: the argv `move` builds, on the rung the rule names, verified the
    same way (plan 17, item 1). A colleague whose process has ended has no
    row, and a call to it is this."""
    if not brief.strip():
        return dead(name, [], "an empty brief calls nobody; provide a note or an objective", None)
    where = rule.where(None, [], cached=False)
    if where.placement is None:
        return dead(name, [], where.reason, None)
    placement = where.placement
    size = machine.transcript_size(cwd, session_id)
    if size is not None and size > RESUME_SIZE_LIMIT:
        return dead(
            name,
            [],
            f"the transcript of {session_id.split('-')[0]} is {size / 1048576:.1f} MB, above the "
            f"{RESUME_SIZE_LIMIT // 1048576} MB the runtime resumes; start a fresh session with "
            "the note instead",
            placement,
        )
    argv = argv_for(
        placement, effort=None, name=name, prompt=brief, resume=session_id, worktree=None
    )
    short, words, since = _launch(placement, argv, Path(cwd))
    attempts: list[Attempt] = []
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
        return dead(name, attempts, words, placement)
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
    if verified.verdict != LaunchVerdict.ALIVE:
        if verified.verdict == LaunchVerdict.DEAD:
            _stop_probe(placement, short, verified.pid)
        return Launch(
            card=name,
            verdict=verified.verdict,
            session=_row(placement, short)
            if verified.verdict == LaunchVerdict.UNCONFIRMED
            else None,
            placement=placement,
            scope=None,
            attempts=attempts,
            reason=verified.reason,
        )
    return _settle(store, placement, short, verified, name, attempts)
