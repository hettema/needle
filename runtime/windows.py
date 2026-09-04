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

from domain.session import Session, SessionKind
from domain.slot import Placement
from domain.window import Opened, WindowKind
from infrastructure import clock
from infrastructure.store import Store
from runtime import launch, machine
from runtime.launch import PROMPTS_SETTLED

WINDOW_VERIFY_SECONDS = 8.0
"""A window appeared in 0.3 s on 2026-09-04; eight is generous for a busy machine."""
WINDOW_POLL_SECONDS = 0.3
APP_ID_PREFIX = "org.omarchy."
"""The owner's contract: `org.omarchy.<kind>-<card>`, routed by his compositor rule."""


class WindowRefused(Exception):
    """No window was opened; the message says why, by name."""


def clients() -> list[dict[str, object]]:
    try:
        done = machine.run([machine.which("hyprctl"), "clients", "-j"], timeout=10)
    except (OSError, machine.CommandMissing) as error:
        raise WindowRefused(f"the compositor cannot be asked: {error}") from error
    if done.returncode != 0:
        raise WindowRefused(f"`hyprctl clients` failed: {done.stderr.strip()[:200]}")
    try:
        blob = json.loads(done.stdout or "[]")
    except json.JSONDecodeError as error:
        raise WindowRefused("`hyprctl clients -j` did not answer with JSON") from error
    return [c for c in blob if isinstance(c, dict)] if isinstance(blob, list) else []


def present(app_id: str) -> dict[str, dict[str, object]]:
    """Address → client, for every window carrying the app-id right now."""
    return {
        str(c.get("address")): c
        for c in clients()
        if c.get("class") == app_id or c.get("initialClass") == app_id
    }


def app_id_for(kind: WindowKind, card: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", card).strip("-") or "unnamed"
    return f"{APP_ID_PREFIX}{kind.value}-{safe}"


def reconcile(store: Store) -> None:
    """Windows the runtime recorded open that the compositor no longer has
    were closed by the owner; record the close so they are never reopened."""
    addresses = {str(c.get("address")) for c in clients()}
    for window in store.windows(open_only=True):
        if window.address not in addresses:
            store.window_closed(window.id, clock.now())


def attach_command(session: Session) -> str:
    return (
        f"CLAUDE_CONFIG_DIR={shlex.quote(session.config_dir)} "
        f"CLAUDE_ACCOUNT={shlex.quote(session.slot)} "
        f"exec claude attach {shlex.quote(session.short_id)}"
    )


def look_command(session: Session, placement: Placement) -> tuple[str, str]:
    """A fresh session in the worktree with the transcript as context, and
    the banner that is its first line. Above the resume limit the transcript
    is named in the brief rather than loaded."""
    home = session.worktree or session.cwd
    size = machine.transcript_size(home, session.session_id)
    banner = (
        f"Fresh session from the transcript of {session.short_id} ({session.name}) — "
        f"{placement.model.value} on the {placement.slot} subscription. Closing this "
        f"window ends this session and nothing else."
    )
    parts = ["claude", "--model", placement.model.value]
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


def open_window(
    store: Store,
    session: Session,
    *,
    kind: WindowKind | None,
    card: str,
    look: Placement | None,
) -> Opened:
    reconcile(store)
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
    else:
        if look is None:
            raise WindowRefused(
                f"{session.short_id} is live nowhere and the rule found no slot for a fresh session"
            )
        kind = kind or WindowKind.LOOK
        banner, command = look_command(session, look)
        fresh = True
    app_id = app_id_for(kind, card)
    before = set(present(app_id))
    try:
        launcher = machine.which("omarchy-launch-tui")
    except machine.CommandMissing as missing:
        raise WindowRefused(f"the terminal did not open: {missing}") from missing
    machine.spawn([launcher, f"--app-id={app_id}", "bash", "-lc", command])
    deadline = time.time() + WINDOW_VERIFY_SECONDS
    while time.time() < deadline:
        new = [address for address in present(app_id) if address not in before]
        if new:
            window = store.record_window(session.session_id, kind, app_id, new[0], clock.now())
            return Opened(window=window, fresh=fresh, banner=banner)
        time.sleep(WINDOW_POLL_SECONDS)
    raise WindowRefused(
        f"no window appeared under {app_id} within {WINDOW_VERIFY_SECONDS:.0f} s; "
        "is the desktop session reachable from here?"
    )
