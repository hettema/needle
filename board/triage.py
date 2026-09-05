"""Where a defect routes, derived once and read by everybody (plan 59).

Pure over domain values and the files a source names; the lifecycle that
acts on these answers lives in `api/dial.py`, and the verb that lands a
result in `api/doors.py`.

Three things live here and nothing else: the fingerprint a row binds itself
to, the cheap bar a `Fix:` line's reason has to clear, and the one function
that turns a document's mark plus a reading's result into the routing state
the CLI, the dial and the page all show. Nothing anywhere else branches on
matching the words `now`, `his` or `unmarked` — that is the drift this
module exists to make impossible.
"""

import hashlib
import re
from collections.abc import Callable
from pathlib import Path

from domain.audit import AuditEntry
from domain.document import Document, FixMark
from domain.triage import Routed, Routing, Source, Triage, TriageResult

FINGERPRINT_LENGTH = 16
"""Enough of the digest to name a text; the whole thing is noise on a card."""

SOURCE_EXCERPT = 4000
"""How much of a source the brief carries. The fingerprint is of the whole
file, never of the excerpt: a change past the cap would otherwise leave a
row standing over a source it never read."""


def fingerprint(text: str) -> str:
    """A text's identity for a row that judged it. Line endings are
    normalised so a checkout with different endings is not a different
    proposition; nothing else is, because a triage reads prose and a moved
    comma can move a meaning."""
    normalised = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()[:FINGERPRINT_LENGTH]


# ── item 2: the cheap bar on a mark's reason ───────────────────────────

CATEGORY_ONLY: frozenset[str] = frozenset(
    {
        "product call",
        "prompt change",
        "new surface",
        "ux",
        "bound",
        "design call",
        "owner call",
        "policy",
        "scope",
        "judgment",
        "judgement",
    }
)
"""Words that name the shape of a decision without naming the decision. Each
was written on a real `Fix:` line and told the next reader nothing."""

REASON_WORDS = 3
"""A reason shorter than this says a category or a bare source, never a
proposition. Deliberately a floor and not a judgment: this ratchet is cheap
and is not the proof — the triage reading (item 3) is, and it reads the
source rather than the shape of the sentence."""

_ARTICLE = re.compile(r"^(?:it is |this is |a |an |the |just |simply |purely )+", re.I)
_NOISE = re.compile(r"[`*_\"'()\[\]]")


def _normalise(why: str) -> str:
    plain = _NOISE.sub("", why).strip().strip(".,;:—-– ").lower()
    return " ".join(_ARTICLE.sub("", plain).split())


def why_is_a_reason(why: str | None) -> str | None:
    """Why a `now` or `his` mark's reason does not clear the bar, or None
    when it does. Refused: nothing after the mark, a category word with the
    decision missing, and a reason too short to be one — a backticked path
    on its own is a source, and a source is not a reason for anything until
    somebody says what in it selects the outcome."""
    if why is None or not why.strip():
        return "the mark names no reason; say what selects this outcome"
    plain = _normalise(why)
    if not plain:
        return "the mark names no reason; say what selects this outcome"
    if plain in CATEGORY_ONLY:
        return (
            f'"{plain}" names the shape of the decision, not the decision; '
            "say which outcome it selects and what selects it"
        )
    if len(plain.split()) < REASON_WORDS:
        return (
            f'"{plain}" is too short to be a reason; a source on its own is not one — '
            "say what in it selects the outcome"
        )
    return None


# ── the source a reading relied on ─────────────────────────────────────

_CARD_REF = re.compile(r"^#?(\d+)$")
_BACKTICKED = re.compile(r"`([^`]+)`")
_PATH = re.compile(r"^[\w./-]+\.[A-Za-z0-9]+")
_LOOSE_CARD = re.compile(r"(?:^|\s)#(\d+)\b")


def source_ref_of(why: str | None) -> str | None:
    """The source a mark's reason points at, if it points at one: the first
    backticked path, else the first `#N`. An affordance and nothing more —
    what makes a source a source is that it resolves and says what the mark
    claims, which is the reading's job (item 3), not this regex's."""
    if not why:
        return None
    for quoted in _BACKTICKED.findall(why):
        candidate = quoted.strip()
        if _PATH.match(candidate):
            return candidate
    card = _LOOSE_CARD.search(why)
    return f"#{card.group(1)}" if card else None
