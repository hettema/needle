import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from board.import_01 import read_01
from board.reconcile import Archived, Born, Effects, Relinked, Renamed
from domain.audit import AuditKind
from domain.card import Actor, CardOrigin, Place
from domain.column import Column
from domain.document import DocumentKind, DocumentRef
from domain.project import Project
from domain.row import RowKind
from infrastructure.corpus import scan
from infrastructure.schema import UtcDateTime
from infrastructure.store import Store, StoreRefusal
from tests.conftest import CARD_FILE_01, NOW


def registered(store: Store, project: Project, card_file_01: dict[str, object]) -> Store:
    store.add_project(project)
    store.import_01(project.slug, read_01(card_file_01, scan(Path(project.path), NOW)), NOW)
    return store


def test_a_project_is_registered_once_by_slug_and_by_path(store: Store, project: Project):
    store.add_project(project)
    with pytest.raises(StoreRefusal, match="already on the board"):
        store.add_project(project)
    with pytest.raises(StoreRefusal, match="already on the board as proj"):
        store.add_project(Project(slug="other", name="O", path=project.path, registered_at=NOW))
    assert [p.slug for p in store.projects()] == ["proj"]
    with pytest.raises(StoreRefusal, match='No project "nope"'):
        store.project("nope")


def test_the_import_round_trips_and_runs_once(
    store: Store, project: Project, card_file_01: dict[str, object]
):
    registered(store, project, card_file_01)
    cards = {c.number: c for c in store.cards("proj")}
    assert len(cards) == 21
    assert cards[252].place == Place(column=Column.BACKLOG, group="Next to plan", position=0)
    assert [r.kind for r in cards[252].rows] == [RowKind.SERVES, RowKind.TODAY, RowKind.COST]
    assert cards[147].tags == ["Action", "Ruling"]
    assert cards[134].link is not None and cards[134].link.archived
    assert cards[134].origin == CardOrigin.IMPORTED and cards[134].born_at == NOW
    assert [g.name for g in store.layout("proj") if g.column == Column.BACKLOG] == [
        "Next to plan",
        "Season opening",
        "Skipper-facing quality",
    ]
    assert store.has_import("proj")
    with pytest.raises(StoreRefusal, match="runs once"):
        store.import_01("proj", read_01(card_file_01, scan(Path(project.path), NOW)), NOW)
    kinds = [(h.kind, h.actor) for h in store.history("proj", 252)]
    assert kinds == [(AuditKind.LINKED, Actor.IMPORT), (AuditKind.BORN, Actor.IMPORT)]
    assert [h.detail for h in store.history("proj", 123)] == [
        "Retired in Needle 0.1: parked into #167"
    ]


def test_a_move_is_persisted_before_it_is_reported_and_survives_a_reopen(
    tmp_path: Path, project: Project, card_file_01: dict[str, object]
):
    path = tmp_path / "needle.db"
    store = registered(Store(path), project, card_file_01)
    moved = store.move(
        "proj", 252, Place(column=Column.UP_NEXT, group=None, position=1), Actor.OWNER, NOW
    )
    assert moved.place == Place(column=Column.UP_NEXT, group=None, position=1)
    store.close()
    reopened = Store(path)
    layout = {(g.column, g.name): g.numbers for g in reopened.layout("proj")}
    assert layout[(Column.UP_NEXT, None)] == [253, 252, 241, 228, 237, 174]
    assert layout[(Column.BACKLOG, "Next to plan")] == [242, 232, 120]
    history = reopened.history("proj", 252)
    assert history[0].kind == AuditKind.MOVED and history[0].actor == Actor.OWNER
    assert history[0].from_place == Place(column=Column.BACKLOG, group="Next to plan", position=0)
    assert history[0].to_place == Place(column=Column.UP_NEXT, group=None, position=1)
    assert history[0].detail == "Moved Backlog · Next to plan → Up next"
    reopened.close()


def test_a_rank_change_reads_as_a_rank_change(
    store: Store, project: Project, card_file_01: dict[str, object]
):
    registered(store, project, card_file_01)
    store.move("proj", 228, Place(column=Column.UP_NEXT, group=None, position=0), Actor.OWNER, NOW)
    assert store.history("proj", 228)[0].detail == "Ranked 1 in Up next — was 3"


def test_a_move_that_changes_nothing_writes_nothing(
    store: Store, project: Project, card_file_01: dict[str, object]
):
    registered(store, project, card_file_01)
    before = len(store.history("proj", 253))
    store.move("proj", 253, Place(column=Column.UP_NEXT, group=None, position=0), Actor.OWNER, NOW)
    assert len(store.history("proj", 253)) == before


def test_a_refused_move_changes_nothing(
    store: Store, project: Project, card_file_01: dict[str, object]
):
    registered(store, project, card_file_01)
    before = store.layout("proj")
    with pytest.raises(StoreRefusal, match='Backlog has no group "Phantom"'):
        store.move(
            "proj", 253, Place(column=Column.BACKLOG, group="Phantom", position=0), Actor.OWNER, NOW
        )
    with pytest.raises(StoreRefusal, match="no card #999"):
        store.move(
            "proj", 999, Place(column=Column.UP_NEXT, group=None, position=0), Actor.OWNER, NOW
        )
    assert store.layout("proj") == before


