"""The triage doors through the API (plan 05, item 2): every card carrying a
verdict is one line on the board, counted on the attention line; accepting
moves the card by the machine with the verdict's reason and the owner's
name; overturning keeps it and records his word; a class is accepted in one
act, and a refusal stays with the card."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from board.import_01 import read_01
from domain.card import Actor, CardOrigin
from domain.row import Row, RowKind
from infrastructure.corpus import scan
from infrastructure.live import sweep
from infrastructure.store import Store
from tests.api.attention import claim_count
from tests.conftest import NOW

SUPERSEDED = "superseded — card #263 carries the same intent as a plan → Not now"
BUILT = (
    "built under another name — docs/plans/done/2026-09-03-the-fuel-pontoon.md delivered it → Done"
)
OPEN = "live and open — waits on the four Search rulings (#144) → stays"


@pytest.fixture
def client(store: Store, project, card_file_01: dict[str, object]):
    store.add_project(project)
    store.import_01(project.slug, read_01(card_file_01, scan(Path(project.path), NOW)), NOW)
    sweep(store, project, origin=CardOrigin.FOUNDING, at=NOW)
    for number, text in ((228, SUPERSEDED), (237, BUILT), (241, OPEN)):
        store.add_row("proj", number, Row(kind=RowKind.VERDICT, text=text), Actor.SESSION, NOW)
    store.add_row(
        "proj", 174, Row(kind=RowKind.VERDICT, text="nothing the board knows"), Actor.SESSION, NOW
    )
    with TestClient(create_app(store, dist=None)) as client:
        yield client


def column_of(client: TestClient, number: int) -> str:
    board = client.get("/api/projects/proj/board").json()
    for column in board["columns"]:
        for group in column["groups"]:
            for card in group["cards"]:
                if card["number"] == number:
                    return column["definition"]["column"]
    raise AssertionError(f"#{number} is not on the board")


def test_every_readable_verdict_is_a_line_and_the_attention_line_counts_them(client: TestClient):
    board = client.get("/api/projects/proj/board").json()
    lines = {v["number"]: v for v in board["verdicts"]}
    assert set(lines) == {228, 237, 241}
    assert claim_count(board, "verdict") == 3
    assert lines[228]["verdict"] == {
        "evidence_class": "superseded",
        "evidence": "card #263 carries the same intent as a plan",
        "to": "Not now",
    }
    assert lines[241]["verdict"]["to"] is None and lines[241]["place"]["column"] == "Up next"
    detail = client.get("/api/projects/proj/cards/174").json()
    assert detail["verdict"] is None
    assert "names no class the board knows" in detail["verdict_note"]
    assert [r["kind"] for r in detail["record"]] == ["VERDICT"]


def test_accepting_moves_the_card_with_the_reason_and_the_owner_named(client: TestClient):
    response = client.post("/api/projects/proj/cards/228/accept")
    assert response.status_code == 200, response.text
    assert response.json()["said"] == (
        "#228 moved to Not now: superseded — card #263 carries the same intent as a plan"
    )
    assert column_of(client, 228) == "Not now"
    detail = client.get("/api/projects/proj/cards/228").json()
    moved = next(h for h in detail["history"] if h["kind"] == "moved")
    assert moved["actor"] == "owner"
    assert moved["detail"].endswith(
        "accepted the verdict: superseded — card #263 carries the same intent as a plan"
    )
    assert [r["kind"] for r in detail["record"]] == ["RULED"]
    assert detail["record"][0]["text"] == f"accepted: {SUPERSEDED}"
    board = client.get("/api/projects/proj/board").json()
    assert claim_count(board, "verdict") == 2
    # A second accept has nothing to act on.
    again = client.post("/api/projects/proj/cards/228/accept")
    assert again.status_code == 409 and "carries no verdict" in again.json()["detail"]


def test_a_verdict_that_stays_is_accepted_without_a_move_and_overturned_with_a_word(
    client: TestClient,
):
    accepted = client.post("/api/projects/proj/cards/241/accept")
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["said"].startswith("#241 stays in Up next: live and open")
    assert column_of(client, 241) == "Up next"
    detail = client.get("/api/projects/proj/cards/241").json()
    assert not any(h["kind"] == "moved" for h in detail["history"])

    empty = client.post("/api/projects/proj/cards/237/overturn", json={"text": "  "})
    assert empty.status_code == 409 and "say why" in empty.json()["detail"]
    overturned = client.post(
        "/api/projects/proj/cards/237/overturn",
        json={"text": "that plan built the pump, not the pontoon"},
    )
    assert overturned.status_code == 200, overturned.text
    assert overturned.json()["said"] == (
        "#237 stays in Up next; your word: that plan built the pump, not the pontoon"
    )
    assert column_of(client, 237) == "Up next"
    detail = client.get("/api/projects/proj/cards/237").json()
    assert detail["record"][-1]["text"] == (
        f"overturned: that plan built the pump, not the pontoon — the verdict read: {BUILT}"
    )
    row = next(h for h in detail["history"] if h["kind"] == "row" and h["actor"] == "owner")
    assert row["detail"].startswith("VERDICT overturned:") and row["detail"].endswith(
        "— his word: that plan built the pump, not the pontoon"
    )


def test_a_class_is_accepted_in_one_act_and_a_refusal_stays_with_the_card(
    client: TestClient, store: Store
):
    # #253's verdict sends it to Executed, which needs a signal it does not name.
    store.add_row(
        "proj",
        253,
        Row(kind=RowKind.VERDICT, text="superseded — folded into #241's plan → Executed"),
        Actor.SESSION,
        NOW,
    )
    response = client.post(
        "/api/projects/proj/triage/accept", json={"evidence_class": "superseded"}
    )
    assert response.status_code == 200, response.text
    ruled = response.json()
    assert ruled["evidence_class"] == "superseded" and ruled["accepted"] == 1
    assert len(ruled["refused"]) == 1 and ruled["refused"][0].startswith(
        "#253: #253 cannot enter Executed"
    )
    assert column_of(client, 228) == "Not now" and column_of(client, 253) == "Up next"
    board = client.get("/api/projects/proj/board").json()
    assert {v["number"] for v in board["verdicts"]} == {253, 237, 241}
    unknown = client.post("/api/projects/proj/triage/accept", json={"evidence_class": "hunch"})
    assert unknown.status_code == 422
