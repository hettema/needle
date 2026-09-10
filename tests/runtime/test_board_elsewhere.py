"""The board serves from the other machine (card #83, item 3): a machine
that is not the board's hands every verb that opens the board's store to
the board's machine over the same wire the board reads it by, a fold's git
runs back on the machine that holds the lane, and every machine's clone is
levelled at the pass. The other machine is the second floor of
`test_machines.py`, reached by the stand-in `ssh`.
"""

import json
from pathlib import Path

import pytest

from api.cli import main
from infrastructure.store import Store
from runtime.service import Runtime
from tests.floor import Floor
from tests.runtime.test_machines import NOW, ground, quick, two_machines  # noqa: F401 — fixtures

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
    # The registry is the board's too: `machines` runs there (the rented
    # floor's store has no rows, so it names itself alone); a runtime verb
    # answers for this machine from its own store, with no wire.
    assert main(["machines"]) == 0
    assert "(here)  desktop" in capfd.readouterr().out
    assert any(
        "needle machines" in " ".join(c["words"]) for c in machine_floor.state()["ssh_calls"]
    )
    count = len(machine_floor.state()["ssh_calls"])
    assert main(["room"]) == 0
    assert "available" in capfd.readouterr().out
    assert len(machine_floor.state()["ssh_calls"]) == count
    assert main(["serve"]) == 1
    assert "serves from rented (rented)" in capfd.readouterr().err
    # The board's machine not answering is said in its name, with ssh's exit.
    machine_floor.host_down("rented")
    assert main(["projects"]) == 255
    err = capfd.readouterr().err
    assert "the line to it was lost: whether `needle projects` ran there is not known" in err
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
    assert runtime.level(str(checkout)).level is True
    levelled = runtime.level_elsewhere(str(checkout))
    assert [m.name for m, _ in levelled] == ["rented"]
    assert levelled[0][1].level is True, levelled[0][1].note
    asked = [" ".join(c["words"]) for c in machine_floor.state().get("ssh_calls", [])[before:]]
    assert any(f"needle push --worktree {path} --json" in a for a in asked)
    assert any(f"needle level {checkout} --json" in a for a in asked)
    # A lane here is pushed here, with no wire.
    runtime._lane_machines[str(path)] = "laptop"
    count = len(machine_floor.state().get("ssh_calls", []))
    assert runtime.fold(str(path), promote_main=False).pushed
    assert len(machine_floor.state().get("ssh_calls", [])) == count
    # A fresh runtime — a verb in its own process — knows where the lane
    # is from the board's own record, not only from this pass's read.
    from domain.lane import LaneRecord

    runtime.store.record_lane(
        LaneRecord(
            project="p",
            card_number=7,
            name="card-7-far",
            path=str(path),
            branch="card-7-far",
            birth=None,
            tip=None,
            first_seen=NOW,
            last_seen=NOW,
            gone_at=None,
            folded_at=None,
            trunk_synced_at=None,
            main_synced_at=None,
            machine="rented",
        )
    )
    fresh = Runtime(runtime.store)
    assert fresh.lane_machine(str(path)).name == "rented"
    # The machine that holds the lane not answering is a push whose fate is
    # unknown, in its name; a clone there is a note, never a stop.
    machine_floor.host_down("rented")
    refused = fresh.fold(str(path), promote_main=False)
    assert not refused.pushed and refused.words.startswith("rented holds the lane")
    assert "whether it pushed is unknown" in refused.words
    levelled = fresh.level_elsewhere(str(checkout))
    assert levelled[0][1].level is None and "rented" in (levelled[0][1].note or "")
    # A machine this pass already found unread is not asked again.
    fresh.unread["rented"] = "did not answer"
    count = len(machine_floor.state().get("ssh_calls", []))
    assert fresh.level_elsewhere(str(checkout))[0][1].note == "not levelled: did not answer"
    assert len(machine_floor.state().get("ssh_calls", [])) == count


def test_the_head_says_which_clones_are_not_level_on_each_machines_own_line(
    machine_floor: Floor, ground: Path, tmp_path: Path
):
    """The trunk's state is the board's own checkout's; another machine's
    stale clone is that machine's fact on the head's machine line (Codex's
    eighth pass on card #83)."""
    from api.board_cli import _board
    from tests.runtime.test_git import sh

    machine_floor.lay_host("rented", available_gb=24.0)
    origin = tmp_path / "origin.git"
    origin.mkdir()
    sh(origin, "init", "--bare", "-b", "develop")
    checkout = tmp_path / "checkout"
    sh(tmp_path, "clone", "-q", str(origin), str(checkout))
    sh(checkout, "checkout", "-q", "-b", "develop")
    (checkout / "docs" / "plans").mkdir(parents=True)
    (checkout / "README.md").write_text("one\n")
    sh(checkout, "add", "README.md")
    sh(checkout, "commit", "-q", "-m", "one")
    sh(checkout, "push", "-q", "origin", "develop", "develop:main")
    assert main(["add", str(checkout), "--slug", "p"]) == 0
    assert main(["machine", "add", "laptop", "--desktop", "--ground", str(ground)]) == 0
    assert main(["machine", "add", "rented", "--host", "rented"]) == 0
    store, live, runtime, loops, _ = _board()
    try:
        loops.level_trunks_now()
        loops.level_clones_now()
        loops.headroom_now()
        assert live.store.trunk("p").level is True and live.store.trunk("p").note is None
        assert [r.clones for r in loops._rooms] == [[], []]
        machine_floor.host_down("rented")
        loops.level_clones_now()
        loops.headroom_now()
        rented = next(r for r in loops._rooms if r.machine.name == "rented")
        assert rented.clones and rented.clones[0].startswith("p: ")
        assert live.store.trunk("p").level is True and live.store.trunk("p").note is None
    finally:
        store.close()


