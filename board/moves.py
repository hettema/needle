"""Where a card lands when it is moved.

A column is an ordered list of groups and a card lives in exactly one, so a
move is always "into this group, at this index". There is no flat position
that has to be resolved into a group afterwards — 0.1's review finding 8, a
drop that landed in a phantom group at the top, cannot be expressed here.
"""

from pydantic import BaseModel

from domain.card import Place
from domain.column import Column


class GroupLayout(BaseModel):
    column: Column
    name: str | None
    numbers: list[int]
    """Card numbers in position order."""


class MoveResult(BaseModel):
    from_place: Place
    to_place: Place
    """Where the card actually landed; the position is clamped to the group."""
    source: GroupLayout
    target: GroupLayout
    changed: bool


class MoveRefused(Exception):
    """The move cannot be made and nothing has changed; the message is the reason."""


def find_place(layout: list[GroupLayout], number: int) -> Place:
    for group in layout:
        if number in group.numbers:
            return Place(
                column=group.column, group=group.name, position=group.numbers.index(number)
            )
    raise MoveRefused(f"There is no card #{number} on this board.")


def apply_move(layout: list[GroupLayout], number: int, to: Place) -> MoveResult:
    from_place = find_place(layout, number)
    source = next(g for g in layout if g.column == from_place.column and g.name == from_place.group)
    target = next((g for g in layout if g.column == to.column and g.name == to.group), None)
    if target is None:
        where = f'group "{to.group}"' if to.group is not None else "the unnamed group"
        raise MoveRefused(f"{to.column} has no {where}.")

    source_numbers = [n for n in source.numbers if n != number]
    if target is source:
        target_numbers = source_numbers
    else:
        target_numbers = [n for n in target.numbers if n != number]
    position = max(0, min(to.position, len(target_numbers)))
    target_numbers.insert(position, number)
    landed = Place(column=target.column, group=target.name, position=position)

    new_source = GroupLayout(column=source.column, name=source.name, numbers=source_numbers)
    new_target = GroupLayout(column=target.column, name=target.name, numbers=target_numbers)
    if target is source:
        new_source = new_target
    return MoveResult(
        from_place=from_place,
        to_place=landed,
        source=new_source,
        target=new_target,
        changed=landed != from_place,
    )