def test_moving_to_a_column_without_an_unnamed_group_makes_one_at_its_end(
    store: Store, project: Project, card_file_01: dict[str, object]
):
    registered(store, project, card_file_01)
    store.move("proj", 253, Place(column=Column.PLANNED, group=None, position=0), Actor.OWNER, NOW)
    planned = [(g.name, g.numbers) for g in store.layout("proj") if g.column == Column.PLANNED]
    assert planned == [
        ("Season opening", [196]),
        ("Skipper-facing quality", [109]),
        ("Trust — from the winter review", [172]),
        (None, [253]),
    ]


def test_births_land_last_in_the_unnamed_group_and_number_onward(
    store: Store, project: Project, card_file_01: dict[str, object]
):
    registered(store, project, card_file_01)
    effects = Effects(
        renamed=[],
        relinked=[],
        archived=[],
        born=[
            Born(
                document=DocumentRef(
                    kind=DocumentKind.PLAN,
                    stem="new-plan",
                    path="docs/plans/new-plan.md",
                    title="New plan",
                ),
                column=Column.PLANNED,
                found_by=None,
            ),
            Born(
                document=DocumentRef(
                    kind=DocumentKind.SUGGESTION,
                    stem="idea",
                    path="docs/slice-suggestions/idea.md",
                    title="Idea",
                ),
                column=Column.BACKLOG,
                found_by=None,
            ),
        ],
    )
    assert store.apply_effects("proj", effects, origin=CardOrigin.FOUNDING, at=NOW) == [262, 263]
    born = store.card("proj", 262)
    assert born is not None
    assert born.title == "New plan" and born.origin == CardOrigin.FOUNDING
    assert born.link is not None and born.link.stem == "new-plan" and not born.link.archived
    assert born.citations == ["docs/plans/new-plan.md"]
    assert born.place == Place(column=Column.PLANNED, group=None, position=0)
    backlog = [(g.name, g.numbers) for g in store.layout("proj") if g.column == Column.BACKLOG]
    assert backlog[-1] == (None, [263])
    assert (
        store.history("proj", 262)[0].detail == "Born from docs/plans/new-plan.md, at registration."
    )
    later = store.apply_effects(
        "proj",
        Effects(
            renamed=[],
            relinked=[],
            archived=[],
            born=[
                Born(
                    document=DocumentRef(
                        kind=DocumentKind.PLAN, stem="p3", path="docs/plans/p3.md", title="P3"
                    ),
                    column=Column.PLANNED,
                    found_by=None,
                )
            ],
        ),
        origin=CardOrigin.ARRIVED,
        at=NOW + timedelta(hours=1),
    )
    assert later == [264]
    assert store.history("proj", 264)[0].detail.endswith("after registration.")


def test_renames_relinks_and_archives_move_the_link_and_leave_a_row(
    store: Store, project: Project, card_file_01: dict[str, object]
):
    registered(store, project, card_file_01)
    effects = Effects(
        renamed=[
            Renamed(
                card_number=196,
                old_stem="2026-09-01-the-waiting-list-offers-every-berth-that-fits",
                document=DocumentRef(
                    kind=DocumentKind.PLAN,
                    stem="renamed",
                    path="docs/plans/renamed.md",
                    title="The waiting list offers every berth that fits",
                ),
            )
        ],
        relinked=[
            Relinked(
                card_number=228,
                document=DocumentRef(
                    kind=DocumentKind.PLAN,
                    stem="told",
                    path="docs/plans/told.md",
                    title="The skipper is told what the office decided",
                ),
                archived=False,
            )
        ],
        archived=[
            Archived(
                card_number=253,
                document=DocumentRef(
                    kind=DocumentKind.PLAN,
                    stem="2026-09-03-every-metered-kilowatt-is-billed",
                    path="docs/plans/done/2026-09-03-every-metered-kilowatt-is-billed.md",
                    title="Every metered kilowatt is billed",
                ),
            )
        ],
        born=[],
    )
    store.apply_effects("proj", effects, origin=CardOrigin.ARRIVED, at=NOW)
    renamed = store.card("proj", 196)
    assert renamed is not None and renamed.link is not None and renamed.link.stem == "renamed"
    assert renamed.citations[-1] == "docs/plans/renamed.md"
    relinked = store.card("proj", 228)
    assert relinked is not None and relinked.link is not None and relinked.link.stem == "told"
    archived = store.card("proj", 253)
    assert archived is not None and archived.link is not None and archived.link.archived
    assert store.history("proj", 196)[0].kind == AuditKind.RENAMED
    assert store.history("proj", 228)[0].kind == AuditKind.LINKED
    assert store.history("proj", 253)[0].kind == AuditKind.ARCHIVED


def test_the_store_takes_aware_datetimes_only():
    with pytest.raises(ValueError, match="aware"):
        UtcDateTime().process_bind_param(datetime(2026, 9, 3), None)
    stored = UtcDateTime().process_bind_param(datetime(2026, 9, 3, 12, tzinfo=UTC), None)
    assert stored == "2026-09-03T12:00:00+00:00"


def test_the_card_file_fixture_is_the_shape_of_the_real_one():
    """The synthetic card file stands in for a real 0.1 file; its keys are 0.1's."""
    payload = json.loads(CARD_FILE_01.read_text(encoding="utf-8"))
    assert set(payload) == {"cols", "nextId", "lanes", "retired"}
    card = payload["cols"][0]["groups"][0]["cards"][0]
    assert set(card) == {"t", "ch", "deep", "b", "id"}
