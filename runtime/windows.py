"""A window into any session, proved by the compositor and never closed by us.

A window is opened detached through Omarchy's launcher, whose exit code says
nothing (it ends in `setsid`), so the proof is one more window under the
app-id than before, read from `hyprctl clients -j` within a deadline. A live
session is always attached (`claude attach`), so closing the window ends only
the viewer; a session live nowhere gets a fresh session in its worktree from
its transcript, and the window's first line says so. The runtime records the
windows it opened and notices when the owner closes one; it never closes one
itself and never opens a second for a session that has one.
"""

import json
import re
import shlex
import time

from domain.gate import Gate
from domain.machine import Machine
from domain.session import Session, SessionKind
from domain.slot import Placement, rung_words
from domain.window import Focused, Opened, WindowKind
from infrastructure import clock
from infrastructure.store import Store
from runtime import launch, machine
from runtime.launch import PROMPTS_SETTLED

WINDOW_VERIFY_SECONDS = 8.0
"""A window appeared in 0.3 s on 2026-09-04; eight is generous for a busy machine."""
WINDOW_POLL_SECONDS = 0.3
FOCUS_VERIFY_SECONDS = 3.0
"""Focus lands within a frame; three seconds covers a workspace switch."""
APP_ID_PREFIX = "org.omarchy."
"""The owner's contract: `org.omarchy.<kind>-<card>`, routed by his compositor rule."""


class WindowRefused(Exception):
    """No window was opened; the message says why, by name."""


def _hyprctl(args: list[str], host: str | None) -> machine.Completed:
    """Ask the compositor here, or on the desktop machine when the board runs
    elsewhere (card #83): the command is resolved here only when it runs
    here — on the other machine its own shell finds it."""
    argv = [machine.which("hyprctl") if host is None else "hyprctl", *args]
    return machine.run(argv, timeout=10, host=host)


def clients(host: str | None = None) -> list[dict[str, object]]:
    try:
        done = _hyprctl(["clients", "-j"], host)
    except (OSError, machine.CommandMissing, machine.Unreachable) as error:
        raise WindowRefused(f"the compositor cannot be asked: {error}") from error
    if done.returncode != 0:
        raise WindowRefused(f"`hyprctl clients` failed: {done.stderr.strip()[:200]}")
    try:
        blob = json.loads(done.stdout or "[]")
    except json.JSONDecodeError as error:
        raise WindowRefused("`hyprctl clients -j` did not answer with JSON") from error
    return [c for c in blob if isinstance(c, dict)] if isinstance(blob, list) else []


def present(app_id: str, host: str | None = None) -> dict[str, dict[str, object]]:
    """Address → client, for every window carrying the app-id right now."""
    return {
        str(c.get("address")): c
        for c in clients(host)
        if c.get("class") == app_id or c.get("initialClass") == app_id
    }


def present_under(prefix: str, host: str | None = None) -> dict[str, dict[str, object]]:
    """Address → client, for every window whose app-id starts with `prefix`:
    the board's own Chromium windows, whichever project each shows (card #41)."""
    return {
        str(c.get("address")): c
        for c in clients(host)
        if str(c.get("class") or c.get("initialClass") or "").startswith(prefix)
    }


def active(host: str | None = None) -> dict[str, object]:
    """The window the compositor reports focused, or an empty dict when none."""
    try:
        done = _hyprctl(["activewindow", "-j"], host)
    except (OSError, machine.CommandMissing, machine.Unreachable) as error:
        raise WindowRefused(f"the compositor cannot be asked: {error}") from error
    if done.returncode != 0:
        raise WindowRefused(f"`hyprctl activewindow` failed: {done.stderr.strip()[:200]}")
    try:
        blob = json.loads(done.stdout or "{}")
    except json.JSONDecodeError as error:
        raise WindowRefused("`hyprctl activewindow -j` did not answer with JSON") from error
    return blob if isinstance(blob, dict) else {}


def focus_script(address: str) -> str:
    """Hyprland here runs a Lua config, and `hyprctl dispatch` takes Lua
    (verified 2026-09-04): the window is looked up by address and focused
    through `hl.dsp.focus`; a missing window is an `error()`, the one way
    `hyprctl eval` says anything but `ok`."""
    safe = re.sub(r"[^0-9A-Za-z]", "", address)
    return (
        f"local w = hl.get_window('address:{safe}'); "
        f"if not w then error('no window at {safe}') end; "
        "hl.dispatch(hl.dsp.focus({window = w}))"
    )


