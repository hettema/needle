"""The one reason a Start waits on another card: the plan's own word.

A plan that genuinely cannot run beside another says so in its head, on
the `**Sequencing:**` line, in the board's vocabulary — `#403` for this
project, `Needle #20`, `omarchy #17` for another — and the board closes
Start while any named card is not in Executed or Done, then opens it by
itself the read after the last one ships (the plan "as many lanes as the
machine can hold", item 2; ruling 3: inferring incompatibility from
terrain is the lock under another name). The parser reads the names
(`board/parse.py::sequenced_cards_of`); this module places them on the
boards and says where each stands. Pure: the caller hands in the projects
and a way to find a card.
"""

from collections.abc import Callable

from domain.card import Card
from domain.column import Column
from domain.document import SequencedCard
from domain.lane import Wait

SHIPPED: frozenset[Column] = frozenset({Column.EXECUTED, Column.DONE})
"""Where a named card no longer holds a Start."""


def _project_of(words: str | None, here: str, projects: dict[str, str]) -> str | None:
    """The project the words before a `#` name — by slug or by name, the
    last one or two words — or this project when there are none; None when
    the words name no project the board holds, which makes them prose."""
    if not words:
        return here
    parts = words.lower().split()
    tails = [" ".join(parts[-k:]) for k in range(1, min(2, len(parts)) + 1)]
    tails = [t.removesuffix("'s").removesuffix("’s") for t in tails] + tails
    for slug, name in projects.items():
        if slug.lower() in tails or name.lower() in tails:
            return slug
    return None


def waits_for(
    named: list[SequencedCard],
    *,
    here: str,
    projects: dict[str, str],
    find: Callable[[str, int], Card | None],
) -> list[Wait]:
    """Every card the line names, placed: which board, which column, and
    whether it has shipped. `projects` maps each slug the board holds to its
    name. The reading stops at the first name the board cannot place: words
    before a `#` that are no project's are prose, and so is everything after
    them — "beside #15" holds nothing, "after Needle #20" holds."""
    out: list[Wait] = []
    for card in named:
        slug = _project_of(card.words, here, projects)
        if slug is None:
            break
        found = find(slug, card.number)
        column = found.place.column if found is not None else None
        out.append(
            Wait(
                label=f"#{card.number}" if slug == here else f"{projects[slug]} #{card.number}",
                project=slug,
                number=card.number,
                column=column,
                shipped=column in SHIPPED,
            )
        )
    return out


def holding(waits: list[Wait]) -> list[Wait]:
    """The named cards that still hold the Start."""
    return [w for w in waits if not w.shipped]


def where(wait: Wait) -> str:
    return f"{wait.label} ({wait.column.value if wait.column is not None else 'not on the board'})"
