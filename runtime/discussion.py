"""The machine's watercooler, read: the notes in the discussion directory.

Sessions of any make on this laptop talk through files there (the
machine's CLAUDE.md, "Sessions on this machine"); until plan 17 nothing
delivered a note, and a chair polled a terminal every thirty seconds to
learn one had landed. The board reads the directory — a stat per file and
the first line of each — and never writes into it (plan 17, ruling 3).
"""

import re
from datetime import UTC, datetime
from pathlib import Path

from domain.watercooler import Note
from runtime import machine

_NAMED_NOTE = re.compile(r"discussion/([A-Za-z0-9._-]+\.md)\b")
"""How a document names a note on the machine's watercooler: any path that
ends in `discussion/<file>.md`, home-relative or absolute."""


def notes() -> list[Note]:
    """Every note in the directory, oldest change first."""
    directory = machine.discussion_dir()
    found: list[Note] = []
    try:
        paths = sorted(p for p in directory.iterdir() if p.suffix == ".md" and p.is_file())
    except OSError:
        return found
    for path in paths:
        note = note_of(path)
        if note is not None:
            found.append(note)
    return sorted(found, key=lambda n: n.at)


def note_of(path: Path) -> Note | None:
    """One note as it stands, or None when it cannot be read."""
    try:
        stamp = path.stat().st_mtime
        with path.open(encoding="utf-8", errors="replace") as f:
            first = f.readline().strip()
    except OSError:
        return None
    return Note(path=str(path), first_line=first, at=datetime.fromtimestamp(stamp, UTC))


def named_in(text: str) -> set[str]:
    """The notes a document names, as paths in the directory: a lane whose
    card names a note is party to that discussion (plan 17, item 2)."""
    directory = machine.discussion_dir()
    return {str(directory / name) for name in _NAMED_NOTE.findall(text)}


def in_directory(path: str) -> bool:
    try:
        return Path(path).parent.resolve() == machine.discussion_dir().resolve()
    except OSError:
        return False
