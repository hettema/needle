import pytest

from board.moves import GroupLayout, MoveRefused, apply_move, find_place
from domain.card import Place
from domain.column import Column


def layout() -> list[GroupLayout]:
    return [
        GroupLayout(column=Column.BACKLOG, name="Next", numbers=[1, 2, 3]),
        GroupLayout(column=Column.BACKLOG, name="Empty", numbers=[]),
        GroupLayout(column=Column.UP_NEXT, name=None, numbers=[10, 11]),
    ]


def test_a_card_is_found_where_it_sits():
    assert find_place(layout(), 2) == Place(column=Column.BACKLOG, group="Next", position=1)


def test_reordering_within_a_group_renumbers_contiguously():
    result = apply_move(layout(), 3, Place(column=Column.BACKLOG, group="Next", position=0))
    assert result.target.numbers == [3, 1, 2]
    assert result.to_place == Place(column=Column.BACKLOG, group="Next", position=0)
    assert result.changed


def test_a_named_group_receives_the_card_even_when_it_is_empty():
    result = apply_move(layout(), 2, Place(column=Column.BACKLOG, group="Empty", position=0))
    assert result.source.numbers == [1, 3]
    assert result.target.numbers == [2]


def test_a_move_across_columns_lands_at_the_index_asked_for():
    result = apply_move(layout(), 1, Place(column=Column.UP_NEXT, group=None, position=1))
    assert result.target.numbers == [10, 1, 11]
    assert result.from_place == Place(column=Column.BACKLOG, group="Next", position=0)


def test_a_position_past_the_end_lands_last_and_says_so():
    result = apply_move(layout(), 1, Place(column=Column.UP_NEXT, group=None, position=99))
    assert result.target.numbers == [10, 11, 1]
    assert result.to_place.position == 2


def test_a_move_to_where_the_card_already_is_changes_nothing():
    result = apply_move(layout(), 2, Place(column=Column.BACKLOG, group="Next", position=1))
    assert not result.changed
    assert result.target.numbers == [1, 2, 3]


def test_an_unknown_card_is_refused():
    with pytest.raises(MoveRefused, match="no card #9"):
        apply_move(layout(), 9, Place(column=Column.UP_NEXT, group=None, position=0))


def test_an_unknown_group_is_refused_and_names_itself():
    with pytest.raises(MoveRefused, match='Backlog has no group "Phantom"'):
        apply_move(layout(), 1, Place(column=Column.BACKLOG, group="Phantom", position=0))
    with pytest.raises(MoveRefused, match="Planned has no the unnamed group"):
        apply_move(layout(), 1, Place(column=Column.PLANNED, group=None, position=0))
