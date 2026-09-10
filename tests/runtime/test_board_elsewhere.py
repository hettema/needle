"""The board serves from the other machine (card #83, item 3): a machine
that is not the board's hands every verb that opens the board's store to
the board's machine over the same wire the board reads it by, a fold's git
runs back on the machine that holds the lane, and every machine's clone is
levelled at the pass. The other machine is the second floor of
`test_machines.py`, reached by the stand-in `ssh`.
"""

import json
from pathlib import Path

from api.cli import main
from infrastructure.store import Store
from tests.floor import Floor
from tests.runtime.test_machines import ground, quick, two_machines  # noqa: F401 — fixtures

__all__ = ["ground", "quick", "two_machines"]


def test_a_board_verb_on_a_machine_that_is_not_the_boards_runs_where_the_board_is(
    machine_floor: Floor, tmp_path: Path, capfd
):
    """`needle board rented` on this floor makes every verb that opens the
    board's store run on the rented floor over the wire, so a session here
    writes the one board and never a copy; `serve` here refuses; a runtime
    verb still answers from this machine's own ledger; `board here` takes
    it back."""
    other = machine_floor.lay_host("rented")
    assert main(["machine", "add", "rented", "--host", "rented"]) == 0
    assert main(["board"]) == 0
    assert "serves from this machine" in capfd.readouterr().out
    assert main(["board", "moon"]) == 1
    assert "no machine named 'moon'" in capfd.readouterr().err
    assert main(["board", "rented"]) == 0
    assert "serves from rented (rented)" in capfd.readouterr().out
    assert (tmp_path / "board.json").is_file()
    assert main(["board"]) == 0
    assert "runs there over ssh, as `uv --project " in capfd.readouterr().out
    # A project registered from here lands in the rented floor's store, and
    # the list of projects is read from there; this floor's store has none.
    corpus = tmp_path / "far-corpus"
    (corpus / "docs" / "plans").mkdir(parents=True)
    assert main(["add", str(corpus), "--slug", "far"]) == 0
    assert main(["projects"]) == 0
    assert "far" in capfd.readouterr().out
    theirs = Store(other.root / "needle.db")
    try:
        assert [p.slug for p in theirs.projects()] == ["far"]
    finally:
        theirs.close()
    mine = Store(tmp_path / "board.db")
    try:
        assert mine.projects() == []
    finally:
        mine.close()
    words = [" ".join(c["words"]) for c in machine_floor.state().get("ssh_calls", [])]
    assert any("needle add " in w for w in words) and any("needle projects" in w for w in words)
    # The runtime's verbs answer for this machine, from its own store.
    assert main(["machines"]) == 0
    assert "rented  horsepower" in capfd.readouterr().out
    assert main(["serve"]) == 1
    assert "serves from rented (rented)" in capfd.readouterr().err
    # The board's machine not answering is said in its name, with ssh's exit.
    machine_floor.host_down("rented")
    assert main(["projects"]) == 255
    assert "could not be reached; `needle projects` did not run" in capfd.readouterr().err
    machine_floor.host_down("rented", False)
    # A file that no longer says where the board is refuses, never falls
    # back to the store here.
    (tmp_path / "board.json").write_text("{}\n")
    assert main(["projects"]) == 1
    assert "does not say where the board is" in capfd.readouterr().err
    assert main(["board", "here"]) == 0
    assert not (tmp_path / "board.json").exists()
    assert "serves from this machine" in capfd.readouterr().out
    assert main(["projects"]) == 0
    assert capfd.readouterr().out.strip() == ""


def test_a_fold_asked_of_the_board_pushes_from_the_machine_that_holds_the_lane(
    two_machines, tmp_path: Path, machine_floor: Floor
):
    """The board's `fold` runs its git where the worktree is: a lane on the
    rented floor is pushed by that floor's `needle push`, and every
    machine's clone is levelled at the pass, each under its own name."""
    from tests.runtime.test_git import lane, sh

    runtime, _ = two_machines
    origin = tmp_path / "origin.git"
    origin.mkdir()
    sh(origin, "init", "--bare", "-b", "develop")
    checkout = tmp_path / "checkout"
    sh(tmp_path, "clone", "-q", str(origin), str(checkout))
    sh(checkout, "checkout", "-q", "-b", "develop")
    (checkout / "README.md").write_text("one\n")
    sh(checkout, "add", "README.md")
    sh(checkout, "commit", "-q", "-m", "one")
    sh(checkout, "push", "-q", "origin", "develop", "develop:main")
    sh(checkout, "fetch", "-q", "origin")
    path = lane(checkout, "card-7-far")
    (path / "README.md").write_text("two\n")
    sh(path, "add", "README.md")
    sh(path, "commit", "-q", "-m", "two")
    runtime._lane_machines[str(path)] = "rented"
    before = len(machine_floor.state().get("ssh_calls", []))
    folded = runtime.fold(str(path), promote_main=False)
    assert folded.pushed and folded.tip == sh(origin, "rev-parse", "develop")
    levelled = runtime.level_everywhere(str(checkout))
    assert [m.name for m, _ in levelled] == ["laptop", "rented"]
    assert all(r.level is True for _, r in levelled), [r.note for _, r in levelled]
    asked = [" ".join(c["words"]) for c in machine_floor.state().get("ssh_calls", [])[before:]]
    assert any(f"needle push --worktree {path} --json" in a for a in asked)
    assert any(f"needle level {checkout} --json" in a for a in asked)
    # A lane here is pushed here, with no wire.
    runtime._lane_machines[str(path)] = "laptop"
    count = len(machine_floor.state().get("ssh_calls", []))
    assert runtime.fold(str(path), promote_main=False).pushed
    assert len(machine_floor.state().get("ssh_calls", [])) == count
    # The machine that holds the lane not answering is a fold that did not
    # happen, in its name; a clone there is a note, never a stop.
    runtime._lane_machines[str(path)] = "rented"
    machine_floor.host_down("rented")
    refused = runtime.fold(str(path), promote_main=False)
    assert not refused.pushed and refused.words.startswith("rented holds the lane")
    levelled = runtime.level_everywhere(str(checkout))
    assert levelled[0][1].level is True
    assert levelled[1][1].level is None and "rented" in (levelled[1][1].note or "")


def test_a_machines_host_is_rewritten_only_when_the_host_is_that_machine(
    machine_floor: Floor, ground: Path, capsys
):
    other = machine_floor.lay_host("rented")
    assert main(["machine", "add", "laptop", "--desktop", "--ground", str(ground)]) == 0
    assert main(["machine", "add", "far", "--host", "rented"]) == 0
    capsys.readouterr()
    assert main(["machine", "host", "far", "nowhere"]) == 1
    assert "could not reach nowhere" in capsys.readouterr().err
    assert main(["machine", "host", "laptop", "rented"]) == 1
    err = capsys.readouterr().err
    assert "rented is not laptop" in err and other.machine_id in err
    assert main(["machine", "host", "ghost", "rented"]) == 1
    assert "no machine named 'ghost'" in capsys.readouterr().err
    assert main(["machine", "host", "far", "rented"]) == 0
    assert capsys.readouterr().out.strip() == "far: reached as rented"
    assert main(["machines", "--json"]) == 0
    rows = {r["machine"]["name"]: r["machine"]["host"] for r in json.loads(capsys.readouterr().out)}
    assert rows == {"laptop": None, "far": "rented"}
