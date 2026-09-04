"""Concurrency is visible before Start (INTENT.md lesson 4): the plan's
footprint against what is running."""

from board.collision import footprint, verdict
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
    said = verdict(
        mine,
        editing={"#7's lane": {"board/moves.py"}},
        declared={"#9's lane": {"api/app.py"}},
    )
    assert said.verdict == CollisionVerdict.COLLIDES
    assert said.sentence == "#7's lane is editing board/moves.py right now."
    assert said.files == ["board/moves.py"]
    declared_only = verdict(
        mine, editing={"#7's lane": set()}, declared={"#9's lane": {"api/app.py"}}
    )
    assert declared_only.verdict == CollisionVerdict.COLLIDES
    assert "has not opened api/app.py yet" in declared_only.sentence


def test_clear_and_unknown_say_so():
    assert verdict({"a.py"}, editing={}, declared={}).verdict == CollisionVerdict.CLEAR
    unknown = verdict(set(), editing={"x": {"a.py"}}, declared={})
    assert unknown.verdict == CollisionVerdict.UNKNOWN and "names no files" in unknown.sentence
