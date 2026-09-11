"""A click on a card of the board's own machine is answered while another
machine is stalled (card #123, item 3): the pass asks every machine outside
the lock, so a door waits on no wire."""

import time
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from domain.machine import Machine
from infrastructure.store import Store
from tests.api import test_doors as doors
from tests.api.test_doors import CARD, start
from tests.floor import Floor

client = doors.client
repo = doors.repo
quick = doors.quick

AT = datetime(2026, 9, 11, 9, 0, tzinfo=UTC)


def test_a_watch_here_is_answered_while_the_other_machine_is_stalled(
    client: TestClient, machine_floor: Floor, repo: Path, store: Store
):
    other = machine_floor.lay_host("rented")
    # The project is the laptop's own record, so its card runs here.
    store.add_machine(
        Machine(
            name="laptop",
            machine_id=machine_floor.machine_id,
            host=None,
            desktop=True,
            ground=str(repo),
            command="needle",
            added_at=AT,
        )
    )
    store.add_machine(
        Machine(
            name="rented",
            machine_id=other.machine_id,
            host="rented",
            desktop=False,
            ground=None,
            command="needle",
            added_at=AT,
        )
    )
    start(client)
    hosts = machine_floor.state()["hosts"]
    hosts["rented"]["env"]["NEEDLE_FAKE_SLOW"] = "8"
    machine_floor.update(hosts=hosts)
    loops = client.app.state.loops
    stalled = client.portal.start_task_soon(loops.reconcile)
    time.sleep(1.0)  # the question is out to the rented machine
    began = time.monotonic()
    watched = client.post(f"/api/projects/proj/cards/{CARD}/watch")
    took = time.monotonic() - began
    assert watched.status_code == 200, watched.text
    assert not stalled.done(), "the rented machine is still being asked"
    assert took < 6.0, f"the Watch took {took:.1f} s behind a stalled machine"
    stalled.result(timeout=60)
    clicked = store.last_clicked_beat()
    assert clicked is not None and clicked.door == "watch"
    assert clicked.door_wait is not None and clicked.door_wait < 1.0, clicked
