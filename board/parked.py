"""A card parked on the owner, read cold, and what may leave his column
(card #82).

A card in Decision moment is there because the board could not tell
whether it needs him. HOW-WE-WORK §1 gives the test that tells, and §11
says one move is his and the rest is the machine's with its reason on the
card. So every card parked on him is read a second time by a session with
none of the context that parked it — plan 59's reading on wider ground,
never a second reader — and the board acts on the result. What lives here
is what that result means, pure over the card's rows and history: when a
parked card is read, where each result sends it, the one rule that keeps a
commitment from leaving his attention unaccounted for, and the re-test a
move on a reading answers on every read. The beat that opens the reading
is `api/dial.py`; the door that lands the result and moves the card is
`api/doors.py::Doors.triage`.
"""

from datetime import datetime

from pydantic import BaseModel

from board.lane import first_line, has_row
from board.reconcile import home_of
from board.signals import past_due, read_or_decline
from board.triage import fingerprint
from domain.audit import AuditEntry, AuditKind
from domain.card import Actor, Card
from domain.column import Column
from domain.document import Document, DocumentKind
from domain.evidence import Evidence
from domain.lane import HANDS_ON, Lane
from domain.row import Row, RowKind
from domain.signal import Reading
from domain.triage import Commitment, Ground, Source, Triage, TriageResult

WAITINGS_PER_CARD = 2
"""How many readings may send one parked card to wait (ruling 6): a WATCH
is one per card and a second write replaces the first, so without a cap a
card whose signal failed could be sent back to wait on every park and the
owner would never see it. The third answer is his."""


def record_fingerprint(document_text: str | None, rows: list[Row]) -> str:
    """What a parked card's reading binds itself to: the document it cites
    and every row on the card, as one text. A parked card may have no
    document at all — the import's cards carry their whole brief as rows —
    so the rows are part of the record. The fingerprint is not what
    re-opens a reading (a new park or the owner's answer is, ruling 5); it
    is what the audit reads to tell a reading of this record from a
    reading of an earlier one."""
    parts = [document_text or ""] + [f"{row.kind.value}: {row.text}" for row in rows]
    return fingerprint("\n".join(parts))


def parked_at(placement: AuditEntry | None) -> datetime | None:
    """When the card was last put in Decision moment, from the audit row
    that placed it; None when the placement is not into that column."""
    if placement is None or placement.to_place is None:
        return None
    if placement.to_place.column != Column.DECISION_MOMENT:
        return None
    return placement.at


def wants_parked_reading(
    card: Card,
    placement: AuditEntry | None,
    latest: Triage | None,
    answered: AuditEntry | None,
    lane: Lane | None,
) -> bool:
    """Whether the board should read this parked card now (card #82, item
    1): it sits in Decision moment on its own, nobody has hands on it, and
    no reading has landed since it was parked or since the owner last
    answered on it. A reading landed at or after the park is the reading
    of *this* park — the card is read once per park, never once per beat;
    his answer after the reading is a change to the record the next
    reading reads (ruling 5), and nothing else re-opens one. His own park
    is read like any other — the column's promise is a sentence on every
    card — and the door moves nothing on it (ruling 7). A card whose ended
    lane still has its copy of the code on disk is read, because the
    reading runs in the project's own checkout and never touches the
    tree; only a live session on the card holds it back."""
    if card.place.column != Column.DECISION_MOMENT or card.folded_into is not None:
        return False
    if lane is not None and lane.state in HANDS_ON:
        return False
    if latest is None:
        return True
    since = parked_at(placement)
    if since is not None and latest.at < since:
        return True
    return answered is not None and answered.at > latest.at


def owner_parked(placement: AuditEntry | None) -> bool:
    """Whether the card's placement in Decision moment is the owner's own
    move (ruling 7): then the door writes the result and moves nothing."""
    return (
        placement is not None
        and placement.actor == Actor.OWNER
        and placement.kind == AuditKind.MOVED
        and parked_at(placement) is not None
    )


