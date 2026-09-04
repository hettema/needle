"""Reading Needle 0.1's card file, once, into the shape the store takes.

The file is `columns → groups → cards`, with rows as `[label, text]` pairs, a
`gate` field, `ch` tag letters and a `deep` field carrying `<span
class="file">` citations. Everything the owner ranked is kept: column, group,
position, rows, tags, citations. What is dropped is 0.1's runtime — `lanes`,
`lane`, `progress` — and its three machine-born asks, because Needle states
those facts as counts and a card nobody withdraws would sit there forever.
"""

import re

from pydantic import BaseModel, ConfigDict, ValidationError

from board.text import file_citations, html_to_text, prose_without_citations
from domain.card import DocumentLink, Place
from domain.column import Column
from domain.corpus import CorpusIndex
from domain.document import DocumentKind
from domain.gate import Gate
from domain.row import Row, RowKind

TAG_LEGEND: dict[str, str] = {
    "A": "Live sooner",
    "B": "Keep winning",
    "C": "Learning",
    "D": "Trust",
    "U": "Urgent",
    "K": "Sept 1",
    "R": "Ruling",
    "X": "Action",
    "M": "Comp",
    "V": "Verify",
    "$": "HR ops",
    "W": "Watch",
}

_CITATION = re.compile(r"^docs/(plans|slice-suggestions)/(done/)?(.+?)(?:\.md)?$")


class ImportRefused(Exception):
    """The file holds something the board has no type for; nothing was written."""


class Card01(BaseModel):
    model_config = ConfigDict(extra="allow")

    t: str
    id: int
    b: list[tuple[str, str]] = []
    ch: list[str] = []
    gate: str | None = None
    deep: str = ""
    citations: list[str] = []
    board: str | None = None


class Group01(BaseModel):
    g: str | None
    cards: list[Card01]


class Column01(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    groups: list[Group01]


class File01(BaseModel):
    model_config = ConfigDict(extra="allow")

    cols: list[Column01]
    nextId: int
    retired: dict[str, str] = {}


class ImportedGroup(BaseModel):
    column: Column
    name: str | None
    position: int


class ImportedCard(BaseModel):
    number: int
    place: Place
    title: str
    gate: Gate | None
    tags: list[str]
    deep: str
    citations: list[str]
    link: DocumentLink | None


class ImportedRows(BaseModel):
    number: int
    rows: list[Row]


class Retired(BaseModel):
    number: int
    reason: str


class SkippedAsk(BaseModel):
    number: int
    title: str
    alarm: str


class Import01(BaseModel):
    groups: list[ImportedGroup]
    cards: list[ImportedCard]
    rows: list[ImportedRows]
    retired: list[Retired]
    skipped_asks: list[SkippedAsk]
    next_number: int


def link_from_citations(citations: list[str], index: CorpusIndex) -> DocumentLink | None:
    """The first plan or suggestion cited is the card's document."""
    for citation in citations:
        match = _CITATION.match(citation.strip())
        if not match:
            continue
        kind = DocumentKind.PLAN if match.group(1) == "plans" else DocumentKind.SUGGESTION
        stem = match.group(3)
        archived = match.group(2) is not None
        document = index.find(kind, stem)
        if document is not None:
            return DocumentLink(
                kind=kind, stem=stem, title=document.title, archived=document.archived
            )
        return DocumentLink(kind=kind, stem=stem, title="", archived=archived)
    return None


def _rows(card: Card01) -> list[Row]:
    rows: list[Row] = []
    for label, text in card.b:
        try:
            kind = RowKind(label)
        except ValueError as error:
            raise ImportRefused(
                f'Card #{card.id} carries a row labelled "{label}", which the board has no '
                "row kind for. Add it to domain.row.RowKind with its half, then import again."
            ) from error
        rows.append(Row(kind=kind, text=html_to_text(text)))
    return rows


def _gate(card: Card01) -> Gate | None:
    if card.gate is None:
        return None
    try:
        return Gate(card.gate.lower())
    except ValueError as error:
        raise ImportRefused(
            f'Card #{card.id} carries the gate "{card.gate}", which is not one of '
            f"{', '.join(g.value for g in Gate)}."
        ) from error


def _tags(card: Card01) -> list[str]:
    tags: list[str] = []
    for letter in card.ch:
        if letter not in TAG_LEGEND:
            raise ImportRefused(
                f'Card #{card.id} carries the tag letter "{letter}", which 0.1\'s legend '
                "does not name. Add it to board.import_01.TAG_LEGEND, then import again."
            )
        tags.append(TAG_LEGEND[letter])
    return tags


def read_01(payload: object, index: CorpusIndex) -> Import01:
    try:
        file = File01.model_validate(payload)
    except ValidationError as error:
        raise ImportRefused(f"The card file is not in 0.1's shape: {error}") from error

    groups: list[ImportedGroup] = []
    cards: list[ImportedCard] = []
    rows: list[ImportedRows] = []
    skipped: list[SkippedAsk] = []
    seen: set[int] = set()
    for column01 in file.cols:
        try:
            column = Column(column01.name)
        except ValueError as error:
            raise ImportRefused(
                f'The file has a column named "{column01.name}", which the board does not.'
            ) from error
        for group_position, group01 in enumerate(column01.groups):
            groups.append(ImportedGroup(column=column, name=group01.g, position=group_position))
            position = 0
            for card01 in group01.cards:
                if card01.id in seen:
                    raise ImportRefused(f"Card #{card01.id} appears twice in the file.")
                seen.add(card01.id)
                if card01.board is not None:
                    skipped.append(SkippedAsk(number=card01.id, title=card01.t, alarm=card01.board))
                    continue
                citations = file_citations(card01.deep) + [
                    c for c in card01.citations if c not in file_citations(card01.deep)
                ]
                cards.append(
                    ImportedCard(
                        number=card01.id,
                        place=Place(column=column, group=group01.g, position=position),
                        title=html_to_text(card01.t),
                        gate=_gate(card01),
                        tags=_tags(card01),
                        deep=prose_without_citations(card01.deep),
                        citations=citations,
                        link=link_from_citations(citations, index),
                    )
                )
                rows.append(ImportedRows(number=card01.id, rows=_rows(card01)))
                position += 1

    retired = [Retired(number=int(n), reason=reason) for n, reason in file.retired.items()]
    highest = max([c.number for c in cards] + [r.number for r in retired] + [0])
    return Import01(
        groups=groups,
        cards=cards,
        rows=rows,
        retired=retired,
        skipped_asks=skipped,
        next_number=max(file.nextId, highest + 1),
    )
