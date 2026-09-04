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


class Renamed(BaseModel):
    card_number: int
    old_stem: str
    document: DocumentRef


class Relinked(BaseModel):
    """A plan naming `**Card:** #N` becomes that card's document."""

    card_number: int
    document: DocumentRef


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

    for document in unlinked_docs:
        if (document.kind, document.stem) in claimed:
            continue
        target = by_number.get(document.card_ref) if document.card_ref is not None else None
        if target is not None and (
            target.link is None
            or (target.link.kind == DocumentKind.SUGGESTION and document.kind == DocumentKind.PLAN)
        ):
            claimed.add((document.kind, document.stem))
            relinked.append(Relinked(card_number=target.number, document=ref(document)))
            continue
        claimed.add((document.kind, document.stem))
        born.append(Born(document=ref(document), column=BIRTH_COLUMN[document.kind]))

    return Effects(renamed=renamed, relinked=relinked, archived=archived, born=born)
