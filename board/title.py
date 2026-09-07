"""The words a card title never uses, read from the one file that lists them
(card #74, item 1).

The owner ranks cards from their titles alone, and on 2026-09-07 nineteen
of Needle's twenty-eight live titles used a word the board or the code
defines and he does not. The rule was written (`docs/plans/README.md`, the
title rule) and held by nothing. What holds it now is two readers of one
list: the ratchet that refuses a live title on Needle's own board, and the
brief of the reading that judges a title at its birth on every board. The
list lives in `docs/vocabulary.md` and neither reader carries a copy, so a
word added there is refused and read against in the same commit.

The list is the floor, not the test. A title can avoid every word and still
say nothing he can place; the cold read applies his test, and this module
only answers the cheap question — which listed words a title contains — so
that failure is loud where it is cheap.
"""

import re
from pathlib import Path

from pydantic import BaseModel

from board.triage import fingerprint
from domain.document import Document
from domain.triage import TitleReading, TitleVerdict

REPO_ROOT = Path(__file__).resolve().parent.parent
VOCABULARY_PATH = REPO_ROOT / "docs" / "vocabulary.md"
VOCABULARY = "docs/vocabulary.md"
"""How the briefs name the file: relative to Needle's checkout, which is
where both the ratchet and the board read it."""

_ENTRY = re.compile(r"^- \*\*([^*]+)\*\*\s*—\s*(.*)$")
_SEQUENCE_TITLE = re.compile(r"^\s*\d{1,3}\s*[—–-]\s")
_SEQUENCE_STEM = re.compile(r"^\d{4}-\d{2}-\d{2}-(\d{1,3})-")
_NOUN_BEFORE_MAKE = re.compile(
    r"\b(?:its|a|an|either|another|any|one|the|same|other|each|every|that|this|of|his|their)"
    r"\s+makes?\b",
    re.I,
)


class Word(BaseModel):
    """One line of the vocabulary: the word, and what the board means by it
    with the plain words to use instead."""

    word: str
    meaning: str


def vocabulary_of(text: str) -> list[Word]:
    """The list as the file carries it: one `- **word** — meaning` line per
    word, in file order. Prose between the lines is the rule's why and is
    not a word."""
    words: list[Word] = []
    for line in text.splitlines():
        match = _ENTRY.match(line.strip())
        if match:
            words.append(Word(word=match.group(1).strip().lower(), meaning=match.group(2).strip()))
    return words


def read_vocabulary(path: Path = VOCABULARY_PATH) -> list[Word]:
    return vocabulary_of(path.read_text(encoding="utf-8"))


def _pattern(word: str) -> re.Pattern[str]:
    # Whole words, either number: a title that says "lanes" is about lanes.
    # Possessives too ("a lane's plan"): the apostrophe is not a letter, so
    # the word boundary already falls before it.
    return re.compile(rf"\b{re.escape(word)}(?:s|es)?\b", re.I)


def jargon_in(title: str, words: list[Word]) -> list[str]:
    """The listed words this title uses, each once, in the list's order.
    "make" is read only where it is the noun the board defines ("its make",
    "another make"): the verb is the owner's own word and a title that
    makes something true is what the rule asks for."""
    found: list[str] = []
    for entry in words:
        if entry.word == "make":
            if _NOUN_BEFORE_MAKE.search(title):
                found.append("make")
            continue
        if _pattern(entry.word).search(title):
            found.append(entry.word)
    return found


def sequence_number_in(title: str, stem: str) -> str | None:
    """The sequence number a plan carries in its title ("08 — …") or its
    stem (`2026-09-05-08-…`), if it carries one: the second identifier the
    owner's ruling of 2026-09-07 retires (card #74, item 5) — the card's
    number is the one he sees, and a plan is cited by its card."""
    if _SEQUENCE_TITLE.match(title):
        return f"title begins {title.split()[0]!r}"
    stem_match = _SEQUENCE_STEM.match(stem)
    if stem_match:
        return f"stem carries {stem_match.group(1)!r} after its date"
    return None


# ── the cold read at birth (item 3) ─────────────────────────────────────


def title_fingerprint(title: str, essence: str | None) -> str:
    """What a title reading binds itself to: the title and the line
    beneath it, which is all the reader judged. Not the whole document — a
    body edited under a passing title is not a new title, and a reading
    costs a session."""
    return fingerprint(f"{title}\n{essence or ''}")


def wants_title_reading(document: Document | None, latest: TitleReading | None) -> bool:
    """Whether a card's title has not been read as it stands: no reading
    yet, or the title or essence changed under the last one. A reading
    that failed and a title that has not changed is not read again — the
    writer rewrites, and the reader reads again."""
    if document is None or document.archived:
        return False
    if latest is None:
        return True
    return latest.title_fingerprint != title_fingerprint(document.title, document.essence)


def title_hold(latest: TitleReading | None, document: Document | None) -> str | None:
    """Why Start is closed on this title, or None. The hold is the last
    reading's verdict, not the fingerprint: a title rewritten after a
    failing read stays held until a reading of the new title passes, so a
    rewrite is never its own verification (the reader marks, the writer
    writes, and the reader reads again)."""
    if latest is None or latest.verdict != TitleVerdict.UNPLACEABLE:
        return None
    changed = (
        document is not None
        and not document.archived
        and latest.title_fingerprint != title_fingerprint(document.title, document.essence)
    )
    failed = f" — the words that failed: {', '.join(latest.failed)}" if latest.failed else ""
    tail = (
        "; the title has changed since, and Start opens when a reading of the new title passes"
        if changed
        else "; Start opens when a reading of a rewritten title passes"
    )
    return f"A cold reading could not place this card from its title: {latest.words}{failed}{tail}"
