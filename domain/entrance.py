"""What a session started in a project will read as its constitution.

A project on the board is built the way `docs/HOW-WE-WORK.md` describes. Whether
the sessions that work it ever *see* that text is a fact about the machine they
run on, not about the project: a colleague reads the file its provider injects
(`~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`), and until that file resolves to
this repository's HOW-WE-WORK there are two texts and the second one wins.

The board says which, and never refuses: a project on a machine with no entrance
is still a project on the board (plan 18, ruling 5). The word is a finding for
the person to act on, and the machine's own card is where the acting happens.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class EntranceWord(StrEnum):
    ONE_TEXT = "one-text"
    """Every injected file resolves to this project's HOW-WE-WORK. A session of
    any make on this machine starts with the one text in front of it."""
    TWO_TEXTS = "two-texts"
    """An injected file exists and resolves somewhere else. Sessions here obey a
    second doctrine, and drift between the two is held by nothing."""
    NONE = "none"
    """An injected file is missing. Sessions here enter with no doctrine at all."""


class InjectedFile(BaseModel):
    """One file a provider puts in front of every session, and where it leads."""

    path: str
    """The injected path as the provider names it, e.g. `~/.claude/CLAUDE.md`."""
    resolves_to: str | None
    """What it is after every link is followed; None when it does not exist."""
    is_the_one_text: bool


class Entrance(BaseModel):
    """The board's reading of a machine's doctrine delivery, at a moment."""

    word: EntranceWord
    line: str
    """The whole sentence as `needle add` prints it, kept so the board shows the
    same words the person read at the door."""
    files: list[InjectedFile]
    read_at: datetime
