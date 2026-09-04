import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.app import board_events, create_app
from board.import_01 import read_01
from domain.card import CardOrigin, Place
from domain.column import Column
from infrastructure.corpus import scan
from infrastructure.live import Live, sweep
from infrastructure.store import Store
from tests.api.attention import claim_count
from tests.conftest import NOW


@pytest.fixture
def client(store: Store, project, card_file_01: dict[str, object]):
    store.add_project(project)
    store.import_01(project.slug, read_01(card_file_01, scan(Path(project.path), NOW)), NOW)
    sweep(store, project, origin=CardOrigin.FOUNDING, at=NOW)
    with TestClient(create_app(store, dist=None)) as client:
        yield client


def numbers(board: dict, column: str) -> list[int]:
    col = next(c for c in board["columns"] if c["definition"]["column"] == column)
    return [card["number"] for g in col["groups"] for card in g["cards"]]


def test_the_board_is_served_with_its_eight_columns(client: TestClient):
    assert [p["slug"] for p in client.get("/api/projects").json()] == ["proj"]
    board = client.get("/api/projects/proj/board").json()
    assert [c["definition"]["column"] for c in board["columns"]] == [
        "Backlog",
        "Planned",
        "Up next",
        "Executing",
        "Decision moment",
        "Executed",
        "Done",
        "Not now",
    ]
    assert board["corpus"]["live_plans"] == 11 and board["corpus"]["watching"] is True
    assert numbers(board, "Up next") == [253, 241, 228, 237, 174]
    # #120's malformed citation and #201's archived plan the corpus lacks
    assert claim_count(board, "document gone") == 2


def test_a_move_is_stored_and_the_new_truth_comes_back(client: TestClient):
    response = client.post(
        "/api/projects/proj/cards/228/move",
        json={"to": {"column": "Up next", "group": None, "position": 0}},
    )
    assert response.status_code == 200
    assert numbers(response.json(), "Up next") == [228, 253, 241, 237, 174]
    assert numbers(client.get("/api/projects/proj/board").json(), "Up next") == [
        228,
        253,
        241,
        237,
        174,
    ]
    detail = client.get("/api/projects/proj/cards/228").json()
    assert detail["history"][0]["kind"] == "moved" and detail["history"][0]["actor"] == "owner"
    assert detail["summary"]["place"]["position"] == 0


def test_a_refused_move_says_why_and_moves_nothing(client: TestClient):
    before = numbers(client.get("/api/projects/proj/board").json(), "Up next")
    response = client.post(
        "/api/projects/proj/cards/253/move",
        json={"to": {"column": "Backlog", "group": "Phantom", "position": 0}},
    )
    assert response.status_code == 409
    assert response.json()["detail"] == 'Backlog has no group "Phantom".'
    assert numbers(client.get("/api/projects/proj/board").json(), "Up next") == before


def test_a_store_failure_reaches_the_page_in_the_stores_own_words(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    def broken(*args: object, **kwargs: object) -> None:
        raise RuntimeError("database is locked")

    monkeypatch.setattr(Store, "move", broken)
    response = client.post(
        "/api/projects/proj/cards/253/move",
        json={"to": {"column": "Backlog", "group": None, "position": 0}},
    )
    assert response.status_code == 500
    assert response.json()["detail"] == "The store refused: RuntimeError: database is locked"
    assert numbers(client.get("/api/projects/proj/board").json(), "Up next") == [
        253,
        241,
        228,
        237,
        174,
    ]


def test_a_malformed_move_is_refused_by_the_types(client: TestClient):
    response = client.post(
        "/api/projects/proj/cards/253/move",
        json={"to": {"column": "Someday", "group": None, "position": 0}},
    )
    assert response.status_code == 422


def test_the_card_detail_carries_the_document_and_the_split_rows(client: TestClient):
    detail = client.get("/api/projects/proj/cards/253").json()
    assert detail["document"]["title"] == "Every metered kilowatt is billed"
    assert detail["document"]["gate"] == "medium"
    assert [r["kind"] for r in detail["brief"]] == ["TODAY", "COST", "PLAN"]
    assert detail["record"] == []
    assert detail["summary"]["essence_source"] == "card"
    assert client.get("/api/projects/proj/cards/999").status_code == 409


def test_a_project_file_is_read_only_from_docs(client: TestClient):
    ok = client.get(
        "/api/projects/proj/files",
        params={"path": "docs/plans/2026-09-03-every-metered-kilowatt-is-billed.md"},
    )
    assert ok.status_code == 200 and ok.json()["text"].startswith("# Every metered")
    assert (
        client.get(
            "/api/projects/proj/files", params={"path": "docs/plans/../../etc/passwd.md"}
        ).status_code
        == 400
    )
    assert (
        client.get("/api/projects/proj/files", params={"path": "pyproject.toml"}).status_code == 400
    )
    assert (
        client.get("/api/projects/proj/files", params={"path": "docs/plans/nope.md"}).status_code
        == 404
    )


def test_the_stream_says_the_version_and_a_move_bumps_it(
    store: Store, project, card_file_01: dict[str, object]
):
    store.add_project(project)
    store.import_01(project.slug, read_01(card_file_01, scan(Path(project.path), NOW)), NOW)

    async def run() -> list[str]:
        live = Live(store)
        live.load()
        loaded = live.version
        seen: list[str] = []
        calls = 0

        async def disconnected() -> bool:
            nonlocal calls
            calls += 1
            return calls > 2

        async def mover() -> None:
            await asyncio.sleep(0.05)
            live.move("proj", 228, Place(column=Column.UP_NEXT, group=None, position=0))

        task = asyncio.create_task(mover())
        async for event in board_events(live, disconnected, keepalive=2.0):
            seen.append(event)
        await task
        return [e.replace(str(loaded), "V").replace(str(loaded + 1), "V+1") for e in seen]

    events = asyncio.run(run())
    assert events[0] == 'event: board\ndata: {"version": V}\n\n'
    assert events[1] == 'event: board\ndata: {"version": V+1}\n\n'


def test_without_a_built_page_the_root_says_how_to_build_it(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200 and "npm run build" in response.text


def test_a_project_deep_link_is_served_the_page(
    store: Store, project, card_file_01: dict[str, object], tmp_path
):
    """`/p/<slug>` is how the page names a second project; a reload or a link
    to it must get the same page as `/`, not a 404 from the static mount."""
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><title>Needle</title>", encoding="utf-8")
    with TestClient(create_app(store, dist=dist)) as client:
        assert client.get("/").status_code == 200
        deep = client.get("/p/needle")
        assert deep.status_code == 200
        assert "Needle" in deep.text
        assert client.get("/api/projects/nothing/board").status_code != 200
