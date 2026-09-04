"""The VERDICT row's grammar, and the classes the board can say by itself.

A verdict is a proposal on a card's own fate (plan 05): the class of evidence
it carries, the evidence in a sentence, and where it should go. The grammar
is small and the parse is lenient about everything but those three:

    VERDICT: <class> — <evidence> → <Done|Not now|Decision moment|Backlog|
        Planned|Up next|stays>

The seven classes are `EvidenceClass`'s values, written as they read. The
arrow may be typed as `->`. A row that names no class the board knows, or no
landing it can move a card to, is refused with this grammar in the message.

The classes computed here are the ones the board's own facts settle: a
shipped card whose signal read delivered, a shipped card whose signal only
the owner can read, a placement the board doubts, and a plan gone stale with
no lane ever. The judgment classes — built under another name, superseded,
live and open — need the corpus read and are a session's to write.
"""

import re
from datetime import datetime

from board.evidence import DOUBT
from board.lane import close_landed
from domain.card import Card
from domain.column import Column
from domain.document import Document, DocumentKind
from domain.evidence import EvidenceState, Standing
from domain.signal import Reading, Signal, SignalKind
from domain.verdict import EvidenceClass, Verdict

GRAMMAR = (
    "VERDICT: <class> — <evidence> → Done|Not now|Decision moment|Backlog|Planned|Up next|stays"
)
STAYS = "stays"
STALE_PLAN_DAYS = 21
"""Three weeks in Planned or Up next with no lane ever is a plan to ask "still
true?" of: the corpus moves fast enough that a plan this old was written
against terrain that has changed (the 2026-08-11 oversight read found every
plan older than that needing a terrain re-check before execution)."""
CLOSED: frozenset[Column] = frozenset({Column.DONE, Column.NOT_NOW})
"""The columns a verdict never covers: a card there is already ruled on."""

_CLASSES = sorted((c for c in EvidenceClass), key=lambda c: -len(c.value))
_HEAD = re.compile(
    r"^\s*(?P<cls>" + "|".join(re.escape(c.value) for c in _CLASSES) + r")\s*(?:[—–:-]|(?=→|->)|$)",
    re.I,
)
_ARROW = re.compile(r"\s*(?:→|->)\s*")
_BY_VALUE = {c.value.lower(): c for c in EvidenceClass}
_COLUMNS = {c.value.lower(): c for c in Column}


class VerdictUnreadable(Exception):
    """The VERDICT row names no verdict the board can act on; the message says what is missing."""


def parse_verdict(text: str) -> Verdict:
    head = _HEAD.match(text)
    if head is None:
        names = ", ".join(c.value for c in EvidenceClass)
        raise VerdictUnreadable(
            f"the VERDICT row names no class the board knows ({names}). The grammar: {GRAMMAR}"
        )
    evidence_class = _BY_VALUE[head.group("cls").lower()]
    rest = text[head.end() :].strip()
    arrows = list(_ARROW.finditer(rest))
    if not arrows:
        raise VerdictUnreadable(
            f"the VERDICT row names no landing (`→ Done`, `→ stays`, ...). The grammar: {GRAMMAR}"
        )
    last = arrows[-1]
    evidence = rest[: last.start()].strip().rstrip("—–-:,; ").strip()
    landing = rest[last.end() :].strip().rstrip(". ")
    if not evidence:
        raise VerdictUnreadable(f"the VERDICT row carries no evidence. The grammar: {GRAMMAR}")
    if landing.lower().startswith(STAYS):
        to: Column | None = None
    elif landing.lower() in _COLUMNS:
        to = _COLUMNS[landing.lower()]
    else:
        raise VerdictUnreadable(
            f"the VERDICT row's landing {landing!r} is no column and not `stays`. "
            f"The grammar: {GRAMMAR}"
        )
    if to in CLOSED and evidence_class == EvidenceClass.LIVE_AND_OPEN:
        raise VerdictUnreadable(
            "a card that is live and open stays; a verdict that closes it names its class"
        )
    return Verdict(evidence_class=evidence_class, evidence=evidence, to=to)


def read_or_decline(text: str | None) -> tuple[Verdict | None, str | None]:
    """The verdict a VERDICT row names, or why it names none."""
    if text is None:
        return None, "no VERDICT row is written"
    try:
        return parse_verdict(text), None
    except VerdictUnreadable as why:
        return None, str(why)


def render_verdict(verdict: Verdict) -> str:
    """The row text for a verdict: the one form `needle verdicts` writes and
    the parse reads back."""
    landing = verdict.to.value if verdict.to is not None else STAYS
    return f"{verdict.evidence_class.value} — {verdict.evidence} → {landing}"


def machine_verdict(
    card: Card,
    standing: Standing,
    document: Document | None,
    signal: Signal | None,
    last: Reading | None,
    *,
    ever_had_a_lane: bool,
    now: datetime,
) -> Verdict | None:
    """The verdict the board's own facts settle, or None where the corpus has to be read."""
    if card.place.column in CLOSED:
        return None
    if standing.state == EvidenceState.DOUBTED:
        words = standing.words or "its evidence is gone"
        return Verdict(
            evidence_class=EvidenceClass.DOUBTED,
            evidence=words.removeprefix(DOUBT),
            to=Column.DECISION_MOMENT,
        )
    if card.place.column == Column.EXECUTED and close_landed(card):
        if last is not None and last.delivered:
            return Verdict(
                evidence_class=EvidenceClass.SHIPPED_SIGNAL_READ,
                evidence=(
                    "the plan is archived, DELIVERED is written and the last reading said "
                    f"delivered: {last.words}"
                ),
                to=Column.DONE,
            )
        if signal is not None and signal.kind == SignalKind.OWNER:
            return Verdict(
                evidence_class=EvidenceClass.SHIPPED_OWNER_ONLY,
                evidence=(
                    "the plan is archived and DELIVERED is written; the signal is a question "
                    f"only you can read, due {signal.due.isoformat()}"
                ),
                to=None,
            )
        return None
    if (
        card.place.column in (Column.PLANNED, Column.UP_NEXT)
        and document is not None
        and document.kind == DocumentKind.PLAN
        and not document.archived
        and not ever_had_a_lane
    ):
        since = document.date or card.born_at.date()
        age = (now.date() - since).days
        if age >= STALE_PLAN_DAYS:
            return Verdict(
                evidence_class=EvidenceClass.STALE_PLAN,
                evidence=f"a plan {age} days old ({document.path}) with no lane ever: still true?",
                to=Column.DECISION_MOMENT,
            )
    return None
