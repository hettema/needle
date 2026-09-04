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
