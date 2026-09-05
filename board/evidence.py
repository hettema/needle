"""Re-testing a machine placement against the facts of this read.

The predicate behind each machine-placed column is one function here, over
the same facts the loop reads (plan 04, item 1). A placement names the
predicate it satisfied on its audit row; a read asks that predicate again and
a card whose evidence is gone carries the missing fact in words. Nothing is
moved from here — the doubt is said before and independent of any move the
loop makes, so a claim never outlives its evidence in silence.
"""

from board.lane import has_row
from board.signals import read_or_decline
from domain.audit import AuditEntry
from domain.card import Actor, Card
from domain.column import Column
from domain.evidence import Evidence, EvidenceState, Standing
from domain.lane import HANDS_ON, Lane, LaneState
from domain.row import RowKind
from domain.signal import Reading

BY_COLUMN: dict[Column, Evidence] = {
    Column.EXECUTING: Evidence.HANDS_ON,
    Column.EXECUTED: Evidence.CLOSE_LANDED,
}
"""What a placement with no predicate named rests on, by column: the 0.1
import's placements and a session's close. Done and Decision moment each have
two makers — a reading or the owner, the lane loop or the owner — and 0.1's
own grammar made Done the owner's move ("verification stays yours"), so an
unnamed placement there is his word and is trusted, never doubted."""

DOUBT = "the board doubts this: "


def evidence_of(card: Card, placement: AuditEntry | None) -> tuple[Actor, Evidence | None]:
    """Who placed the card and on what predicate; None when nobody's predicate governs it."""
    if placement is None:
        return Actor.CORPUS, None
    if placement.actor == Actor.OWNER:
        return Actor.OWNER, None
    if placement.evidence is not None:
        return placement.actor, placement.evidence
    return placement.actor, BY_COLUMN.get(card.place.column)


def missing_fact(
    evidence: Evidence, card: Card, lane: Lane | None, last: Reading | None
) -> str | None:
    """The fact the predicate needs and this read does not have, or None when it holds."""
    if evidence == Evidence.HANDS_ON:
        if lane is None or lane.state == LaneState.NONE:
            return "no lane exists for it — no worktree on disk and no session"
        if lane.state in HANDS_ON:
            return None
        why = f" ({lane.died})" if lane.died else ""
        return f"no live session has hands on its worktree{why}"
    if evidence == Evidence.CLOSE_LANDED:
        gone: list[str] = []
        if card.link is None:
            gone.append("no plan or suggestion is written behind it")
        elif not card.link.archived:
            gone.append(f"its plan is not archived (docs/plans/{card.link.stem}.md is live)")
        if not has_row(card, RowKind.DELIVERED):
            gone.append("no DELIVERED row is written")
        watch = next((r.text for r in card.rows if r.kind == RowKind.WATCH), None)
        signal, why = read_or_decline(watch)
        if signal is None:
            gone.append(f"its WATCH row names no signal the board can read ({why})")
        return "; ".join(gone) or None
    if evidence == Evidence.SIGNAL_DELIVERED:
        if last is None:
            return "no reading of its signal has been made"
        if not last.delivered:
            return f"the last reading did not say delivered: {last.words}"
        return None
    if evidence == Evidence.SIGNAL_FAILED:
        if last is None:
            return "no reading of its signal exists"
        if last.delivered:
            return f"the last reading says delivered: {last.words}"
        return None
    if evidence == Evidence.DOCUMENT_ARCHIVED:
        if card.link is None:
            return "no document is written behind it any more"
        if not card.link.archived:
            return f"its document is live again ({card.link.stem})"
    if evidence == Evidence.PLAN_LIVE:
        if card.link is None:
            return "no document is written behind it any more"
        if card.link.archived:
            return f"its plan is archived ({card.link.path()})"
        return None
    if lane is not None and lane.state in HANDS_ON:
        return f"a session has hands on it again: {lane.sentence}"
    return None


def standing_for(
    card: Card,
    placement: AuditEntry | None,
    lane: Lane | None,
    last: Reading | None,
    *,
    read: bool,
) -> Standing:
    """Where the card's placement stands on this read. `read` is whether the
    loop has read the machine since the board was served; before that every
    machine placement is evidence unknown, the 0.1 import's included."""
    actor, evidence = evidence_of(card, placement)
    if evidence is None:
        return Standing(actor=actor, evidence=None, state=EvidenceState.TRUSTED, words=None)
    if not read:
        words = (
            "imported from Needle 0.1; evidence unknown until the first read"
            if actor == Actor.IMPORT
            else "not tested yet: the loop has not read the machine"
        )
        return Standing(actor=actor, evidence=evidence, state=EvidenceState.UNKNOWN, words=words)
    gone = missing_fact(evidence, card, lane, last)
    if gone is None:
        return Standing(actor=actor, evidence=evidence, state=EvidenceState.HELD, words=None)
    return Standing(actor=actor, evidence=evidence, state=EvidenceState.DOUBTED, words=DOUBT + gone)
