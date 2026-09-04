"""The store's part of plan 06: a defect born on Backlog's rail and rehomed by
its document's word (item 2), a card folded under the card whose plan
carries it and following it from then on (item 5), and the write stamp the
server reads to tell another process's commit from its own (item 6)."""

from datetime import timedelta
from pathlib import Path

import pytest

from board.import_01 import read_01
from board.reconcile import Born, Effects, Folded, Rehomed, Relinked
from domain.audit import AuditKind
from domain.board import TrunkState
from domain.card import Actor, CardOrigin, Place
from domain.column import DEFECTS_RAIL, Column
from domain.document import DocumentKind, DocumentRef, SuggestionKind
from domain.project import Project
from infrastructure.corpus import scan
from infrastructure.store import Store, StoreRefusal
from tests.conftest import NOW


@pytest.fixture
def board(store: Store, project: Project, card_file_01: dict[str, object]) -> Store:
    store.add_project(project)
    store.import_01(project.slug, read_01(card_file_01, scan(Path(project.path), NOW)), NOW)
    return store


def effects(**parts) -> Effects:
    base: dict = dict(renamed=[], relinked=[], folded=[], rehomed=[], archived=[], born=[])
    base.update(parts)
    return Effects(**base)


def suggestion_ref(stem: str) -> DocumentRef:
    return DocumentRef(
        kind=DocumentKind.SUGGESTION, stem=stem, path=f"docs/slice-suggestions/{stem}.md", title=stem
    )


PLAN = DocumentRef(
    kind=DocumentKind.PLAN, stem="together", path="docs/plans/together.md", title="Together"
)


def test_a_defect_is_born_on_the_rail_above_every_named_group_and_an_idea_below(board: Store):
    born = board.apply_effects(
        "proj",
        effects(
            born=[
                Born(
                    document=suggestion_ref("d"),
                    column=Column.BACKLOG,
                    found_by=None,
                    kind=SuggestionKind.DEFECT,
                ),
                Born(
                    document=suggestion_ref("i"),
                    column=Column.BACKLOG,
                    found_by=None,
                    kind=SuggestionKind.IDEA,
                ),
            ]
        ),
        origin=CardOrigin.ARRIVED,
        at=NOW,
    )
    defect, idea = (board.card("proj", n) for n in born)
    assert defect is not None and defect.place == Place(
        column=Column.BACKLOG, group=DEFECTS_RAIL, position=0
    )
    assert idea is not None and idea.place.group is None
    backlog = [g for g in board.layout("proj") if g.column == Column.BACKLOG]
    assert backlog[0].name == DEFECTS_RAIL and backlog[0].numbers == [defect.number]
    assert "reads on the defects rail" in board.history("proj", defect.number)[0].detail
    # The document's word moves a card on and off the rail.
    board.apply_effects(
        "proj",
        effects(
            rehomed=[
                Rehomed(card_number=defect.number, into_rail=False, kind=SuggestionKind.IDEA),
                Rehomed(card_number=idea.number, into_rail=True, kind=SuggestionKind.DEFECT),
            ]
        ),
        origin=CardOrigin.ARRIVED,
        at=NOW + timedelta(minutes=1),
    )
    moved_off = board.card("proj", defect.number)
    moved_on = board.card("proj", idea.number)
    assert moved_off is not None and moved_off.place.group is None
    assert moved_on is not None and moved_on.place.group == DEFECTS_RAIL
    row = board.history("proj", moved_on.number)[0]
    assert row.actor == Actor.CORPUS and "Kind: defect" in row.detail


def test_a_card_folds_under_its_leader_follows_it_and_is_not_moved_alone(board: Store):
    # #252 and #242 are Backlog suggestions in the fixture; #253 is a plan in Up next.
    board.apply_effects(
        "proj",
        effects(folded=[Folded(card_number=252, into=253, plan=PLAN)]),
        origin=CardOrigin.ARRIVED,
        at=NOW,
    )
    folded = board.card("proj", 252)
    assert folded is not None and folded.folded_into == 253
    assert folded.place.column == Column.UP_NEXT and folded.place.group is None
    layout = {(g.column, g.name): g.numbers for g in board.layout("proj")}
    assert 252 not in layout[(Column.BACKLOG, "Next to plan")], "a folded card takes no slot"
    assert 252 not in layout[(Column.UP_NEXT, None)] and 253 in layout[(Column.UP_NEXT, None)]
    assert layout[(Column.BACKLOG, "Next to plan")] == sorted(
        layout[(Column.BACKLOG, "Next to plan")],
        key=lambda n: board.card("proj", n).place.position,  # type: ignore[union-attr]
    )
    row = board.history("proj", 252)[0]
    assert row.kind == AuditKind.FOLDED_INTO and row.actor == Actor.CORPUS
    assert "Folded into #253: its suggestion is carried by docs/plans/together.md" in row.detail
    with pytest.raises(StoreRefusal, match="folded into #253"):
        board.move("proj", 252, Place(column=Column.BACKLOG, group=None, position=0), Actor.OWNER, NOW)
    # The leader moves; the folded card goes with it, by the same hand.
    board.move(
        "proj", 253, Place(column=Column.PLANNED, group=None, position=0), Actor.OWNER, NOW
    )
    followed = board.card("proj", 252)
    assert followed is not None and followed.place.column == Column.PLANNED
    trail = board.history("proj", 252)[0]
    assert trail.kind == AuditKind.MOVED and trail.actor == Actor.OWNER
    assert "followed #253, into which it is folded" in trail.detail
    assert 252 not in {n for g in board.layout("proj") for n in g.numbers}


