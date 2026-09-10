"""Every lane's scope carries the floor as its high mark, whoever made the
scope (card #107): the runtime reads the mark on every pass and sets it where
it is missing, and one scope whose set fails costs no other its mark."""

import subprocess

from domain.dial import lane_mark
from infrastructure.store import Store
from runtime import machine
from runtime.remote import Remote
from tests.runtime.test_machines import NOW, ground, quick, two_machines  # noqa: F401 — fixtures

__all__ = ["NOW", "ground", "quick", "two_machines"]

FLOOR = 5 * 1024**3
GB = 1024**3
A, B, C = "needle-card-1-a.scope", "needle-card-2-b.scope", "needle-card-3-c.scope"


def _shown(units, properties):
    marks = {A: "infinity", B: "infinity", C: str(FLOOR)}
    return {u: {"Id": u, "MemoryHigh": marks[u]} for u in units}


def test_one_scope_whose_set_times_out_costs_no_other_its_mark(monkeypatch):
    """Codex's reading of the fix (2026-09-09): a timeout on one unit raised
    out of the whole set, so the scope before it was never answered and the
    one after it never tried. Here B times out; A is set and answered, C
    already holds the mark and is left alone."""
    asked: list[list[str]] = []

    def run(argv, **kwargs):
        asked.append(argv)
        if B in argv:
            raise subprocess.TimeoutExpired(argv, 10)
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(machine, "show_units", _shown)
    monkeypatch.setattr(machine, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(machine, "run", run)
    held = machine.hold_scopes_at([A, B, C], FLOOR)
    assert held == [A]
    assert [a[4] for a in asked] == [A, B], "C already holds the mark; B was tried"
    assert asked[0][1:4] == ["--user", "set-property", "--runtime"]
    assert asked[0][5] == f"MemoryHigh={FLOOR}"


def test_a_lane_on_the_horsepower_is_held_to_what_the_machine_has_above_the_floor(
    two_machines, machine_floor
):
    """The desktop's 5 GB is a rule for a machine the owner's screen shares;
    on the rented machine it slowed Hello Revenue #503 for two hours with
    24 GB free (2026-09-10). A lane there is held to what the machine has
    above the floor, and the reading says so: the mark, and a lane past it
    in those words. The rented floor knows itself from its own row, as the
    record lays it."""
    runtime, other = two_machines
    rented = next(m for m in runtime.machines() if m.name == "rented")
    theirs = Store(other.root / "needle.db")
    try:
        theirs.add_machine(rented)
    finally:
        theirs.close()
    unit = "needle-card-503-a-website.scope"
    machine_floor.update(
        scopes={
            unit: {"ActiveState": "active", "MemoryCurrent": str(6 * GB), "MemoryHigh": "infinity"}
        }
    )
    reading = Remote(rented).room(hold=True)
    assert reading.mark == 27 * GB, "32 GB total, the 5 GB floor kept"
    assert reading.marked == [unit]
    sets = [c for c in machine_floor.state()["systemctl_calls"] if "set-property" in c]
    assert sets[-1][-2:] == [unit, f"MemoryHigh={27 * GB}"]
    assert not reading.full, "6 GB is room on the horsepower"
    machine_floor.update(
        scopes={
            unit: {
                "ActiveState": "active",
                "MemoryCurrent": str(28 * GB),
                "MemoryHigh": str(27 * GB),
            }
        }
    )
    reading = Remote(rented).room(hold=True)
    assert reading.sentence == (
        "the machine is full: needle-card-503-a-website.scope holds 28.0 GB, "
        "past the 27 GB a lane may hold here"
    )
    # The desktop keeps the floor as its mark, and its words.
    here = runtime.room(hold=True)
    assert here.mark == FLOOR and here.full
    assert here.sentence is not None and here.sentence.endswith(
        "holds 28.0 GB, past the 5 GB floor"
    )


def test_the_mark_is_the_floor_wherever_the_total_is_not_known():
    """A total nobody read hands out no room: the rule is the floor on the
    desktop, on a horsepower machine whose memory was not read, and on one
    with no more than the floor."""
    assert lane_mark(True, 32 * GB) == FLOOR
    assert lane_mark(False, 32 * GB) == 27 * GB
    assert lane_mark(False, 0) == FLOOR
    assert lane_mark(False, 4 * GB) == FLOOR
