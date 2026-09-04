"""The eight columns and their grammar.

The columns are the owner's, carried from Needle 0.1. Their definitions are
data rather than prose in a README because the page shows them one hover away
and a session reads them as the rule for where a card may go; a definition
that lived only in a document would drift from the one on the screen.
"""

from enum import StrEnum

from pydantic import BaseModel


class Column(StrEnum):
    BACKLOG = "Backlog"
    PLANNED = "Planned"
    UP_NEXT = "Up next"
    EXECUTING = "Executing"
    DECISION_MOMENT = "Decision moment"
    EXECUTED = "Executed"
    DONE = "Done"
    NOT_NOW = "Not now"


class ColumnDefinition(BaseModel):
    """What a column means, whose move it is, and how the page treats it."""

    column: Column
    note: str
    """The one line under the column head."""
    definition: list[str]
    """The paragraphs of the hover definition, in order."""
    moved_by: str
    """Whose move a card into this column is; shown under the definition."""
    ranked: bool
    """Position is the owner's priority and the page numbers the cards."""
    yours: bool
    """The column is the owner's move and reads as such."""
    furled_on_laptop: bool
    """Starts folded to a rail on a laptop screen (owner ruling 3)."""


COLUMN_DEFINITIONS: list[ColumnDefinition] = [
    ColumnDefinition(
        column=Column.BACKLOG,
        note="Ideas written up as suggestions, ranked below the line. Planning one is what "
        "promotes it.",
        definition=[
            "Written ideas. A suggestion exists on disk; nobody has planned it yet.",
            "Planning one is what promotes it — the column is the stage of the writing, never "
            "a label somebody applied.",
        ],
        moved_by="you, or by a plan appearing",
        ranked=False,
        yours=False,
        furled_on_laptop=False,
    ),
    ColumnDefinition(
        column=Column.PLANNED,
        note="The thinking is done and written — a plan exists, waiting its turn for the queue.",
        definition=[
            "The thinking is done and written. A plan exists, waiting its turn for the queue.",
            "A card here without a live plan is a card in the wrong column, and the board says so.",
        ],
        moved_by="you",
        ranked=False,
        yours=False,
        furled_on_laptop=False,
    ),
    ColumnDefinition(
        column=Column.UP_NEXT,
        note="What we should do next, ranked. Position is rank — the proposed order, yours to "
        "override by moving.",
        definition=[
            "What we should do next, ranked. Position is priority and it is true — nothing "
            "re-sorts behind your back.",
            "The ranking rule proposes an order; you override it by moving a card, and "
            "repeated overrides are evidence the rule is misnamed, not noise.",
        ],
        moved_by="you — the one gate that is yours alone",
        ranked=True,
        yours=False,
        furled_on_laptop=False,
    ),
    ColumnDefinition(
        column=Column.EXECUTING,
        note="In flight now.",
        definition=[
            "Hands are on it.",
            "From slice 02 this column is a machine fact: the board moves a card in the moment "
            "a live session has hands on it, and out again to wherever the work says. In this "
            "slice nothing runs, so it is yours to move.",
        ],
        moved_by="the machine, from slice 02",
        ranked=False,
        yours=False,
        furled_on_laptop=False,
    ),
    ColumnDefinition(
        column=Column.DECISION_MOMENT,
        note="Your move. Top group unblocks build lanes; bottom group is actions and sign-offs "
        "elsewhere.",
        definition=[
            "Your move. Nothing here proceeds without a word from you.",
            "Two groups: what unblocks a build lane, and what is an action or a sign-off "
            "somewhere else. Work whose completion still needs your verification sits here, "
            "never in a shipped column.",
        ],
        moved_by="you, or by the machine when work finished with nothing said",
        ranked=False,
        yours=True,
        furled_on_laptop=False,
    ),
    ColumnDefinition(
        column=Column.EXECUTED,
        note="Built and archived; waiting for the signal that says it delivered.",
        definition=[
            "Built work, its plan archived, waiting for the signal that says it delivered.",
            "A card enters here with its WATCH row naming that signal. Done is a closed loop, "
            "not a claim: this is never where cards go to be forgotten.",
        ],
        moved_by="you, in this slice; the close of a session's work, from slice 03",
        ranked=False,
        yours=False,
        furled_on_laptop=True,
    ),
    ColumnDefinition(
        column=Column.DONE,
        note="The signal arrived.",
        definition=[
            "The signal named on the card arrived and somebody read it.",
            "From slice 03 the board or a session reads the signal and moves the card here itself.",
        ],
        moved_by="you, in this slice; the board or a session, from slice 03",
        ranked=False,
        yours=False,
        furled_on_laptop=True,
    ),
    ColumnDefinition(
        column=Column.NOT_NOW,
        note="Parked in writing, with a wake trigger.",
        definition=[
            "Deliberately not on the plate. The idea waits in writing, with what would wake it.",
            "A card here is a ruling, not a forgetting: it says why not, and when again.",
        ],
        moved_by="you",
        ranked=False,
        yours=False,
        furled_on_laptop=True,
    ),
]

COLUMN_BY_NAME: dict[Column, ColumnDefinition] = {d.column: d for d in COLUMN_DEFINITIONS}

DEFECTS_RAIL = "Defects"
"""The name of Backlog's one machine-kept group: the defects rail (plan 06,
item 2). A suggestion whose document says `Kind: defect` sits here and one
that says idea does not; the corpus keeps it so on every read, so the rail
is a lens on what is written, never a label somebody applied."""

DEFECTS_RAIL_POSITION = -1
"""Before every group the owner named, which start at 0."""