def _answered_after(history: list[AuditEntry], kind: RowKind) -> bool:
    """Whether an answer of the owner's landed after the newest row of this
    kind was written. A row with no writing on the history (the import's)
    is answered by any answer at all."""
    written = next(
        (
            e.at
            for e in history
            if e.kind == AuditKind.ROW and e.detail.startswith(f"{kind.value} ")
        ),
        None,
    )
    return any(
        e.kind == AuditKind.ANSWERED and (written is None or e.at >= written) for e in history
    )


def commitments_of(card: Card, history: list[AuditEntry], last: Reading | None) -> list[Commitment]:
    """Every commitment on the card that nothing accounts for (card #82,
    item 3), each naming the row. A commitment is what the card's rows
    promise: a DELIVERED with no signal the board can read; a WATCH nobody
    has read, or whose last reading did not say delivered; a question in
    the owner's words (an ASK or a Q) with no answer of his after it; a
    RULING nobody has ruled on. Accounted for means fulfilled with evidence
    on the card (the signal read as delivered), withdrawn by his answer, or
    ruled on. Age, shipped code and an absent signal are not read here at
    all, so none of them can qualify: the other make's objection was that
    a reader takes inactivity or shipped code as permission to abandon a
    commitment, and this function cannot see either. `history` is the
    card's, newest first, as the store answers it."""
    found: list[Commitment] = []
    watch = next((r.text for r in card.rows if r.kind == RowKind.WATCH), None)
    signal, why = read_or_decline(watch)
    delivered = next((r for r in card.rows if r.kind == RowKind.DELIVERED), None)
    if delivered is not None and signal is None:
        found.append(
            Commitment(
                row=RowKind.DELIVERED,
                words=f"a DELIVERED with no signal the board can read ({why}): "
                f"{first_line(delivered.text)}",
                transferable=True,
            )
        )
    if signal is not None:
        if last is None:
            found.append(
                Commitment(
                    row=RowKind.WATCH,
                    words=f"a WATCH nobody has read yet: {signal.what}",
                    transferable=True,
                )
            )
        elif not last.delivered:
            found.append(
                Commitment(
                    row=RowKind.WATCH,
                    words=f"a WATCH whose last reading did not say delivered "
                    f"({first_line(last.words)}): {signal.what}",
                    transferable=True,
                )
            )
    for kind in (RowKind.ASK, RowKind.Q):
        row = next((r for r in card.rows if r.kind == kind), None)
        if row is not None and not _answered_after(history, kind):
            found.append(
                Commitment(
                    row=kind,
                    words=f"a question in your words with no answer ({kind.value}): "
                    f"{first_line(row.text)}",
                    transferable=False,
                )
            )
    ruling = next((r for r in card.rows if r.kind == RowKind.RULING), None)
    if ruling is not None and not has_row(card, RowKind.RULED):
        found.append(
            Commitment(
                row=RowKind.RULING,
                words=f"a RULING nobody has ruled on: {first_line(ruling.text)}",
                transferable=False,
            )
        )
    return found


def unaccounted(commitments: list[Commitment]) -> str:
    """The commitments in one clause, for a refusal, a history line or a face."""
    return "; ".join(c.words for c in commitments)


