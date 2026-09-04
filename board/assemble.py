"""Assembling what the page receives from what the store holds and the corpus says.

Everything a card shows beyond its stored place and rows is derived here, at
read time, from the document: its state (five, always one), its gate, its
essence. Deriving rather than copying is what keeps the board true to the
file with nobody syncing anything.
"""

from datetime import datetime, timedelta

from board.moves import GroupLayout
from board.reconcile import ref
from domain.audit import AuditEntry
from domain.board import (
    Attention,
    BoardState,
    CardDetail,
    CardSummary,
    ColumnView,
    EssenceSource,
    GroupView,
)
from domain.card import Card, CardOrigin
from domain.column import COLUMN_DEFINITIONS, Column
from domain.corpus import CorpusIndex, CorpusSummary
from domain.document import Document, DocumentKind, DocumentRef, DocumentState
from domain.gate import Gate
from domain.project import Project
from domain.row import ROW_HALF, Row, RowHalf, RowKind

NEW_FOR = timedelta(days=1)

_FOLDER: dict[DocumentKind, str] = {
    DocumentKind.PLAN: "docs/plans",
    DocumentKind.SUGGESTION: "docs/slice-suggestions",
}


def document_of(card: Card, index: CorpusIndex) -> Document | None:
    if card.link is None:
        return None
    return index.find(card.link.kind, card.link.stem)


def document_state(card: Card, document: Document | None) -> DocumentState:
    if card.link is None:
        return DocumentState.NOTE
    if document is None:
        return DocumentState.GONE
    if document.archived:
        return DocumentState.ARCHIVED
    return DocumentState(document.kind.value)


def cited_path(card: Card) -> str | None:
    """The path the card cites for its document, whether or not it exists."""
    if card.link is None:
        return None
    folder = _FOLDER[card.link.kind] + ("/done" if card.link.archived else "")
    return f"{folder}/{card.link.stem}.md"


def card_gate(card: Card, document: Document | None) -> Gate | None:
    if document is not None and document.gate is not None:
        return document.gate
    return card.gate


def essence(card: Card, document: Document | None) -> tuple[str | None, EssenceSource | None]:
    serves = next((r.text for r in card.rows if r.kind == RowKind.SERVES), None)
    if serves:
        return serves, EssenceSource.CARD
    if document is not None and document.essence:
        return document.essence, EssenceSource.DOCUMENT
    return None, None


def is_new(card: Card, now: datetime) -> bool:
    return card.origin == CardOrigin.ARRIVED and card.born_at >= now - NEW_FOR


def summarize(card: Card, index: CorpusIndex, now: datetime) -> CardSummary:
    document = document_of(card, index)
    text, source = essence(card, document)
    state = document_state(card, document)
    path = document.path if document is not None else cited_path(card)
    return CardSummary(
        number=card.number,
        title=card.title,
        essence=text,
        essence_source=source,
        gate=card_gate(card, document),
        tags=card.tags,
        document_state=state,
        document_path=path,
        points=sum(1 for r in card.rows if r.kind != RowKind.SERVES),
        is_new=is_new(card, now),
        age_date=document.date if document is not None and document.date else card.born_at.date(),
        place=card.place,
    )


def split_rows(rows: list[Row]) -> tuple[list[Row], list[Row]]:
    brief = [r for r in rows if ROW_HALF[r.kind] == RowHalf.BRIEF]
    record = [r for r in rows if ROW_HALF[r.kind] == RowHalf.RECORD]
    return brief, record


def documents_without_card(index: CorpusIndex, cards: list[Card]) -> list[DocumentRef]:
    linked = {(c.link.kind, c.link.stem) for c in cards if c.link}
    return [ref(d) for d in index.live() if (d.kind, d.stem) not in linked]


def corpus_summary(index: CorpusIndex, *, watching: bool, watch_note: str | None) -> CorpusSummary:
    live = index.live()
    return CorpusSummary(
        live_plans=sum(1 for d in live if d.kind == DocumentKind.PLAN),
        live_suggestions=sum(1 for d in live if d.kind == DocumentKind.SUGGESTION),
        archived=len(index.archived()),
        watching=watching,
        watch_note=watch_note,
        read_at=index.read_at,
    )


def assemble_board(
    *,
    project: Project,
    layout: list[GroupLayout],
    cards: list[Card],
    index: CorpusIndex,
    version: int,
    watching: bool,
    watch_note: str | None,
    now: datetime,
) -> BoardState:
    by_number = {c.number: c for c in cards}
    summaries = {n: summarize(c, index, now) for n, c in by_number.items()}

    columns: list[ColumnView] = []
    for definition in COLUMN_DEFINITIONS:
        groups = [
            GroupView(name=g.name, cards=[summaries[n] for n in g.numbers])
            for g in layout
            if g.column == definition.column
        ]
        if not groups:
            groups = [GroupView(name=None, cards=[])]
        columns.append(
            ColumnView(
                definition=definition,
                groups=groups,
                count=sum(len(g.cards) for g in groups),
            )
        )

    def count(column: Column) -> int:
        return sum(1 for c in cards if c.place.column == column)

    without_card = documents_without_card(index, cards)
    attention = Attention(
        asking_you=count(Column.DECISION_MOMENT),
        in_flight=count(Column.EXECUTING),
        arrived_today=sum(1 for s in summaries.values() if s.is_new),
        documents_gone=sum(1 for s in summaries.values() if s.document_state == DocumentState.GONE),
        documents_without_card=len(without_card),
    )
    return BoardState(
        project=project,
        version=version,
        generated_at=now,
        corpus=corpus_summary(index, watching=watching, watch_note=watch_note),
        attention=attention,
        columns=columns,
        documents_without_card=without_card,
    )


def assemble_detail(
    card: Card, index: CorpusIndex, history: list[AuditEntry], now: datetime
) -> CardDetail:
    document = document_of(card, index)
    brief, record = split_rows(card.rows)
    own = cited_path(card)
    return CardDetail(
        card=card,
        summary=summarize(card, index, now),
        brief=brief,
        record=record,
        document=document,
        other_citations=[c for c in card.citations if c != own],
        history=history,
    )