_TRAILER = re.compile(r"(::|#L|:\d+$).*$")


def resolve_source(
    ref: str | None,
    root: Path,
    card_document: Callable[[int], str | None],
) -> Source | None:
    """What a reading names as its source, resolved: a path in the project,
    or `#N` for a card, read through `card_document`. A reference that
    resolves nowhere comes back with no text and no fingerprint, named — the
    verb refuses `now` on it, because prose shaped like a source is not a
    source (`docs/no-such-plan.md` reads exactly like a real path)."""
    if ref is None or not ref.strip():
        return None
    written = ref.strip().strip("`").strip()
    card = _CARD_REF.match(written)
    path = card_document(int(card.group(1))) if card else _TRAILER.sub("", written)
    if not path:
        return Source(
            ref=written,
            path=None,
            text=None,
            fingerprint=None,
            note=f"{written} names no document the board can read",
        )
    file = (root / path).resolve()
    try:
        inside = file.is_relative_to(root.resolve())
    except ValueError:  # pragma: no cover — is_relative_to raises on nothing here
        inside = False
    if not inside:
        return Source(
            ref=written,
            path=path,
            text=None,
            fingerprint=None,
            note=f"{path} is outside the project; a source has to be readable in it",
        )
    if not file.is_file():
        return Source(
            ref=written,
            path=path,
            text=None,
            fingerprint=None,
            note=f"{path} is not a file in this project: the source resolved nowhere",
        )
    text = file.read_text(encoding="utf-8", errors="replace")
    excerpt = text if len(text) <= SOURCE_EXCERPT else text[:SOURCE_EXCERPT] + "\n… (truncated)"
    return Source(
        ref=written,
        path=path,
        text=excerpt,
        fingerprint=fingerprint(text),
        note=f"{path}, {len(text)} characters, fingerprint {fingerprint(text)}",
    )


# ── item 1: the one routing state ──────────────────────────────────────

UNMARKED = "unmarked"


def _mark_words(document: Document) -> str:
    if document.fix is None:
        return f"{UNMARKED} ({document.fix_note})"
    fix = document.fix
    return f"marked {fix.mark.value}" + (f" {fix.trigger}" if fix.trigger else "")


def routing_of(
    document: Document | None,
    triage: Triage | None,
    *,
    source_fingerprint: str | None,
) -> Routed:
    """Where this defect routes, and why in one sentence. `triage` is the
    card's latest reading; `source_fingerprint` is that reading's source as
    it reads today.

    Two invariants, and every branch below is one of them. A reading may
    make routing stricter the moment it lands. A reading never makes it
    looser than the corpus: a `now` on a document the corpus does not mark
    `now` routes to nobody until a commit rewrites the mark citing the row,
    because the document is what the next cold session reads and the row is
    not."""
    if document is None:
        return Routed(
            state=Routing.NEEDS_TRIAGE,
            why="no live document behind the card; nothing to verify",
        )
    if triage is None:
        return Routed(
            state=Routing.NEEDS_TRIAGE,
            why=f"{_mark_words(document)}, and no reading has verified it; it is nobody's yet",
        )
    if triage.document_fingerprint != document.fingerprint:
        return Routed(
            state=Routing.STALE,
            why=(
                f"the reading of {triage.at.date().isoformat()} judged an earlier text of "
                f"{document.path}; it is nobody's until a fresh reading"
            ),
        )
    if triage.source_fingerprint is not None and source_fingerprint != triage.source_fingerprint:
        moved = "has changed" if source_fingerprint is not None else "is gone"
        return Routed(
            state=Routing.STALE,
            why=(
                f"the source the reading relied on ({triage.source_ref}) {moved}; it is "
                "nobody's until a fresh reading"
            ),
        )
    mark = document.fix.mark if document.fix is not None else None
    if triage.result == TriageResult.CANNOT_TELL:
        return Routed(
            state=Routing.CANNOT_TELL,
            why=f"the reading could not settle it: {triage.words}",
        )
    if triage.result == TriageResult.SPLIT:
        return Routed(
            state=Routing.NEEDS_TRIAGE,
            why=(
                "the reading found two decisions in one document and authorises neither: "
                f"{triage.words}"
            ),
        )
    if triage.result == TriageResult.HIS:
        return Routed(state=Routing.TRIAGED_HIS, why=f"a reading says it is yours: {triage.words}")
    if triage.result == TriageResult.WHEN:
        if mark in (FixMark.WHEN, FixMark.NOW):
            return Routed(
                state=Routing.TRIAGED_WHEN,
                why=f"a reading says it waits for a trigger: {triage.words}",
            )
        return Routed(
            state=Routing.NEEDS_TRIAGE,
            why=(
                "a reading says it waits for a trigger, and the document is "
                f"{_mark_words(document)}; nothing routes until a commit rewrites the "
                "mark citing the reading"
            ),
        )
    if mark == FixMark.NOW:
        return Routed(state=Routing.TRIAGED_NOW, why=f"a reading verified it: {triage.words}")
    return Routed(
        state=Routing.NEEDS_TRIAGE,
        why=(
            f"a reading verified it as now, and the document is {_mark_words(document)}; a row "
            "never routes more freely than the corpus — a commit has to rewrite the mark citing "
            "the reading first"
        ),
    )


