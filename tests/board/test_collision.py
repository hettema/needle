"""Concurrency is visible before Start (INTENT.md lesson 4): the plan's
footprint against what is running."""

from board.collision import drift, footprint, verdict
from domain.lane import CollisionVerdict

PLAN = """# A plan

Touches `api/app.py`, `board/moves.py::apply_move` and `frontend/src/App.tsx:12`,
cites `docs/plans/done/old.md`, and names `nothing/here.py` which does not exist.
"""


def test_the_footprint_is_the_named_files_that_exist():
    exists = {"api/app.py", "board/moves.py", "frontend/src/App.tsx", "docs/plans/done/old.md"}
    assert footprint(PLAN, exists.__contains__) == exists


def test_an_edit_in_progress_is_reported_before_a_declared_overlap():
    mine = {"api/app.py", "board/moves.py"}
    said = verdict(mine, editing={7: {"board/moves.py"}}, declared={9: {"api/app.py"}})
    assert said.verdict == CollisionVerdict.COLLIDES
    assert said.sentence == "#7's lane is editing board/moves.py right now."
    assert said.files == ["board/moves.py"] and said.cards == [7]
    declared_only = verdict(mine, editing={7: set()}, declared={9: {"api/app.py"}})
    assert declared_only.verdict == CollisionVerdict.COLLIDES
    assert "has not opened api/app.py yet" in declared_only.sentence
    assert declared_only.cards == [9]


def test_clear_and_unknown_say_so():
    clear = verdict({"a.py"}, editing={}, declared={})
    assert clear.verdict == CollisionVerdict.CLEAR and clear.cards == []
    unknown = verdict(set(), editing={3: {"a.py"}}, declared={})
    assert unknown.verdict == CollisionVerdict.UNKNOWN and "names no files" in unknown.sentence


def test_two_live_lanes_editing_the_same_file_collide_on_both_sides_and_others_do_not():
    said = drift({7: {"a.py", "b.py", "shared.py"}, 9: {"shared.py", "c.py"}, 11: {"d.py"}})
    seven, nine = said[7], said[9]
    assert seven is not None and nine is not None and said[11] is None
    assert seven.verdict == CollisionVerdict.COLLIDES and seven.files == ["shared.py"]
    assert seven.sentence == "#9's lane is also editing shared.py." and seven.cards == [9]
    assert nine.sentence == "#7's lane is also editing shared.py." and nine.cards == [7]
    assert drift({}) == {} and drift({7: {"a.py"}}) == {7: None}