def waiting_refused(
    card: Card,
    words: str,
    *,
    last: Reading | None,
    earlier: list[Triage],
    commitments: list[Commitment],
    now: datetime,
) -> str | None:
    """Why a `waiting` may not land on this card, or None (ruling 6, and
    ruling 13 from the review). Three refusals. A question in the owner's
    words, or a RULING nobody has ruled on, stands on the card: a WATCH
    row cannot carry either, so a `waiting` would send his question to
    Executed, where the signal's delivery would close the card with the
    question never answered — the silent exit item 3 forbids. The card's
    WATCH was already read as not delivered, or is past due, and the new
    signal watches the same thing: the card would go back to wait on a
    signal that already failed, and fail again, and be parked again, and
    be read again — a cycle he never sees. And two readings already sent
    this card to wait: the third answer is his. `earlier` is every earlier
    parked reading on the card."""
    signal, why = read_or_decline(words)
    if signal is None:
        return f"a `waiting` names a signal the board can read: {why}"
    held = [c for c in commitments if not c.transferable]
    if held:
        return (
            "a WATCH row cannot carry a question in the owner's words or a ruling nobody has "
            "ruled on, and this card holds one: "
            + unaccounted(held)
            + "; the result is `his`, with it as the line"
        )
    waited = sum(1 for t in earlier if t.result == TriageResult.WAITING)
    if waited >= WAITINGS_PER_CARD:
        return (
            f"{waited} readings have already sent this card to wait; a third `waiting` is "
            "refused, and the answer is `his`"
        )
    standing, _ = read_or_decline(
        next((r.text for r in card.rows if r.kind == RowKind.WATCH), None)
    )
    if standing is None or standing.what != signal.what:
        return None
    if last is not None and not last.delivered:
        return (
            f"the card's WATCH ({standing.what}) was already read as not delivered "
            f"({first_line(last.words)}); a `waiting` on the same signal defers a failed "
            "signal past the owner, so it is refused unless the signal watches something "
            "else"
        )
    if past_due(standing, now):
        return (
            f"the card's WATCH ({standing.what}) is past its due date {standing.due}; a "
            "`waiting` on the same signal is refused unless the signal watches something else"
        )
    return None


RESULT_WORDS: dict[TriageResult, str] = {
    TriageResult.NOW: "found the record already answers it",
    TriageResult.WAITING: "found it waits for a signal the board can read",
    TriageResult.STALE: "found it over",
    TriageResult.HIS: "found the decision is yours",
}
"""What a cold reading found, per result, in the owner's words: the history
line and the face say it one way."""


class ParkedLanding(BaseModel):
    """Where a parked card's reading sends it (card #82, item 2), why in
    the words the history line carries, and the predicate the move rests
    on; no column when the card stays."""

    column: Column | None
    reason: str
    evidence: Evidence | None


def now_refused(document: Document | None) -> str | None:
    """Why a `now` may not land on this parked card, or None (ruling 4):
    `now` needs something to execute — a live plan or a live suggestion.
    An archived or absent document would land the card in Planned wearing
    the wrong-column doubt, moved onto the owner's attention while
    claiming to be taken off it."""
    if document is None:
        return (
            "a `now` needs a live document to execute, and this card has none; the result "
            "is `waiting`, `his` or `stale`"
        )
    if document.archived:
        return (
            f"a `now` needs a live document to execute, and {document.path} is archived; "
            "the result is `waiting`, `his` or `stale`"
        )
    return None


def where_after_parked_reading(
    result: TriageResult,
    words: str,
    *,
    source: Source | None,
    document: Document | None,
    replaced_watch: str | None,
) -> ParkedLanding:
    """The one map from a parked card's result to its landing (card #82,
    item 2), and the rulings behind it. `now` is Planned for a live plan
    and the home column for a live suggestion, never Up next: the record
    settled that it is execution, and the owner ranks (ruling 2; ruling 4
    says what it needs). `waiting` is Executed, where a watched card sits
    and the signal loop of plan 16 reads it; the door writes the WATCH row
    first and names what it replaced. `his` stays, and the face shows the
    line. `stale` is Done with what ended it — the one exit the door
    refuses while a commitment is unaccounted for (item 3), which is
    judged before this map is read, never here."""
    if result == TriageResult.NOW:
        where = f" (source `{source.path or source.ref}`)" if source is not None else ""
        plan = document is not None and document.kind == DocumentKind.PLAN
        column = Column.PLANNED if plan else home_of(document.suggestion_kind if document else None)
        return ParkedLanding(
            column=column,
            reason=f"a cold reading {RESULT_WORDS[TriageResult.NOW]}: {words}{where}",
            evidence=Evidence.RECORD_ANSWERED,
        )
    if result == TriageResult.WAITING:
        replaced = f" (the WATCH it replaced: {replaced_watch})" if replaced_watch else ""
        return ParkedLanding(
            column=Column.EXECUTED,
            reason=f"a cold reading {RESULT_WORDS[TriageResult.WAITING]}: {words}" + replaced,
            evidence=Evidence.RECORD_ANSWERED,
        )
    if result == TriageResult.STALE:
        return ParkedLanding(
            column=Column.DONE,
            reason=f"a cold reading {RESULT_WORDS[TriageResult.STALE]}: {words}",
            evidence=Evidence.RECORD_ANSWERED,
        )
    return ParkedLanding(
        column=None,
        reason=f"a cold reading {RESULT_WORDS[TriageResult.HIS]}: {words}",
        evidence=None,
    )