def already_ruled(triage: Triage | None, answered: AuditEntry | None) -> str | None:
    """Why the owner is not asked again, or None when the question is still
    open for him. His `answered` row is durable and the corpus write that
    follows it is not: every failure after the row leaves the row standing,
    so the test for *has he answered this* is the row's time against the
    reading's, never whether the lane that applies it worked (plan 59, item
    5). A later reading of changed text is a new question and he is asked
    it."""
    if triage is None or answered is None:
        return None
    if answered.at < triage.at:
        return None
    return f"you ruled on this on {answered.at.date().isoformat()}: {answered.detail}"


class Sources:
    """The project's sources as one read sees them, resolved once each.

    A board assembly asks after the source of every defect on the rail, and
    a rail is hundreds of cards; without this, one read of the page is one
    file read per card, four times a second. The cache lives exactly as long
    as the read that made it, so a source edited between two reads is a new
    fingerprint on the next one — which is the whole point of the
    fingerprint."""

    def __init__(self, root: Path, card_document: Callable[[int], str | None]):
        self.root = root
        self.card_document = card_document
        self._seen: dict[str, Source | None] = {}

    def resolve(self, ref: str | None) -> Source | None:
        if ref is None:
            return None
        if ref not in self._seen:
            self._seen[ref] = resolve_source(ref, self.root, self.card_document)
        return self._seen[ref]

    def fingerprint_of(self, ref: str | None) -> str | None:
        resolved = self.resolve(ref)
        return resolved.fingerprint if resolved is not None else None


def routing_now(document: Document | None, triage: Triage | None, sources: Sources) -> Routed:
    """`routing_of` with the row's source read as it stands today: the one
    call every reader makes."""
    return routing_of(
        document,
        triage,
        source_fingerprint=sources.fingerprint_of(triage.source_ref if triage else None),
    )


# ── the sentences the card shows ───────────────────────────────────────


def triaged_row(triage: Triage, source: Source | None) -> str:
    """The `TRIAGED` row's text: what the reading landed, what it leaned on,
    and the decision identity, in one sentence the owner can read without
    opening anything. The record beside it is what the machine reads; this
    is what he does."""
    where = (
        f" — source `{source.path or source.ref}`"
        if source is not None and source.path is not None
        else ""
    )
    direction = f" — {triage.direction.value}" if triage.direction is not None else ""
    return f"{triage.result.value}{where}{direction}: {triage.words} ({triage.decision})"


def split_row(other: str, half: str, decision: str) -> str:
    """The `SPLIT` row's text on one half of a separated document: which
    half this card is, where the other went, and the decision both came
    out of, so `needle fixes` can follow the two fates from one identity."""
    return f"{half} — the other half is {other} ({decision})"
