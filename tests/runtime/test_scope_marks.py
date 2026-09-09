"""Every lane's scope carries the floor as its high mark, whoever made the
scope (card #107): the runtime reads the mark on every pass and sets it where
it is missing, and one scope whose set fails costs no other its mark."""

import subprocess

from runtime import machine

FLOOR = 5 * 1024**3
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