def parked_doubt(latest: Triage | None, commitments: list[Commitment]) -> str | None:
    """The doubt a parked card's face carries after a `stale` the door
    refused (card #82, item 3): which commitment the reading did not
    account for, re-read on every read from the rows as they stand — so a
    commitment answered since clears it without anyone moving anything."""
    if latest is None or latest.ground != Ground.PARKED or latest.result != TriageResult.STALE:
        return None
    if not commitments:
        return None
    return (
        f"a cold reading called it over ({latest.words}), but this is unaccounted for: "
        + unaccounted(commitments)
    )


def parked_words(
    latest: Triage | None,
    *,
    doubt: str | None,
    parked_by_owner: bool,
    being_read: bool,
) -> str | None:
    """Why a card in Decision moment is there, after its cold reading, in
    the face's words (card #82; review finding 3): the doubt of a refused
    `stale` first; his line on a `his`; on a card he parked himself, what
    the reading found and that it stays for him; on a `stale` the door
    refused whose commitment has since been settled, that it is settled
    and the card waits for his move — never "you parked it yourself" on a
    card the machine parked. None when no reading has landed: the
    column's own words, or that a reading is on now."""
    if doubt is not None:
        return doubt
    if latest is None or latest.ground != Ground.PARKED:
        if being_read:
            return (
                "a cold reading of the record is judging now whether this needs you; the "
                "column's word until it lands: nothing here moves without a word from you"
            )
        return None
    found = f"a cold reading of the record {RESULT_WORDS[latest.result]}: {latest.words}"
    if latest.result == TriageResult.HIS:
        return found
    if parked_by_owner:
        return f"{found}. You parked it yourself, so it stays until you move it"
    if latest.result == TriageResult.STALE:
        return (
            f"{found}, and the board refused to close it over what was then unaccounted for; "
            "that is settled since, and the card waits for your move"
        )
    return f"{found}; the board moved nothing, and the card waits for your move"


def record_answered_missing(
    decision: Triage | None,
    card: Card,
    *,
    source_fingerprint: str | None,
    commitments: list[Commitment],
) -> str | None:
    """The fact a `RECORD_ANSWERED` placement needs and this read does not
    have, or None when it holds (ruling 8): per result, because "a reading
    exists" never stops being true. `now`: the source the reading named
    still reads as it did. `waiting`: the WATCH row still names a signal,
    and it is the reading's. `stale`: no commitment on the card is
    unaccounted for."""
    if decision is None or decision.ground != Ground.PARKED:
        return "no cold reading of the card exists"
    if decision.result == TriageResult.NOW:
        if (
            decision.source_fingerprint is not None
            and source_fingerprint != decision.source_fingerprint
        ):
            moved = "has changed" if source_fingerprint is not None else "is gone"
            return f"the source the reading relied on ({decision.source_ref}) {moved}"
        return None
    if decision.result == TriageResult.WAITING:
        watch = next((r.text for r in card.rows if r.kind == RowKind.WATCH), None)
        signal, why = read_or_decline(watch)
        if signal is None:
            return f"its WATCH row names no signal the board can read ({why})"
        named, _ = read_or_decline(decision.words)
        if named is not None and named.what != signal.what:
            return f"its WATCH row watches something other than the reading named ({named.what})"
        return None
    if decision.result == TriageResult.STALE:
        if commitments:
            return "a commitment on it is unaccounted for: " + unaccounted(commitments)
        return None
    return f"the reading landed {decision.result.value}, which moves nothing"
