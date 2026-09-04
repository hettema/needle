"""What a read of the corpus implies for the cards.

The corpus is the only way in (owner ruling 2026-09-03): a live document with
no card becomes one. Identity follows the document — its stem first, then its
title — so a card keeps its number when its file is archived or renamed. And
a card follows its plan (plan 06, item 5): a plan whose head cites a
suggestion carries it, so the suggestion's card becomes the plan's card with
the same number and history, and the other suggestions the same plan cites
fold under that card instead of standing on their own. The function is pure:
it says what should happen and the store makes it so.
"""

from pydantic import BaseModel

from domain.card import Card, DocumentLink
from domain.column import DEFECTS_RAIL, Column
from domain.corpus import CorpusIndex
from domain.document import Document, DocumentKind, DocumentRef, SuggestionKind

BIRTH_COLUMN: dict[DocumentKind, Column] = {
    DocumentKind.PLAN: Column.PLANNED,
    DocumentKind.SUGGESTION: Column.BACKLOG,
}

SHIPPED: frozenset[Column] = frozenset({Column.EXECUTED, Column.DONE})
"""A card here is shipped work; a plan citing its suggestion carries nothing
that is still open, so it neither relinks nor folds."""

PROMOTED_FROM: frozenset[Column] = frozenset({Column.BACKLOG, Column.NOT_NOW})
"""Where a plan appearing is what promotes a card to Planned. Anywhere else
the card sits where the owner put it, and the plan is simply its document."""


class Born(BaseModel):
    document: DocumentRef
    column: Column
    found_by: str | None
    """The document's `Found by` line, so a birth can say which conversation
    it came from when the line names one (plan 07, item 1)."""
    kind: SuggestionKind | None
    """A suggestion's kind: a defect is born on Backlog's defects rail (plan 06, item 2)."""


class Renamed(BaseModel):
    card_number: int
    old_stem: str
    document: DocumentRef


class Relinked(BaseModel):
    """A document becomes a card's document: one naming `**Card:** #N`, or a
    plan whose head cites the suggestion the card carries."""

    card_number: int
    document: DocumentRef
    archived: bool
    """The document sits in done/: the link is born archived, so a shipped
    card whose plan named it only at the close is not doubted for want of a
    plan (three of Hello Revenue's Executed cards were, 2026-09-04)."""
    why: str
    """How the document claims the card, for the history row."""
    promote: bool
    """A live plan took over a suggestion or a note: the card moves to
    Planned from Backlog or Not now, since a plan appearing is what promotes it."""


class Folded(BaseModel):
    """A card whose suggestion a plan carries alongside another's: it folds
    under the plan's card, follows it, and closes when it closes."""

    card_number: int
    into: int
    plan: DocumentRef


class Rehomed(BaseModel):
    """A Backlog card whose document's kind and whose group disagree: a
    defect belongs on the rail and an idea below it."""

    card_number: int
    into_rail: bool
    kind: SuggestionKind


class Archived(BaseModel):
    card_number: int
    document: DocumentRef


class Effects(BaseModel):
    renamed: list[Renamed]
    relinked: list[Relinked]
    folded: list[Folded]
    rehomed: list[Rehomed]
    archived: list[Archived]
    born: list[Born]

    def empty(self) -> bool:
        return not (
            self.renamed
            or self.relinked
            or self.folded
            or self.rehomed
            or self.archived
            or self.born
        )


def ref(document: Document) -> DocumentRef:
    return DocumentRef(
        kind=document.kind, stem=document.stem, path=document.path, title=document.title
    )


def link_for(document: Document) -> DocumentLink:
    return DocumentLink(
        kind=document.kind, stem=document.stem, title=document.title, archived=document.archived
    )


def _linked_stems(cards: list[Card]) -> set[tuple[DocumentKind, str]]:
    return {(c.link.kind, c.link.stem) for c in cards if c.link}


def carried_stems(index: CorpusIndex) -> set[str]:
    """Every suggestion stem some plan's head cites. A carried suggestion is
    never born as a card of its own: the plan's card is its card."""
    return {stem for d in index.documents if d.kind == DocumentKind.PLAN for stem in d.cites}


