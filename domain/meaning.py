"""The colour language's five words, and the one shape every sentence on a
card takes (plan 27; card #75).

A card is the owner's surface for two things: what this is, and whether it
needs him. The colour answered the second from plan 27 on — amber is "only
you can act", teal "happening now", grey "nothing for you" — and the sentence
beneath it was written from the machine's side ("Start waits on the plan's
own word: its Sequencing names #20 …"), so on 2026-09-07 he read a held card
and asked whether there was something he had to do. The colour and the
sentence say the same thing now, because a sentence is built here from its
meaning and its parts and never as free text: the opening is the meaning's
own words, then his part or the fact, then the plain reason, then what
happens without him. A model that carries a sentence refuses one whose
opening is not its meaning's (`domain.board.CardState`) or not an opening at
all (`Door.why`, `Lane.sentence`, `Collision.sentence`), so the colour and
the words cannot disagree on any project's board; the words themselves are
read against `docs/vocabulary.md` by a ratchet.
"""

from enum import StrEnum


class Meaning(StrEnum):
    """The colour language's five words (plan 27). Every colour on the board
    says one of these and nothing else; the page paints a meaning, never a
    count, a category, a button or a column."""

    YOURS = "yours"
    """Amber: only you can act."""
    BROKEN = "broken"
    """Red: evidence is gone or two things disagree."""
    LIVE = "live"
    """Teal: happening right now."""
    PROVEN = "proven"
    """Green: the loop closed."""
    QUIET = "quiet"
    """Grey: information with no claim on you."""


OPENING: dict[Meaning, str] = {
    Meaning.YOURS: "Your move",
    Meaning.BROKEN: "Something is wrong",
    Meaning.LIVE: "Happening now",
    Meaning.PROVEN: "Proven",
    Meaning.QUIET: "Nothing for you",
}
"""How a sentence in each meaning opens: his part first, in the words the
colour already says. One opening per meaning, and the page reads the same
map for the sentences it writes itself (the column note, the head's
tooltips)."""

_CLOSERS = ".!?"
_QUOTES = "”\"'"


def _clause(text: str) -> str:
    """One part of a sentence, ending in a full stop unless it already
    closes — a quoted question keeps its mark inside the quote."""
    text = text.strip()
    if not text:
        return text
    last = text[-1]
    if last in _CLOSERS or (last in _QUOTES and len(text) > 1 and text[-2] in _CLOSERS):
        return text
    return text + "."


def say(meaning: Meaning, what: str, *, why: str | None = None, then: str | None = None) -> str:
    """The one shape: `<opening>: <what>. <why>. <then>.` — `what` is his part
    on an amber face and the plain fact on every other; `why` the reason in
    his words; `then` what happens without him, or what it takes from him
    when nothing does. A caller hands in parts, never a sentence, so the
    opening cannot be wrong for the colour."""
    parts = [_clause(f"{OPENING[meaning]}: {what.strip()}")]
    for part in (why, then):
        if part and part.strip():
            part = part.strip()
            parts.append(_clause(part[0].upper() + part[1:]))
    return " ".join(parts)


def opening_of(text: str) -> Meaning | None:
    """Which meaning a sentence opens with, or None when it opens with none of
    the five — the check every sentence-carrying model runs at construction."""
    for meaning, opening in OPENING.items():
        if text.startswith(f"{opening}:"):
            return meaning
    return None


def opened(text: str, field: str) -> str:
    """Refuse a sentence that opens with none of the five; answer it unchanged."""
    if opening_of(text) is None:
        raise ValueError(
            f"{field} must open with one of {list(OPENING.values())}, built through "
            f"domain.meaning.say; got {text!r}"
        )
    return text
