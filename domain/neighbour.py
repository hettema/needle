"""What a live document sits beside: the other live documents on its ground
(card #69).

A lane's `Collision` (domain/lane.py) is about two sessions editing now,
and a `Wait` is a plan's own hold; a document's neighbours are documents at
rest, read against each other on every corpus read, so they are a shape of
their own — born after that search (the plan's ruling "one footprint, two
readers"). The board retrieves; it never judges: a neighbour by words is a
candidate, and whether two intents can both hold is the session's to say
with both in front of it, or the owner's (ruling 3).
"""

from datetime import date
from enum import StrEnum

from pydantic import BaseModel

from domain.document import DocumentKind


class NeighbourGround(StrEnum):
    """How two documents came to be neighbours."""

    FILES = "files"
    """Both name a repository path that few other documents name."""
    WORDS = "words"
    """A candidate by the rare words of its title and intent — retrieval,
    never a verdict."""


class Neighbour(BaseModel):
    number: int
    title: str
    essence: str | None
    """The first sentence of the neighbour's intent: what the brief carries
    so the session judges by intent, never by title alone."""
    kind: DocumentKind
    path: str
    ground: NeighbourGround
    files: list[str]
    """The paths both name, when the ground is files."""
    words: list[str]
    """The words both use, when the ground is words."""
    named: bool
    """Whether this document names the neighbour: its card, its Sequencing
    line, or the neighbour's path anywhere in the text."""
    rulings: list[str]
    """The bold leads of the neighbour's `## Rulings` section, when it has
    one: what a plan written beside it must not reverse unknowingly."""


class Beside(BaseModel):
    """One document's neighbours, as the card and every writing brief show
    them, and whether the head counts it."""

    neighbours: list[Neighbour]
    unnamed: list[int]
    """The file-ground neighbours this document does not name — the
    failure item 1 counts. A word candidate is never here (ruling 3)."""
    counted: bool
    """Whether the head counts this document among those beside a
    neighbour they do not name: unnamed is nonempty and the document was
    born once the reader existed (`COUNTED_FROM`); a document born blind
    before that shows its neighbours as a quiet fact."""
    born: date | None
    """The day the document's card was born, which decides `counted`."""
    sentence: str | None
    """The face line: the neighbours in one plain sentence, or None when the
    document sits beside nothing."""
    clears: str | None
    """Who clears the count and by what act, when it is counted."""