def reconcile(index: CorpusIndex, cards: list[Card]) -> Effects:
    by_number = {c.number: c for c in cards}
    linked = _linked_stems(cards)
    card_of = {(c.link.kind, c.link.stem): c for c in cards if c.link}
    carried = carried_stems(index)
    unlinked_docs = [
        d
        for d in index.live()
        if (d.kind, d.stem) not in linked
        and not (d.kind == DocumentKind.SUGGESTION and d.stem in carried)
    ]

    renamed: list[Renamed] = []
    relinked: list[Relinked] = []
    folded: list[Folded] = []
    rehomed: list[Rehomed] = []
    archived: list[Archived] = []
    born: list[Born] = []
    claimed: set[tuple[DocumentKind, str]] = set()

    for card in cards:
        if card.link is None:
            continue
        current = index.find(card.link.kind, card.link.stem)
        if current is not None:
            if current.archived and not card.link.archived:
                archived.append(Archived(card_number=card.number, document=ref(current)))
            continue
        match = next(
            (
                d
                for d in unlinked_docs
                if d.kind == card.link.kind
                and d.title == card.link.title
                and (d.kind, d.stem) not in claimed
            ),
            None,
        )
        if match is not None:
            claimed.add((match.kind, match.stem))
            renamed.append(
                Renamed(card_number=card.number, old_stem=card.link.stem, document=ref(match))
            )

    def names_its_card(document: Document) -> Card | None:
        target = by_number.get(document.card_ref) if document.card_ref is not None else None
        if target is not None and (
            target.link is None
            or (target.link.kind == DocumentKind.SUGGESTION and document.kind == DocumentKind.PLAN)
        ):
            return target
        return None

    def carriable(card: Card | None) -> bool:
        """A card a plan may carry: it stands on its own, behind a suggestion,
        and is not shipped."""
        return (
            card is not None
            and card.folded_into is None
            and card.link is not None
            and card.link.kind == DocumentKind.SUGGESTION
            and card.place.column not in SHIPPED
        )

    # A card follows its plan: live plans first, so a suggestion two plans
    # cite folds under the one still open.
    taken: set[int] = set()
    plans = sorted(
        (d for d in index.documents if d.kind == DocumentKind.PLAN and d.cites),
        key=lambda d: (d.archived, d.path),
    )
    for plan in plans:
        cited = [card_of.get((DocumentKind.SUGGESTION, stem)) for stem in plan.cites]
        cited = [c for c in cited if carriable(c) and c.number not in taken]
        owner = card_of.get((DocumentKind.PLAN, plan.stem)) or names_its_card(plan)
        if owner is None and cited:
            owner = cited[0]
            claimed.add((plan.kind, plan.stem))
            relinked.append(
                Relinked(
                    card_number=owner.number,
                    document=ref(plan),
                    archived=plan.archived,
                    why="which carries this card's suggestion",
                    promote=not plan.archived,
                )
            )
        if owner is None:
            continue
        taken.add(owner.number)
        for other in cited:
            if other.number == owner.number:
                continue
            taken.add(other.number)
            folded.append(Folded(card_number=other.number, into=owner.number, plan=ref(plan)))

    for document in unlinked_docs:
        if (document.kind, document.stem) in claimed:
            continue
        claimed.add((document.kind, document.stem))
        target = names_its_card(document)
        if target is not None:
            relinked.append(
                Relinked(
                    card_number=target.number,
                    document=ref(document),
                    archived=False,
                    why="which names this card",
                    promote=document.kind == DocumentKind.PLAN,
                )
            )
            continue
        born.append(
            Born(
                document=ref(document),
                column=BIRTH_COLUMN[document.kind],
                found_by=document.found_by,
                kind=document.suggestion_kind,
            )
        )

    # An archived document is never born (the corpus is the only way in, and
    # done/ is the record of what already came in), but one that names its
    # card links to it: a plan written at the close, archived in the same
    # fold, is still the card's document.
    for document in index.archived():
        if (document.kind, document.stem) in linked or (document.kind, document.stem) in claimed:
            continue
        target = names_its_card(document)
        if target is not None and target.number not in {r.card_number for r in relinked}:
            claimed.add((document.kind, document.stem))
            relinked.append(
                Relinked(
                    card_number=target.number,
                    document=ref(document),
                    archived=True,
                    why="which names this card",
                    promote=False,
                )
            )

    # The defects rail follows the document's word, on every read.
    folding = {f.card_number for f in folded}
    for card in cards:
        if (
            card.link is None
            or card.link.kind != DocumentKind.SUGGESTION
            or card.folded_into is not None
            or card.number in folding
            or card.place.column != Column.BACKLOG
        ):
            continue
        document = index.find(card.link.kind, card.link.stem)
        if document is None or document.suggestion_kind is None:
            continue
        in_rail = card.place.group == DEFECTS_RAIL
        wants_rail = document.suggestion_kind == SuggestionKind.DEFECT
        if in_rail != wants_rail:
            rehomed.append(
                Rehomed(card_number=card.number, into_rail=wants_rail, kind=document.suggestion_kind)
            )

    # A card whose suggestion a plan takes over in this same read is not a
    # card whose document was archived: the plan-writing session moves the
    # carried suggestion to done/ in the commit that lands the plan, and
    # when the watcher sees both in one batch the archive would otherwise be
    # stamped over the new link, so the card read "its plan was archived,
    # but no session wrote it up" and went to Decision moment with a done/
    # path that does not exist (Needle #30, 2026-09-04 23:03Z; found by the
    # dial's own path, plan 11, which follows the plan onto the card).
    taken_over = {r.card_number for r in relinked}
    archived = [a for a in archived if a.card_number not in taken_over]

    return Effects(
        renamed=renamed,
        relinked=relinked,
        folded=folded,
        rehomed=rehomed,
        archived=archived,
        born=born,
    )
