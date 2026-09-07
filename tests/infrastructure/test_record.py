"""The record is readable by the projects it serves (plan 08, item 3): every
row carries when it was written and by whom, the reader gives them back
oldest first, and the migration's backfill dates the rows that were there
before it from the audit."""

from datetime import timedelta
from pathlib import Path

from alembic import command
from alembic.config import Config

from domain.card import Actor, Place
from domain.column import Column
from domain.project import Project
from domain.row import Row, RowKind
from infrastructure import store as store_mod
from infrastructure.store import Store
from tests.infrastructure.test_store import NOW, registered

LATER = NOW + timedelta(hours=1)
LATEST = NOW + timedelta(hours=2)


def _write_some(store: Store) -> None:
    store.add_row("proj", 253, Row(kind=RowKind.RULING, text="first ruling"), Actor.OWNER, NOW)
    store.add_row("proj", 253, Row(kind=RowKind.DELIVERED, text="delivered v1"), Actor.SESSION, NOW)
    store.add_row(
        "proj", 253, Row(kind=RowKind.DELIVERED, text="delivered v2"), Actor.SESSION, LATER
    )
    store.add_row("proj", 253, Row(kind=RowKind.RULING, text="second ruling"), Actor.OWNER, LATER)
    store.add_row("proj", 253, Row(kind=RowKind.VERDICT, text="a verdict"), Actor.MACHINE, LATER)
    store.rule_on_verdict(
        "proj",
        253,
        LATEST,
        accepted=True,
        word=None,
        to=Place(column=Column.NOT_NOW, group=None, position=0),
        replace=False,
        said="accepted",
    )


def test_every_row_says_when_and_by_whom_and_the_reader_gives_them_back_oldest_first(
    store: Store, project: Project, card_file_01: dict[str, object]
):
    registered(store, project, card_file_01)
    imported = store.rows_written("proj")
    assert imported and all(r.by == Actor.IMPORT and r.at == NOW for r in imported), (
        "0.1's rows are dated at the import and signed by it"
    )
    _write_some(store)
    mine = [r for r in store.rows_written("proj") if r.card == 253 and r.by != Actor.IMPORT]
    assert [(r.kind, r.text, r.at, r.by) for r in mine] == [
        (RowKind.RULING, "first ruling", NOW, Actor.OWNER),
        (RowKind.DELIVERED, "delivered v2", LATER, Actor.SESSION),
        (RowKind.RULING, "second ruling", LATER, Actor.OWNER),
        (RowKind.RULED, "accepted: a verdict", LATEST, Actor.OWNER),
    ], "a rewritten row carries the time of its standing text; the earlier text is history"
    assert mine[0].title and mine[0].column == Column.NOT_NOW
    since = store.rows_written("proj", since=LATER)
    assert {r.text for r in since} == {"delivered v2", "second ruling", "accepted: a verdict"}
    assert store.rows_written("proj", since=LATEST + timedelta(seconds=1)) == []


def test_the_backfill_dates_rows_older_than_the_record_from_the_audit(
    store: Store, project: Project, card_file_01: dict[str, object], tmp_path: Path
):
    """Down to 0012 (the columns go), back up to head (they return, filled
    from the audit's row lines): the record reads the same as before."""
    registered(store, project, card_file_01)
    _write_some(store)
    before = store.rows_written("proj")
    config = Config()
    config.set_main_option("script_location", str(store_mod._MIGRATIONS))
    with store.engine.begin() as connection:
        config.attributes["connection"] = connection
        command.downgrade(config, "0012")
    with store.engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
    after = store.rows_written("proj")
    assert [(r.card, r.kind, r.text, r.at, r.by) for r in after] == [
        (r.card, r.kind, r.text, r.at, r.by) for r in before
    ]
