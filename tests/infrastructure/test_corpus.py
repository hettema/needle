import asyncio
from pathlib import Path

import pytest

from domain.card import CardOrigin
from domain.column import Column
from domain.document import DocumentKind
from infrastructure.corpus import NotACorpus, check_corpus, scan
from infrastructure.live import Live, sweep
from infrastructure.store import Store
from tests.conftest import NOW, write_plan, write_suggestion


def test_the_scan_reads_the_four_folders_and_skips_readmes(corpus: Path):
    index = scan(corpus, NOW)
    kinds = sorted((d.kind, d.archived, d.stem) for d in index.documents)
    assert (
        DocumentKind.PLAN,
        False,
        "2026-09-01-the-waiting-list-offers-every-berth-that-fits",
    ) in kinds
    assert (DocumentKind.PLAN, True, "2026-08-30-the-office-runs-its-own-checks") in kinds
    assert (DocumentKind.SUGGESTION, True, "2026-04-02-shared-mooring-lines") in kinds
    assert not any(d.stem == "README" for d in index.documents)
    assert len(index.live()) == 19 and len(index.archived()) == 8


def test_a_folder_without_plans_is_not_a_corpus(tmp_path: Path):
    with pytest.raises(NotACorpus):
        check_corpus(tmp_path)
    check_corpus(tmp_path) if (tmp_path / "docs" / "plans").mkdir(parents=True) else None


def test_the_registration_sweep_cards_every_live_document(store: Store, project, corpus: Path):
    store.add_project(project)
    index, effects = sweep(store, project, origin=CardOrigin.FOUNDING, at=NOW)
    assert len(effects.born) == 19
    cards = store.cards("proj")
    assert {c.place.column for c in cards} == {Column.PLANNED, Column.BACKLOG}
    assert all(c.origin == CardOrigin.FOUNDING for c in cards)
    again = sweep(store, project, origin=CardOrigin.FOUNDING, at=NOW)[1]
    assert again.empty()


def test_a_file_that_lands_while_the_board_watches_is_a_card_within_seconds(
    store: Store, project, corpus: Path
):
    store.add_project(project)
    sweep(store, project, origin=CardOrigin.FOUNDING, at=NOW)

    async def run() -> tuple[int, int, list[str]]:
        live = Live(store)
        live.load()
        await live.start_watching()
        for _ in range(50):
            await asyncio.sleep(0.1)
            if live.projects["proj"].watching:
                break
        assert live.projects["proj"].watching, live.projects["proj"].watch_note
        version = live.version
        write_plan(corpus, "2026-09-04-a-new-plan", title="A new plan arrives")
        write_suggestion(corpus, "2026-09-04-an-idea", title="An idea arrives")
        titles: list[str] = []
        for _ in range(100):
            await asyncio.sleep(0.1)
            board = live.board("proj")
            titles = [
                c.title for col in board.columns for g in col.groups for c in g.cards if c.is_new
            ]
            if len(titles) == 2:
                break
        board = live.board("proj")
        await live.stop()
        return version, board.version, titles

    version_before, version_after, titles = asyncio.run(run())
    assert sorted(titles) == ["A new plan arrives", "An idea arrives"]
    assert version_after > version_before
    board_cards = {c.title: c for c in store.cards("proj")}
    assert board_cards["A new plan arrives"].origin == CardOrigin.ARRIVED


def test_an_archive_and_a_rename_keep_the_number(store: Store, project, corpus: Path):
    store.add_project(project)
    sweep(store, project, origin=CardOrigin.FOUNDING, at=NOW)
    plan = next(
        c for c in store.cards("proj") if c.title == "The waiting list offers every berth that fits"
    )
    old = corpus / "docs" / "plans" / "2026-09-01-the-waiting-list-offers-every-berth-that-fits.md"
    old.rename(corpus / "docs" / "plans" / "2026-09-01-the-waiting-list.md")
    effects = sweep(store, project, origin=CardOrigin.ARRIVED, at=NOW)[1]
    assert [r.card_number for r in effects.renamed] == [plan.number] and effects.born == []
    (corpus / "docs" / "plans" / "2026-09-01-the-waiting-list.md").rename(
        corpus / "docs" / "plans" / "done" / "2026-09-01-the-waiting-list.md"
    )
    effects = sweep(store, project, origin=CardOrigin.ARRIVED, at=NOW)[1]
    assert [a.card_number for a in effects.archived] == [plan.number]
    after = store.card("proj", plan.number)
    assert (
        after is not None
        and after.link is not None
        and after.link.archived
        and after.link.stem == "2026-09-01-the-waiting-list"
    )
