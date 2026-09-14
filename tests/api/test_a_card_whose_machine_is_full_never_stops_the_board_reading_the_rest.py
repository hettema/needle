"""A card whose machine is full never stops the board reading the rest
(card #148), on the floor: with the laptop full and the rented machine
with room, a beat opens the oldest reading that *can* open — a card of a
project the rented machine reads — and the cards of the laptop's own
record wait without holding anyone (item 1); a card left out says so on
its face once per spell, not once a beat, and once more when its reading
finally opens (item 2); with every machine full the beat opens nothing
and the head names both machines' numbers, as before (item 1).

What opened the card: from 16:06Z on 2026-09-14 every beat picked Omarchy
#3, the oldest unread title, asked the full laptop for a reading, was
refused, wrote the refusal on the card and read nothing else — twenty-four
beats in a row, while 127 defects on the rented machine's projects waited.
"""

import shutil
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from board.dial import LEFT_OUT, REFUSED
from domain.card import CardOrigin
from domain.machine import Machine
from domain.project import Project
from domain.signal import SessionWork
from infrastructure.live import sweep
from infrastructure.store import Store
from runtime import launch
from tests.api import test_doors as doors
from tests.api.test_dial import board, land_on_the_way, reading_for, tick, turn
from tests.api.test_doors import git, reconcile
from tests.conftest import NOW
from tests.floor import Floor

client = doors.client
repo = doors.repo
quick = doors.quick

GROUND = "ground"
"""The laptop's own record: a second project, a copy of the fixture whose
cards are a day older than the fixture's, so a beat that ranks by age
alone picks one of these first — and is refused, since the laptop is
full and its own cards run nowhere else."""


def two_machines(
    client: TestClient,
    machine_floor: Floor,
    store: Store,
    repo: Path,
    tmp_path: Path,
    *,
    ground_on: str,
) -> Floor:
    """Two machines and two projects: this floor as the laptop, a second
    floor as the rented machine with 24 GB; the fixture project, read
    wherever there is room, and a second project — a copy whose cards are
    a day older — that is the record of the machine `ground_on` names,
    so its cards run there or nowhere."""
    ground = tmp_path / GROUND
    shutil.copytree(repo, ground, ignore=shutil.ignore_patterns(".git"))
    git(ground, "init", "-q", "-b", "develop")
    git(ground, "add", ".")
    git(ground, "commit", "-q", "-m", "founding")
    project = Project(slug=GROUND, name="Ground", path=str(ground), registered_at=NOW)
    store.add_project(project)
    sweep(store, project, origin=CardOrigin.FOUNDING, at=NOW - timedelta(days=1))
    other = machine_floor.lay_host("rented", available_gb=24.0)
    store.add_machine(
        Machine(
            name="laptop",
            machine_id=machine_floor.machine_id,
            host=None,
            desktop=True,
            ground=str(ground) if ground_on == "laptop" else None,
            command="needle",
            added_at=NOW,
        )
    )
    store.add_machine(
        Machine(
            name="rented",
            machine_id=other.machine_id,
            host="rented",
            desktop=False,
            ground=str(ground) if ground_on == "rented" else None,
            command="needle",
            added_at=NOW,
        )
    )
    return other


def laptop_full_rented_with_room(
    client: TestClient, machine_floor: Floor, store: Store, repo: Path, tmp_path: Path
) -> Floor:
    """The laptop full and the ground of the older project; the rented
    machine with room reads the fixture project."""
    other = two_machines(client, machine_floor, store, repo, tmp_path, ground_on="laptop")
    machine_floor.set_memory(available_gb=2.0, swap_free_gb=8.0)
    client.app.state.loops.live.load()
    reconcile(client)
    return other


def oldest_unread(store: Store, slug: str) -> int:
    """The card a beat ranking by age alone would open first on this board:
    the fixture's oldest card is the same number on both copies."""
    return min(c.number for c in store.cards(slug) if c.folded_into is None)


def open_readings(store: Store, slug: str) -> list[int]:
    return sorted(store.open_windowless_sessions(slug, SessionWork.TRIAGE))


def notes(store: Store, slug: str, number: int, prefix: str) -> list[str]:
    return [h.detail for h in store.history(slug, number) if h.detail.startswith(prefix)]


