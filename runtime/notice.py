"""The one door that interrupts the owner (card #41): a notice on his
screen that stays until he dismisses it, a sound, and a button that puts
the card in front of him.

The only module that names `notify-send` and `pw-play`. The notifier
blocks until the notification is answered or dismissed — that block is the
popup staying on screen (the machine's account watcher, omarchy plan 08) —
so the whole thing runs in a shell of its own that the runtime never waits
on: the sound, the notifier, and, if the button was pressed, the command
that shows the card. What the runtime can know is whether it could hand
the notice to the machine; a notifier that refuses after that is the
shell's, and the record says the notice was raised, not seen.
"""

import re
import shlex
from pathlib import Path

from pydantic import BaseModel

from domain.notice import Moment, Notice, Told
from runtime import machine, windows

APP_NAME = "notify-send"
"""The app name the machine's notifier lets through while the owner has
do-not-disturb on: `urgency=critical` and this name is its one channel
for alerts that cannot wait (the shell's own rule, read in
`/usr/share/omarchy/shell/plugins/notifications/NotificationLogic.js` on
2026-09-09, when a notice sent as "Needle" was closed by the notifier in
six milliseconds and filed to history unseen). The ring is that class by
the plan's own intent — the moment the board needs his hand — so it goes
through; the popup names Needle in its summary instead."""
ACTION = "default"
"""The one action the notifier invokes: it draws no buttons, and a click
on the popup runs the action whose identifier is `default` (the shell's
`Service.qml`, read 2026-09-09). The popup is the button."""
BUTTON = "Open the board"
SOUND_DIR = Path("/usr/share/sounds/freedesktop/stereo")
"""The stock freedesktop sounds, present on this machine (verified 2026-09-09)."""
SOUNDS = {Moment.MOVED_ON: "complete.oga", Moment.NEEDS_YOU: "message-new-instant.oga"}
BOARD_APP_ID = "chrome-{host}__p_"
"""How Chromium names an `--app=` window: the URL's host without its port
and its path, `/` written `_`, then the profile
(`chrome-127.0.0.1__p_needle-Profile_5` for `127.0.0.1:8480/p/needle`, the
machine's window rule, verified 2026-09-09). Any window under the prefix is
a board of ours, whatever project it shows: the page switches project
itself."""
_APP_URL = re.compile(r"--app=(?P<base>https?://(?P<host>[^/\s]+))/p/(?P<slug>[A-Za-z0-9_-]+)")


class NoBoardEntry(Exception):
    """No desktop entry opens the board on the project named."""


class BoardEntry(BaseModel):
    """The board's desktop entry for one project, as the machine wrote it."""

    path: str
    argv: list[str]
    """Its Exec line, split as a shell would."""
    base: str
    """The board's origin: `http://127.0.0.1:8480`."""
    host: str


def summary_of(notice: Notice) -> str:
    return f"Needle · {notice.project_name} #{notice.card_number}: {notice.title}"


def tell(notice: Notice, opens: list[str]) -> Told:
    """Raise the notice: `notify-send -u critical -t 0` with one action, and
    the moment's sound beside it; `opens` runs when the button is pressed.
    Answers whether the machine took it and the words the card records."""
    try:
        notifier = machine.which("notify-send")
        player = machine.which("pw-play")
    except machine.CommandMissing as missing:
        return Told(raised=False, words=f"could not tell you: {missing}")
    notify = [
        notifier,
        "-u",
        "critical",
        "-t",
        "0",
        "-a",
        APP_NAME,
        "-A",
        f"{ACTION}={BUTTON}",
        summary_of(notice),
        notice.words,
    ]
    play = [player, str(SOUND_DIR / SOUNDS[notice.moment])]
    script = (
        f"{shlex.join(play)} >/dev/null 2>&1 & "
        f'chosen="$({shlex.join(notify)})"; '
        f'[ "$chosen" = {ACTION} ] && exec {shlex.join(opens)}'
    )
    try:
        machine.spawn(["sh", "-c", script], wait=False)
    except OSError as error:
        return Told(raised=False, words=f"could not tell you: {error}")
    return Told(raised=True, words=notice.words)


def board_entry(slug: str) -> BoardEntry:
    """The desktop entry whose Exec opens the board on the project — the
    machine's own, never written here."""
    folder = machine.applications_dir()
    try:
        entries = sorted(folder.glob("*.desktop"))
    except OSError:
        entries = []
    for path in entries:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in text.splitlines():
            if not line.startswith("Exec="):
                continue
            found = _APP_URL.search(line)
            if found is not None and found.group("slug") == slug:
                return BoardEntry(
                    path=str(path),
                    argv=shlex.split(line[len("Exec=") :]),
                    base=found.group("base"),
                    host=found.group("host"),
                )
    raise NoBoardEntry(f"no desktop entry under {folder} opens the board on {slug}")


def show(slug: str, number: int) -> str:
    """Put the card in front of him: tell the board's server to show it (every
    open page navigates to it), bring a board window forward, and open the
    board's desktop entry on the card's page when no window shows one.
    Answers what was done, in a sentence; raises `NoBoardEntry` or
    `WindowRefused` when it could not be."""
    entry = board_entry(slug)
    url = f"{entry.base}/p/{slug}#card-{number}"
    asked = _ask_board(entry.base, slug, number)
    prefix = BOARD_APP_ID.format(host=entry.host.split(":")[0])
    # The window already on the card's project first — no page has to
    # navigate — else any board of ours, whose page switches project
    # (live on 2026-09-09 the first window under the prefix was another
    # project's while the card's own stood beside it).
    open_boards = windows.present_under(f"{prefix}{slug}-") or windows.present_under(prefix)
    if open_boards:
        address = next(iter(open_boards))
        windows.focus_address(address)
        return f"Showed #{number} on {slug}: {asked}; focused the board's window ({address})."
    argv = [_APP_URL.sub(f"--app={url}", word) for word in entry.argv]
    machine.spawn(argv)
    return f"Showed #{number} on {slug}: {asked}; no board window was open, so {url} was opened."


def _ask_board(base: str, slug: str, number: int) -> str:
    argv = [
        machine.which("curl"),
        "-sS",
        "-m",
        "5",
        "-o",
        "/dev/null",
        "-w",
        "%{http_code}",
        "-X",
        "POST",
        f"{base}/api/show/{slug}/{number}",
    ]
    try:
        done = machine.run(argv, timeout=10)
    except (OSError, machine.Timeout) as error:
        return f"the board could not be asked ({error})"
    lines = done.stdout.strip().splitlines()
    code = lines[-1].strip() if lines else ""
    if done.returncode != 0 or not code.startswith("2"):
        return f"the board could not be asked ({(done.stderr or code).strip()[:120]})"
    return "the board was asked to show it"