def test_a_relink_by_a_plan_promotes_from_backlog_and_a_plan_naming_a_folded_card_unfolds_it(
    board: Store,
):
    board.apply_effects(
        "proj",
        effects(
            relinked=[
                Relinked(
                    card_number=252,
                    document=PLAN,
                    archived=False,
                    why="which carries this card's suggestion",
                    promote=True,
                )
            ],
            folded=[Folded(card_number=242, into=252, plan=PLAN)],
        ),
        origin=CardOrigin.ARRIVED,
        at=NOW,
    )
    leader = board.card("proj", 252)
    assert leader is not None and leader.link is not None and leader.link.stem == "together"
    assert leader.place.column == Column.PLANNED
    history = board.history("proj", 252)
    assert history[0].kind == AuditKind.MOVED and "a plan appeared for it" in history[0].detail
    assert history[1].kind == AuditKind.LINKED and "carries this card's suggestion" in history[1].detail
    follower = board.card("proj", 242)
    assert follower is not None and follower.folded_into == 252
    assert follower.place.column == Column.PLANNED
    # A second plan names #242 by number: it stands on its own again, in Planned.
    other = DocumentRef(kind=DocumentKind.PLAN, stem="own", path="docs/plans/own.md", title="Own")
    board.apply_effects(
        "proj",
        effects(
            relinked=[
                Relinked(
                    card_number=242,
                    document=other,
                    archived=False,
                    why="which names this card",
                    promote=True,
                )
            ]
        ),
        origin=CardOrigin.ARRIVED,
        at=NOW + timedelta(minutes=1),
    )
    unfolded = board.card("proj", 242)
    assert unfolded is not None and unfolded.folded_into is None
    assert unfolded.link is not None and unfolded.link.stem == "own"
    assert 242 in {n for g in board.layout("proj") if g.column == Column.PLANNED for n in g.numbers}
    assert any("Unfolded from #252" in h.detail for h in board.history("proj", 242))
    # A relink from Up next stays where the owner queued it.
    board.move(
        "proj", 242, Place(column=Column.UP_NEXT, group=None, position=0), Actor.OWNER, NOW
    )
    third = DocumentRef(kind=DocumentKind.PLAN, stem="third", path="docs/plans/third.md", title="T")
    board.apply_effects(
        "proj",
        effects(
            relinked=[
                Relinked(
                    card_number=242,
                    document=third,
                    archived=False,
                    why="which names this card",
                    promote=True,
                )
            ]
        ),
        origin=CardOrigin.ARRIVED,
        at=NOW + timedelta(minutes=2),
    )
    queued = board.card("proj", 242)
    assert queued is not None and queued.place.column == Column.UP_NEXT


def test_the_write_stamp_counts_every_commit_and_tells_this_stores_from_anothers(
    store: Store, project: Project
):
    seq0, _ = store.write_stamp()
    store.add_project(project)
    seq1, origin = store.write_stamp()
    assert seq1 == seq0 + 1 and origin == store.origin
    assert store.own_commits_upto(seq1) == 1 and store.own_commits_upto(seq1) == 0
    # A refused write commits nothing and stamps nothing.
    with pytest.raises(StoreRefusal):
        store.add_project(project)
    assert store.write_stamp()[0] == seq1 and store.own_commits_upto(seq1) == 0
    # Another process's write: the stamp moves, and none of it is this store's.
    other = Store(store.path)
    other.record_trunk("proj", TrunkState(level=True, behind=0, note=None, read_at=NOW))
    other.close()
    seq2, origin2 = store.write_stamp()
    assert seq2 == seq1 + 1 and origin2 == other.origin != store.origin
    assert (seq2 - seq1) - store.own_commits_upto(seq2) == 1
    # Own and foreign in one interval: the count still separates them.
    other = Store(store.path)
    store.record_trunk("proj", TrunkState(level=False, behind=1, note=None, read_at=NOW))
    other.record_trunk("proj", TrunkState(level=True, behind=0, note=None, read_at=NOW))
    other.close()
    seq3, _ = store.write_stamp()
    assert (seq3 - seq2) - store.own_commits_upto(seq3) == 1