def test_a_machines_host_is_rewritten_only_when_the_host_is_that_machine(
    machine_floor: Floor, ground: Path, tmp_path: Path, capsys
):
    from domain.machine import Machine
    from runtime import machine as machine_mod
    from tests.runtime.test_machines import NOW

    other = machine_floor.lay_host("rented")
    # The machine this runtime names from its hostname, with no row, has
    # nothing to rewrite; a registered row with no host yet is the case.
    assert main(["machine", "host", machine_mod.hostname(), "rented"]) == 1
    assert "no machine named" in capsys.readouterr().err
    assert main(["machine", "add", "laptop", "--desktop", "--ground", str(ground)]) == 0
    mine = Store(tmp_path / "board.db")
    try:
        mine.add_machine(
            Machine(
                name="far",
                machine_id=other.machine_id,
                host=None,
                desktop=False,
                ground=None,
                command="needle",
                added_at=NOW,
            )
        )
    finally:
        mine.close()
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


def test_a_machine_that_is_not_the_boards_answers_for_itself_alone(
    machine_floor: Floor, ground: Path, tmp_path: Path
):
    """The moved store carries both machine rows on both machines. The
    board asks the other machine `sessions`; a runtime there that fanned
    out over its rows would ask the board's machine, which would ask it
    back (Codex's eighth pass on card #83). So a machine that hands its
    verbs away answers for itself only, and its registry verbs run on the
    board: a timing written from it lands in the board's store."""
    from domain.machine import BoardMachine

    other = machine_floor.lay_host("rented")
    assert main(["machine", "add", "laptop", "--desktop", "--ground", str(ground)]) == 0
    assert main(["machine", "add", "rented", "--host", "rented"]) == 0
    # The rented floor's store is the copied store: both rows, and its
    # board file names the laptop by a host the floor never laid.
    mine = Store(tmp_path / "board.db")
    theirs = Store(other.root / "needle.db")
    try:
        for row in mine.machines():
            host = "laptop" if row.name == "laptop" else None
            theirs.add_machine(row.model_copy(update={"host": host}))
    finally:
        theirs.close()
        mine.close()
    (other.root / "board.json").write_text(
        BoardMachine(name="laptop", host="laptop", command="needle").model_dump_json()
    )
    runtime = Runtime(Store(tmp_path / "board.db"))
    sessions = runtime.sessions()
    assert sessions == []
    hosts = [c["host"] for c in machine_floor.state().get("ssh_calls", [])]
    assert "rented" in hosts and "laptop" not in hosts
    assert "rented" not in runtime.unread
    # From the other side — the board now on the rented floor, this one
    # handing its verbs there — a registry write goes to the board and not
    # the ledger here: `machine timing` writes the board's row.
    runtime.store.close()
    (other.root / "board.json").unlink()
    (tmp_path / "board.json").write_text(
        BoardMachine(name="rented", host="rented", command="needle").model_dump_json()
    )
    assert main(["machine", "timing", "laptop", "pytest", "12.5"]) == 0
    theirs = Store(other.root / "needle.db")
    try:
        assert [t.seconds for t in theirs.timings("laptop")] == [12.5]
    finally:
        theirs.close()
    mine = Store(tmp_path / "board.db")
    try:
        assert mine.timings("laptop") == []
        alone = Runtime(mine).machines()
        assert [m.machine_id for m in alone] == [machine_floor.machine_id], (
            "a machine that is not the board's lists itself alone"
        )
    finally:
        mine.close()


def test_a_path_the_caller_gave_relative_to_its_directory_crosses_absolute(
    machine_floor: Floor, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capfd
):
    """The other side runs in a login's directory, not ours: `add .` and
    `fold --worktree .` are resolved here before they cross."""
    machine_floor.lay_host("rented")
    assert main(["machine", "add", "rented", "--host", "rented"]) == 0
    assert main(["board", "rented"]) == 0
    corpus = tmp_path / "near-corpus"
    (corpus / "docs" / "plans").mkdir(parents=True)
    monkeypatch.chdir(corpus)
    assert main(["add", ".", "--slug", "near"]) == 0
    capfd.readouterr()
    words = [" ".join(c["words"]) for c in machine_floor.state().get("ssh_calls", [])]
    assert any(f"needle add {corpus.resolve()} --slug near" in w for w in words)
    assert not any(" add . " in w for w in words)
    main(["fold", "--worktree", "."])
    words = [" ".join(c["words"]) for c in machine_floor.state().get("ssh_calls", [])]
    assert any(f"needle fold --worktree {corpus.resolve()}" in w for w in words)