def focus_address(address: str, app_id: str = "the window", *, host: str | None = None) -> str:
    """Bring the window at `address` forward and prove it by the compositor's
    active window carrying that address; answers the app-id the compositor
    reports. The one focus, for a session's window and for the board's own
    (card #41)."""
    try:
        done = _hyprctl(["eval", focus_script(address)], host)
    except (OSError, machine.CommandMissing, machine.Unreachable) as error:
        raise WindowRefused(f"the compositor cannot be asked: {error}") from error
    if done.returncode != 0 or "error" in done.stdout.lower():
        raise WindowRefused(
            f"the compositor refused to focus {app_id} ({address}): "
            f"{(done.stderr or done.stdout).strip()[:200]}"
        )
    deadline = time.time() + FOCUS_VERIFY_SECONDS
    while time.time() < deadline:
        now = active(host)
        if str(now.get("address")) == address:
            return str(now.get("class") or app_id)
        time.sleep(WINDOW_POLL_SECONDS)
    raise WindowRefused(
        f"{app_id} ({address}) was told to focus and the compositor still "
        f"reports {active(host).get('class') or 'no window'} active after "
        f"{FOCUS_VERIFY_SECONDS:.0f} s"
    )


def focus_window(store: Store, session: Session, *, host: str | None = None) -> Focused:
    """Bring the session's open window forward and prove it by the
    compositor's active window carrying its address."""
    reconcile(store, host=host)
    open_windows = store.windows(session.session_id, open_only=True)
    if not open_windows:
        raise WindowRefused(f"no window is open into {session.short_id}; open one first")
    window = open_windows[0]
    return Focused(window=window, app_id=focus_address(window.address, window.app_id, host=host))


