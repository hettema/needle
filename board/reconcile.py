"""What a read of the corpus implies for the cards.

The corpus is the only way in (owner ruling 2026-09-03): a live document with
no card becomes one. Identity follows the document — its stem first, then its
title — so a card keeps its number when its file is archived or renamed. The
function is pure: it says what should happen and the store makes it so.
"""

from pydantic import BaseModel

from domain.card import Card, DocumentLink
from domain.column import Column
from domain.corpus import CorpusIndex
from domain.document import Document, DocumentKind, DocumentRef

BIRTH_COLUMN: dict[DocumentKind, Column] = {
    DocumentKind.PLAN: Column.PLANNED,
    DocumentKind.SUGGESTION: Column.BACKLOG,
}


class Born(BaseModel):
    document: DocumentRef
    column: Column
    found_by: str | None
    """The document's `Found by` line, so a birth can say which conversation
    it came from when the line names one (plan 07, item 1)."""


class Renamed(BaseModel):
    card_number: int
    old_stem: str
    document: DocumentRef


class Relinked(BaseModel):
    """A document naming `**Card:** #N` becomes that card's document."""

    card_number: int
    document: DocumentRef
    archived: bool
    """The document sits in done/: the link is born archived, so a shipped
    card whose plan named it only at the close is not doubted for want of a
    plan (three of Hello Revenue's Executed cards were, 2026-09-04)."""


class Archived(BaseModel):
    card_number: int
    document: DocumentRef


class Effects(BaseModel):
    renamed: list[Renamed]
    relinked: list[Relinked]
    archived: list[Archived]
    born: list[Born]

    def empty(self) -> bool:
        return not (self.renamed or self.relinked or self.archived or self.born)


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


def reconcile(index: CorpusIndex, cards: list[Card]) -> Effects:
    by_number = {c.number: c for c in cards}
    linked = _linked_stems(cards)
    unlinked_docs = [d for d in index.live() if (d.kind, d.stem) not in linked]

    renamed: list[Renamed] = []
    relinked: list[Relinked] = []
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

    for document in unlinked_docs:
        if (document.kind, document.stem) in claimed:
            continue
        claimed.add((document.kind, document.stem))
        target = names_its_card(document)
        if target is not None:
            relinked.append(
                Relinked(card_number=target.number, document=ref(document), archived=False)
            )
            continue
        born.append(
            Born(
                document=ref(document),
                column=BIRTH_COLUMN[document.kind],
                found_by=document.found_by,
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
                Relinked(card_number=target.number, document=ref(document), archived=True)
            )

    return Effects(renamed=renamed, relinked=relinked, archived=archived, born=born)