def test_a_beat_opens_the_oldest_card_a_machine_with_room_can_read_and_the_rest_wait(
    client: TestClient, machine_floor: Floor, store: Store, repo: Path, tmp_path: Path
):
    other = laptop_full_rented_with_room(client, machine_floor, store, repo, tmp_path)
    turn(client, lanes=1)
    assert board(client)["dial"]["full"] is None, (
        "the rented machine has room, so the head is not full"
    )
    before = len(machine_floor.state()["launch_log"])
    tick(client)
    assert len(machine_floor.state()["launch_log"]) == before + 1, (
        f"the beat should have opened a reading of proj #{oldest_unread(store, 'proj')} on the "
        "rented machine instead of asking the full laptop for the ground's older card"
    )
    assert open_readings(store, GROUND) == [], "the laptop is full: its own cards wait"
    assert open_readings(store, "proj") == [reading_for(machine_floor)]
    launched = machine_floor.state()["launch_log"][-1]
    assert launched["config_dir"].startswith(str(other.root)), (
        f"the reading opened under {launched['config_dir']}, not on the rented machine"
    )
    held = oldest_unread(store, GROUND)
    assert len(notes(store, GROUND, held, LEFT_OUT)) == 1
    assert (
        "laptop is the machine this project records and it is full"
        in notes(store, GROUND, held, LEFT_OUT)[0]
    )
    assert notes(store, GROUND, held, REFUSED) == [], "the launch was never asked"
    # Every machine full: the beat opens nothing and the head names both.
    other.set_memory(available_gb=1.5, swap_free_gb=8.0)
    reconcile(client)
    full = board(client)["dial"]["full"]
    assert full is not None and "rented: the machine is full: 1.5 GB available" in full, full
    land_on_the_way(client, reading_for(machine_floor))
    before = len(machine_floor.state()["launch_log"])
    tick(client)
    assert len(machine_floor.state()["launch_log"]) == before


def test_a_card_left_out_says_so_once_per_spell_and_once_more_when_its_reading_opens(
    client: TestClient, machine_floor: Floor, store: Store, repo: Path, tmp_path: Path
):
    laptop_full_rented_with_room(client, machine_floor, store, repo, tmp_path)
    turn(client, lanes=1)
    held = oldest_unread(store, GROUND)
    for _ in range(20):
        tick(client)
        on = reading_for(machine_floor)
        assert on is not None and open_readings(store, "proj") == [on]
        land_on_the_way(client, on)  # the seat reads the rest, one card a beat
    assert len(notes(store, GROUND, held, LEFT_OUT)) == 1, notes(store, GROUND, held, LEFT_OUT)
    assert notes(store, GROUND, held, REFUSED) == []
    # The laptop has room again: the ground's oldest card is the oldest
    # unread on the board, and its reading opens on the next beat.
    machine_floor.set_memory(available_gb=9.0, swap_free_gb=8.0)
    reconcile(client)
    tick(client)
    assert open_readings(store, GROUND) == [held]
    history = [h.detail for h in store.history(GROUND, held)]
    assert [line for line in history if line.startswith(LEFT_OUT)] == [history[1]]
    assert history[0].startswith("A reading of the ") and "started" in history[0]


def test_a_launch_refused_for_another_cause_holds_the_beat_no_more_than_room_does(
    client: TestClient,
    machine_floor: Floor,
    store: Store,
    repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """The rooms say the older project's machine can open its reading — the
    laptop has room — and the launch itself refuses for a cause the rooms
    do not carry (here: no subscription with allowance, played by refusing
    every start in that project's checkout). The card says so once, its
    project is passed over for the beat, and the fixture project's oldest
    card opens on the rented machine instead."""
    other = two_machines(client, machine_floor, store, repo, tmp_path, ground_on="laptop")
    machine_floor.set_memory(available_gb=9.0, swap_free_gb=8.0)
    client.app.state.loops.live.load()
    reconcile(client)
    runtime = client.app.state.dial.runtime
    ground = str(tmp_path / GROUND)
    real = runtime.start_windowless

    def refusing(request):
        if request.repo == ground:
            return launch.dead(request.card, [], "no subscription has allowance on laptop", None)
        return real(request)

    monkeypatch.setattr(runtime, "start_windowless", refusing)
    turn(client, lanes=1)
    held = oldest_unread(store, GROUND)
    for _ in range(5):
        before = len(machine_floor.state()["launch_log"])
        tick(client)
        assert len(machine_floor.state()["launch_log"]) == before + 1, (
            f"the beat should have read on past the ground's #{held}, whose launch was refused"
        )
        on = reading_for(machine_floor)
        assert on is not None and open_readings(store, "proj") == [on]
        assert open_readings(store, GROUND) == []
        assert machine_floor.state()["launch_log"][-1]["config_dir"].startswith(str(other.root))
        land_on_the_way(client, on)
    refusals = notes(store, GROUND, held, REFUSED)
    assert len(refusals) == 1 and "no subscription has allowance" in refusals[0], refusals
    assert notes(store, GROUND, held, LEFT_OUT) == []