def app_id_for(kind: WindowKind, card: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", card).strip("-") or "unnamed"
    return f"{APP_ID_PREFIX}{kind.value}-{safe}"


def reconcile(store: Store, *, host: str | None = None) -> None:
    """Windows the runtime recorded open that the compositor no longer has
    were closed by the owner; record the close so they are never reopened."""
    addresses = {str(c.get("address")) for c in clients(host)}
    for window in store.windows(open_only=True):
        if window.address not in addresses:
            store.window_closed(window.id, clock.now())


def attach_command(session: Session) -> str:
    return (
        f"CLAUDE_CONFIG_DIR={shlex.quote(session.config_dir)} "
        f"CLAUDE_ACCOUNT={shlex.quote(session.slot)} "
        f"exec claude attach {shlex.quote(session.short_id)}"
    )


TMUX_PREFIX = "needle-"
"""The multiplexer session on the other machine carries the window's own
name, so the proof reads the same word the compositor's app-id carries."""


def tmux_name(kind: WindowKind, card: str) -> str:
    return TMUX_PREFIX + app_id_for(kind, card)[len(APP_ID_PREFIX) :]


def via_tmux(via: Machine, name: str, command: str) -> str:
    """The desktop's terminal command for a session on another machine
    (card #83, item 4): `ssh -t` to that machine and, there, attach to — or
    make — the multiplexer session named for the window, running `command`
    inside it. The multiplexer is what makes the tunnel's drop a viewer's
    end and never the session's: a laptop that sleeps loses the terminal,
    and `-A` gives it the same session back. Quoted twice on purpose: once
    for the other machine's shell, which `ssh` hands the line to whole, and
    once for the desktop's, which reads the launcher's `bash -lc` string."""
    if via.host is None:
        raise WindowRefused(f"{via.name} has no host the desktop can reach it by")
    remote = shlex.join(["tmux", "new-session", "-A", "-s", name, "bash", "-lc", command])
    return f"exec ssh -t {shlex.quote(via.host)} -- {shlex.quote(remote)}"


def tmux_has(host: str, name: str) -> bool:
    """The multiplexer's word on the other machine: whether the session
    named exists there right now (`tmux has-session -t`, exit 0)."""
    try:
        done = machine.run(["tmux", "has-session", "-t", f"={name}"], timeout=15, host=host)
    except (OSError, machine.Unreachable, machine.Timeout):
        return False
    return done.returncode == 0


def _prove_attached(proof: str, deadline: float) -> None:
    """The second half of a remote window's proof: the multiplexer on the
    other machine holds the session the terminal attached to. `proof` is
    `<host>\\t<name>`; a window that appeared with nothing behind it on the
    other machine is refused by that name."""
    host, name = proof.split("\t", 1)
    while time.time() < deadline:
        if tmux_has(host, name):
            return
        time.sleep(WINDOW_POLL_SECONDS)
    raise WindowRefused(
        f"the terminal opened but {host} holds no multiplexer session {name} "
        f"within {WINDOW_VERIFY_SECONDS:.0f} s"
    )


def look_command(session: Session, placement: Placement) -> tuple[str, str]:
    """A fresh session in the worktree with the transcript as context, and
    the banner that is its first line. Above the resume limit the transcript
    is named in the brief rather than loaded."""
    home = session.worktree or session.cwd
    size = machine.transcript_size(home, session.session_id)
    banner = (
        f"Fresh session from the transcript of {session.short_id} ({session.name}) — "
        f"{rung_words(placement.model, placement.slot)}. Closing this "
        f"window ends this session and nothing else."
    )
    parts = ["claude", *(["--model", placement.model] if placement.model else [])]
    if session.effort is not None:
        parts += ["--effort", session.effort.value]
    parts += list(PROMPTS_SETTLED)
    if size is not None and size > launch.RESUME_SIZE_LIMIT:
        limit = launch.RESUME_SIZE_LIMIT // 1048576
        banner += (
            f" The transcript is {size / 1048576:.1f} MB, above the "
            f"{limit} MB the runtime loads, so it is named, not loaded."
        )
        parts.append(launch.fresh_brief(session, size))
    else:
        parts += ["--resume", session.session_id, "--fork-session"]
    command = (
        f"cd {shlex.quote(home)} && printf '%s\\n\\n' {shlex.quote(banner)} && "
        f"CLAUDE_CONFIG_DIR={shlex.quote(placement.config_dir)} "
        f"CLAUDE_ACCOUNT={shlex.quote(placement.slot)} exec "
        + " ".join(shlex.quote(p) for p in parts)
    )
    return banner, command


def discuss_command(
    placement: Placement, *, cwd: str, session_id: str, brief: str, effort: Gate | None, what: str
) -> tuple[str, str]:
    """A fresh conversation in the project root, on the slot and model the
    rule chose, with the card's brief as its first prompt. The session id is
    chosen here so the board can tell the conversation from hands on a tree."""
    banner = (
        f"{what} — {rung_words(placement.model, placement.slot)}. "
        "A conversation, never hands on any tree; closing this window ends only it."
    )
    parts = ["claude", *(["--model", placement.model] if placement.model else [])]
    parts += ["--session-id", session_id]
    if effort is not None:
        parts += ["--effort", effort.value]
    parts += [*PROMPTS_SETTLED, brief]
    command = (
        f"cd {shlex.quote(cwd)} && printf '%s\\n\\n' {shlex.quote(banner)} && "
        f"CLAUDE_CONFIG_DIR={shlex.quote(placement.config_dir)} "
        f"CLAUDE_ACCOUNT={shlex.quote(placement.slot)} exec "
        + " ".join(shlex.quote(p) for p in parts)
    )
    return banner, command


def open_fresh(
    store: Store,
    *,
    session_id: str,
    kind: WindowKind,
    card: str,
    command: str,
    banner: str | None,
    fresh: bool,
    host: str | None = None,
    proof: str | None = None,
) -> Opened:
    """Open a terminal running `command` under the kind's app-id and prove it
    by one more client than before; record it against the session id."""
    app_id = app_id_for(kind, card)
    before = set(present(app_id, host))
    try:
        launcher = machine.which("omarchy-launch-tui") if host is None else "omarchy-launch-tui"
        machine.spawn([launcher, f"--app-id={app_id}", "bash", "-lc", command], host=host)
    except (machine.CommandMissing, machine.Unreachable, OSError) as missing:
        raise WindowRefused(f"the terminal did not open: {missing}") from missing
    deadline = time.time() + WINDOW_VERIFY_SECONDS
    while time.time() < deadline:
        new = [address for address in present(app_id, host) if address not in before]
        if new:
            if proof is not None:
                _prove_attached(proof, deadline)
            window = store.record_window(session_id, kind, app_id, new[0], clock.now())
            return Opened(window=window, fresh=fresh, banner=banner)
        time.sleep(WINDOW_POLL_SECONDS)
    raise WindowRefused(
        f"no window appeared under {app_id} within {WINDOW_VERIFY_SECONDS:.0f} s; "
        "is the desktop session reachable from here?"
    )


def open_window(
    store: Store,
    session: Session,
    *,
    kind: WindowKind | None,
    card: str,
    look: Placement | None,
    host: str | None = None,
    via: Machine | None = None,
) -> Opened:
    """A window into the session on the desktop (`host` when the desktop is
    another machine), attached over the tunnel to a session on `via` when
    the session runs on a machine that is not the desktop (card #83)."""
    reconcile(store, host=host)
    already = store.windows(session.session_id, open_only=True)
    if already:
        window = already[0]
        raise WindowRefused(
            f"{session.short_id} already has a window: {window.app_id} ({window.address}); "
            "close it and call again"
        )
    if session.stale:
        raise WindowRefused(
            f"{session.short_id} on {session.slot} is a stale copy; open the live one"
        )
    if session.pid is not None:
        if session.kind == SessionKind.INTERACTIVE:
            raise WindowRefused(
                f"{session.short_id} runs in a terminal of its own; that terminal is its window"
            )
        kind = kind or WindowKind.LANE
        command, banner, fresh = attach_command(session), None, False
        if via is not None:
            command = via_tmux(via, tmux_name(kind, card), command)
    else:
        if look is None:
            raise WindowRefused(
                f"{session.short_id} is live nowhere and the rule found no slot for a fresh session"
            )
        kind = kind or WindowKind.LOOK
        banner, command = look_command(session, look)
        fresh = True
        if via is not None:
            command = via_tmux(via, tmux_name(kind, card), command)
    return open_fresh(
        store,
        session_id=session.session_id,
        kind=kind,
        card=card,
        command=command,
        banner=banner,
        fresh=fresh,
        host=host,
        proof=None if via is None else f"{via.host}\t{tmux_name(kind, card)}",
    )
