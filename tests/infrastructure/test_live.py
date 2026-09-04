"""The running board hears the corpus from its first file and the store from
its next write (plan 01b, item 3)."""

import asyncio
import shutil
from collections.abc import Awaitable, Callable
from pathlib import Path

from domain.card import CardOrigin
from domain.project import Project
from infrastructure.live import Live, sweep
from infrastructure.store import Store
from tests.conftest import NOW, copy_harbourmaster, write_suggestion


async def until(condition: Callable[[], bool], seconds: float = 10.0) -> bool:
    for _ in range(int(seconds / 0.1)):
        if condition():
            return True
        await asyncio.sleep(0.1)
    return condition()


async def watching(live: Live, slug: str) -> None:
    assert await until(lambda: live.projects[slug].watching), live.projects[slug].watch_note


def run(body: Callable[[], Awaitable[None]]) -> None:
    asyncio.run(body())


def test_a_corpus_folder_created_after_start_is_watched_from_its_first_file(
    store: Store, project: Project, corpus: Path
):
    shutil.rmtree(corpus / "docs" / "slice-suggestions")
    store.add_project(project)
    sweep(store, project, origin=CardOrigin.FOUNDING, at=NOW)

    async def body() -> None:
        live = Live(store)
        live.load()
        await live.start_watching()
        await watching(live, "proj")
        write_suggestion(
            corpus, "2026-09-04-the-first-idea", title="The first idea in a new folder"
        )

        def carded() -> bool:
            return any(c.title == "The first idea in a new folder" for c in store.cards("proj"))

        assert await until(carded), "a file in a folder created after start was never carded"
        await live.stop()

    run(body)


def test_a_project_added_while_serving_is_on_the_board_without_a_restart(
    store: Store, project: Project, tmp_path: Path
):
    store.add_project(project)
    sweep(store, project, origin=CardOrigin.FOUNDING, at=NOW)
    second_root = copy_harbourmaster(tmp_path / "second")

    async def body() -> None:
        live = Live(store)
        live.load()
        await live.start_watching()
        await watching(live, "proj")
        before = live.version
        # What `needle add` does, from another process: a write to the store's file.
        other = Store(store.path)
        other.add_project(
            Project(slug="second", name="Second", path=str(second_root), registered_at=NOW)
        )
        other.close()
        assert await until(lambda: "second" in live.projects), "the new project was never seen"
        await watching(live, "second")
        assert live.version > before
        assert live.board("second").project.slug == "second"
        await live.stop()

    run(body)


def test_closing_ends_a_wait_at_once(store: Store, project: Project):
    store.add_project(project)

    async def body() -> None:
        live = Live(store)
        live.load()
        waiter = asyncio.create_task(live.wait_for_change(live.version, timeout=30))
        await asyncio.sleep(0.05)
        live.close()
        assert await asyncio.wait_for(waiter, 1) == live.version
        assert await live.wait_for_change(live.version, timeout=30) == live.version

    run(body)


def test_a_write_from_another_process_is_heard_within_the_poll_and_the_servers_own_never_is(
    store: Store, project: Project
):
    """Plan 06, item 6: a `needle row` from a lane's process is on the page
    within a second and the loops act on it; the server's own writes — the
    lane loop's records, a move — never make it re-read itself."""
    from domain.card import Actor
    from domain.row import Row, RowKind

    store.add_project(project)
    sweep(store, project, origin=CardOrigin.FOUNDING, at=NOW)
    number = store.cards("proj")[0].number

    async def body() -> None:
        live = Live(store)
        live.load()
        heard: list[int] = []

        async def on_change() -> None:
            heard.append(live.version)

        live.on_change = on_change
        await live.start_watching()
        await watching(live, "proj")
        await asyncio.sleep(1.5)
        before = live.version
        heard.clear()
        live.add_row("proj", number, Row(kind=RowKind.REVIEW, text="own"), Actor.SESSION)
        await asyncio.sleep(2.5)
        assert live.version == before + 1, "an own write bumps once, at the write"
        assert heard == [], "the server never re-reads its own write"
        other = Store(store.path)
        other.add_row("proj", number, Row(kind=RowKind.REVIEW, text="theirs"), Actor.SESSION, NOW)
        other.close()
        assert await until(lambda: len(heard) >= 1, 3.0), "the other process's write was not heard"
        assert live.version > before + 1
        assert any(r.text == "theirs" for r in live.card("proj", number).rows)
        await live.stop()

    run(body)


def test_a_hand_move_against_the_documents_kind_is_refused_with_the_line_to_edit(
    store: Store, project: Project, corpus: Path
):
    """Plan 06, item 2: the rail is a lens on the `Kind:` line, kept by the
    corpus on every read; a drag that disagrees with the line is refused now
    rather than undone later."""
    import pytest

    from domain.card import Place
    from domain.column import DEFECTS_RAIL, Column
    from infrastructure.store import StoreRefusal

    # The conftest suggestion is filed by a review, so it reads as a defect.
    write_suggestion(corpus, "2026-09-04-a-found-defect", title="The berth count is off by one")
    store.add_project(project)
    sweep(store, project, origin=CardOrigin.FOUNDING, at=NOW)
    live = Live(store)
    live.load()
    defect = next(c for c in store.cards("proj") if c.title == "The berth count is off by one")
    assert defect.place.group == DEFECTS_RAIL
    with pytest.raises(StoreRefusal, match="Kind: defect") as refused:
        live.move("proj", defect.number, Place(column=Column.BACKLOG, group=None, position=0))
    assert "docs/slice-suggestions/2026-09-04-a-found-defect.md" in str(refused.value)
    idea = next(
        c
        for c in store.cards("proj")
        if c.link is not None
        and c.link.kind.value == "suggestion"
        and c.place.column == Column.BACKLOG
        and c.place.group != DEFECTS_RAIL
    )
    with pytest.raises(StoreRefusal, match="Kind: idea"):
        live.move("proj", idea.number, Place(column=Column.BACKLOG, group=DEFECTS_RAIL, position=0))
    # Out of Backlog is the owner's move as ever, and back into Backlog lands below the rail.
    live.move("proj", defect.number, Place(column=Column.UP_NEXT, group=None, position=0))
    live.move("proj", defect.number, Place(column=Column.BACKLOG, group=DEFECTS_RAIL, position=0))
    assert store.card("proj", defect.number).place.group == DEFECTS_RAIL  # type: ignore[union-attr]
