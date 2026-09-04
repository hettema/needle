"""The board's own store: SQLite, one file, outside every project's tree.

Every write is one transaction that carries its audit rows, so the store can
never hold a change without its trace. A move that would change nothing writes
nothing. A refusal raises `StoreRefusal` with the reason in one sentence and
leaves the store as it was; any other failure propagates with the database's
own words, which the page shows verbatim.
"""

import sqlite3
from datetime import datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from board.import_01 import Import01
from board.moves import GroupLayout, MoveRefused, apply_move
from board.reconcile import Effects
from domain.audit import AuditEntry, AuditKind
from domain.card import Actor, Card, CardOrigin, DocumentLink, Place
from domain.column import COLUMN_DEFINITIONS, Column
from domain.document import DocumentKind, DocumentRef
from domain.gate import Gate
from domain.project import Project
from domain.row import Row, RowKind
from infrastructure.schema import AuditRow, CardRow, CardRowRow, GroupRow, ProjectRow

_COLUMN_ORDER: dict[str, int] = {d.column.value: i for i, d in enumerate(COLUMN_DEFINITIONS)}
_MIGRATIONS = Path(__file__).parent / "migrations"


class StoreRefusal(Exception):
    """The store declines the write and nothing has changed; the message says why."""


def _set_pragmas(connection: sqlite3.Connection, record: object) -> None:
    cursor = connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


def open_engine(path: Path) -> Engine:
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite+pysqlite:///{path}", connect_args={"timeout": 5})
    event.listen(engine, "connect", _set_pragmas)
    return engine


def migrate(engine: Engine) -> None:
    config = Config()
    config.set_main_option("script_location", str(_MIGRATIONS))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")


class Store:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.engine = open_engine(self.path)
        migrate(self.engine)

    def close(self) -> None:
        """Release every pooled connection. A store is closed by whoever opened it."""
        self.engine.dispose()

    # ── projects ───────────────────────────────────────────────────────

    def add_project(self, project: Project) -> None:
        with Session(self.engine) as session, session.begin():
            existing = session.get(ProjectRow, project.slug)
            if existing is not None:
                raise StoreRefusal(
                    f'A project with the slug "{project.slug}" is already on the board, '
                    f"at {existing.path}."
                )
            same_path = session.scalar(select(ProjectRow).where(ProjectRow.path == project.path))
            if same_path is not None:
                raise StoreRefusal(f"{project.path} is already on the board as {same_path.slug}.")
            session.add(
                ProjectRow(
                    slug=project.slug,
                    name=project.name,
                    path=project.path,
                    registered_at=project.registered_at,
                    next_card_number=1,
                    imported_01_at=None,
                )
            )

    def projects(self) -> list[Project]:
        with Session(self.engine) as session:
            rows = session.scalars(select(ProjectRow).order_by(ProjectRow.registered_at)).all()
            return [_project(r) for r in rows]

    def project(self, slug: str) -> Project:
        with Session(self.engine) as session:
            row = session.get(ProjectRow, slug)
            if row is None:
                raise StoreRefusal(f'No project "{slug}" is on the board.')
            return _project(row)

    def has_import(self, slug: str) -> bool:
        with Session(self.engine) as session:
            row = session.get(ProjectRow, slug)
            return row is not None and row.imported_01_at is not None

    # ── reading ────────────────────────────────────────────────────────

    def layout(self, slug: str) -> list[GroupLayout]:
        with Session(self.engine) as session:
            return _layout(session, slug)

    def cards(self, slug: str) -> list[Card]:
        with Session(self.engine) as session:
            groups = {
                g.id: g
                for g in session.scalars(select(GroupRow).where(GroupRow.project_slug == slug))
            }
            rows = _rows_by_card(session, slug)
            cards = session.scalars(select(CardRow).where(CardRow.project_slug == slug)).all()
            return [_card(c, groups[c.group_id], rows.get(c.number, [])) for c in cards]

    def card(self, slug: str, number: int) -> Card | None:
        with Session(self.engine) as session:
            row = session.get(CardRow, (slug, number))
            if row is None:
                return None
            group = session.get(GroupRow, row.group_id)
            assert group is not None
            rows = _rows_by_card(session, slug, number).get(number, [])
            return _card(row, group, rows)

    def history(self, slug: str, number: int) -> list[AuditEntry]:
        with Session(self.engine) as session:
            rows = session.scalars(
                select(AuditRow)
                .where(AuditRow.project_slug == slug, AuditRow.card_number == number)
                .order_by(AuditRow.id.desc())
            ).all()
            return [_audit_entry(r) for r in rows]

    # ── writing ────────────────────────────────────────────────────────

    def move(self, slug: str, number: int, to: Place, actor: Actor, at: datetime) -> Card:
        with Session(self.engine) as session, session.begin():
            if session.get(ProjectRow, slug) is None:
                raise StoreRefusal(f'No project "{slug}" is on the board.')
            if to.group is None:
                _landing_group(session, slug, to.column)
            layout = _layout(session, slug)
            try:
                result = apply_move(layout, number, to)
            except MoveRefused as refusal:
                raise StoreRefusal(str(refusal)) from refusal
            if result.changed:
                for group in (result.source, result.target):
                    _write_positions(session, slug, group)
                _audit(
                    session,
                    slug,
                    number,
                    at=at,
                    actor=actor,
                    kind=AuditKind.MOVED,
                    from_place=result.from_place,
                    to_place=result.to_place,
                    detail=_describe_move(result.from_place, result.to_place),
                )
            session.flush()
            row = session.get(CardRow, (slug, number))
            assert row is not None
            group_row = session.get(GroupRow, row.group_id)
            assert group_row is not None
            return _card(row, group_row, _rows_by_card(session, slug, number).get(number, []))

    def apply_effects(
        self, slug: str, effects: Effects, *, origin: CardOrigin, at: datetime
    ) -> list[int]:
        """Make the corpus read true in the store. Returns the numbers born."""
        born: list[int] = []
        with Session(self.engine) as session, session.begin():
            project = session.get(ProjectRow, slug)
            if project is None:
                raise StoreRefusal(f'No project "{slug}" is on the board.')
            for renamed in effects.renamed:
                card = session.get(CardRow, (slug, renamed.card_number))
                assert card is not None
                card.link_stem = renamed.document.stem
                card.link_title = renamed.document.title
                card.link_archived = False
                if renamed.document.path not in card.citations:
                    card.citations = [*card.citations, renamed.document.path]
                _audit(
                    session,
                    slug,
                    card.number,
                    at=at,
                    actor=Actor.CORPUS,
                    kind=AuditKind.RENAMED,
                    from_place=None,
                    to_place=None,
                    detail=f"Its document was renamed from {renamed.old_stem} to "
                    f"{renamed.document.stem}; matched by title.",
                )
            for relinked in effects.relinked:
                card = session.get(CardRow, (slug, relinked.card_number))
                assert card is not None
                card.link_kind = relinked.document.kind.value
                card.link_stem = relinked.document.stem
                card.link_title = relinked.document.title
                card.link_archived = False
                if relinked.document.path not in card.citations:
                    card.citations = [*card.citations, relinked.document.path]
                _audit(
                    session,
                    slug,
                    card.number,
                    at=at,
                    actor=Actor.CORPUS,
                    kind=AuditKind.LINKED,
                    from_place=None,
                    to_place=None,
                    detail=f"Linked to {relinked.document.path}, which names this card.",
                )
            for archived in effects.archived:
                card = session.get(CardRow, (slug, archived.card_number))
                assert card is not None
                card.link_archived = True
                _audit(
                    session,
                    slug,
                    card.number,
                    at=at,
                    actor=Actor.CORPUS,
                    kind=AuditKind.ARCHIVED,
                    from_place=None,
                    to_place=None,
                    detail=f"Its document was archived to {archived.document.path}.",
                )
            for birth in effects.born:
                group = _landing_group(session, slug, birth.column)
                position = _group_size(session, group.id)
                number = project.next_card_number
                project.next_card_number = number + 1
                session.add(
                    CardRow(
                        project_slug=slug,
                        number=number,
                        group_id=group.id,
                        position=position,
                        title=birth.document.title,
                        gate=None,
                        tags=[],
                        deep="",
                        citations=[birth.document.path],
                        link_kind=birth.document.kind.value,
                        link_stem=birth.document.stem,
                        link_title=birth.document.title,
                        link_archived=False,
                        origin=origin.value,
                        born_at=at,
                    )
                )
                place = Place(column=birth.column, group=None, position=position)
                how = "at registration" if origin == CardOrigin.FOUNDING else "after registration"
                _audit(
                    session,
                    slug,
                    number,
                    at=at,
                    actor=Actor.CORPUS,
                    kind=AuditKind.BORN,
                    from_place=None,
                    to_place=place,
                    detail=f"Born from {birth.document.path}, {how}.",
                )
                born.append(number)
        return born

    def import_01(self, slug: str, imported: Import01, at: datetime) -> None:
        with Session(self.engine) as session, session.begin():
            project = session.get(ProjectRow, slug)
            if project is None:
                raise StoreRefusal(f'No project "{slug}" is on the board.')
            if project.imported_01_at is not None:
                raise StoreRefusal(
                    f"{slug} already imported its 0.1 card file on "
                    f"{project.imported_01_at.isoformat()}; the import runs once."
                )
            if session.scalar(select(CardRow).where(CardRow.project_slug == slug)) is not None:
                raise StoreRefusal(
                    f"{slug} already has cards; the 0.1 import runs on an empty board."
                )
            group_ids: dict[tuple[Column, str | None], int] = {}
            for group in imported.groups:
                row = GroupRow(
                    project_slug=slug,
                    column=group.column.value,
                    name=group.name,
                    position=group.position,
                )
                session.add(row)
                session.flush()
                group_ids[(group.column, group.name)] = row.id
            rows_by_number = {r.number: r.rows for r in imported.rows}
            for card in imported.cards:
                session.add(
                    CardRow(
                        project_slug=slug,
                        number=card.number,
                        group_id=group_ids[(card.place.column, card.place.group)],
                        position=card.place.position,
                        title=card.title,
                        gate=card.gate.value if card.gate else None,
                        tags=card.tags,
                        deep=card.deep,
                        citations=card.citations,
                        link_kind=card.link.kind.value if card.link else None,
                        link_stem=card.link.stem if card.link else None,
                        link_title=card.link.title if card.link else None,
                        link_archived=card.link.archived if card.link else None,
                        origin=CardOrigin.IMPORTED.value,
                        born_at=at,
                    )
                )
                rows = rows_by_number.get(card.number, [])
                for position, row in enumerate(rows):
                    session.add(
                        CardRowRow(
                            project_slug=slug,
                            card_number=card.number,
                            position=position,
                            kind=row.kind.value,
                            text=row.text,
                        )
                    )
                _audit(
                    session,
                    slug,
                    card.number,
                    at=at,
                    actor=Actor.IMPORT,
                    kind=AuditKind.BORN,
                    from_place=None,
                    to_place=card.place,
                    detail=f"Born from Needle 0.1's card file — column, position and "
                    f"{len(rows)} row{'s' if len(rows) != 1 else ''}.",
                )
                if card.link is not None:
                    _audit(
                        session,
                        slug,
                        card.number,
                        at=at,
                        actor=Actor.IMPORT,
                        kind=AuditKind.LINKED,
                        from_place=None,
                        to_place=None,
                        detail=f"Linked to {card.citations[0]}, cited on the 0.1 card.",
                    )
            for retired in imported.retired:
                _audit(
                    session,
                    slug,
                    retired.number,
                    at=at,
                    actor=Actor.IMPORT,
                    kind=AuditKind.RETIRED,
                    from_place=None,
                    to_place=None,
                    detail=f"Retired in Needle 0.1: {retired.reason}",
                )
            project.next_card_number = max(project.next_card_number, imported.next_number)
            project.imported_01_at = at


# ── helpers ────────────────────────────────────────────────────────────


def _project(row: ProjectRow) -> Project:
    return Project(slug=row.slug, name=row.name, path=row.path, registered_at=row.registered_at)


def _link(row: CardRow) -> DocumentLink | None:
    if row.link_kind is None or row.link_stem is None:
        return None
    return DocumentLink(
        kind=DocumentKind(row.link_kind),
        stem=row.link_stem,
        title=row.link_title or "",
        archived=bool(row.link_archived),
    )


def _card(row: CardRow, group: GroupRow, rows: list[Row]) -> Card:
    return Card(
        number=row.number,
        project=row.project_slug,
        place=Place(column=Column(group.column), group=group.name, position=row.position),
        title=row.title,
        gate=Gate(row.gate) if row.gate else None,
        tags=list(row.tags),
        deep=row.deep,
        citations=list(row.citations),
        link=_link(row),
        origin=CardOrigin(row.origin),
        born_at=row.born_at,
        rows=rows,
    )


def _rows_by_card(session: Session, slug: str, number: int | None = None) -> dict[int, list[Row]]:
    query = select(CardRowRow).where(CardRowRow.project_slug == slug)
    if number is not None:
        query = query.where(CardRowRow.card_number == number)
    query = query.order_by(CardRowRow.card_number, CardRowRow.position)
    out: dict[int, list[Row]] = {}
    for row in session.scalars(query):
        out.setdefault(row.card_number, []).append(Row(kind=RowKind(row.kind), text=row.text))
    return out


def _layout(session: Session, slug: str) -> list[GroupLayout]:
    groups = session.scalars(select(GroupRow).where(GroupRow.project_slug == slug)).all()
    groups = sorted(groups, key=lambda g: (_COLUMN_ORDER[g.column], g.position))
    cards = session.scalars(
        select(CardRow).where(CardRow.project_slug == slug).order_by(CardRow.position)
    ).all()
    numbers: dict[int, list[int]] = {g.id: [] for g in groups}
    for card in cards:
        numbers[card.group_id].append(card.number)
    return [
        GroupLayout(column=Column(g.column), name=g.name, numbers=numbers[g.id]) for g in groups
    ]


def _landing_group(session: Session, slug: str, column: Column) -> GroupRow:
    """The column's unnamed group, made at the column's end when it has none.

    A card born from the corpus, or moved to a column without naming a group,
    lands here: below the owner's named groups, never above them.
    """
    existing = session.scalar(
        select(GroupRow).where(
            GroupRow.project_slug == slug,
            GroupRow.column == column.value,
            GroupRow.name.is_(None),
        )
    )
    if existing is not None:
        return existing
    siblings = session.scalars(
        select(GroupRow).where(GroupRow.project_slug == slug, GroupRow.column == column.value)
    ).all()
    position = max([g.position for g in siblings], default=-1) + 1
    group = GroupRow(project_slug=slug, column=column.value, name=None, position=position)
    session.add(group)
    session.flush()
    return group


def _group_size(session: Session, group_id: int) -> int:
    return len(session.scalars(select(CardRow.number).where(CardRow.group_id == group_id)).all())


def _write_positions(session: Session, slug: str, group: GroupLayout) -> None:
    row = session.scalar(
        select(GroupRow).where(
            GroupRow.project_slug == slug,
            GroupRow.column == group.column.value,
            GroupRow.name.is_(None) if group.name is None else GroupRow.name == group.name,
        )
    )
    assert row is not None
    for position, number in enumerate(group.numbers):
        card = session.get(CardRow, (slug, number))
        assert card is not None
        card.group_id = row.id
        card.position = position


def _describe_move(from_place: Place, to_place: Place) -> str:
    if from_place.column == to_place.column and from_place.group == to_place.group:
        return (
            f"Ranked {to_place.position + 1} in {to_place.column} — was {from_place.position + 1}"
        )
    return f"Moved {_where(from_place)} → {_where(to_place)}"


def _where(place: Place) -> str:
    if place.group is None:
        return f"{place.column}"
    return f"{place.column} · {place.group}"


def _audit(
    session: Session,
    slug: str,
    number: int,
    *,
    at: datetime,
    actor: Actor,
    kind: AuditKind,
    from_place: Place | None,
    to_place: Place | None,
    detail: str,
) -> None:
    session.add(
        AuditRow(
            project_slug=slug,
            card_number=number,
            at=at,
            actor=actor.value,
            kind=kind.value,
            from_column=from_place.column.value if from_place else None,
            from_group=from_place.group if from_place else None,
            from_position=from_place.position if from_place else None,
            to_column=to_place.column.value if to_place else None,
            to_group=to_place.group if to_place else None,
            to_position=to_place.position if to_place else None,
            detail=detail,
        )
    )


def _audit_entry(row: AuditRow) -> AuditEntry:
    from_place = (
        Place(column=Column(row.from_column), group=row.from_group, position=row.from_position or 0)
        if row.from_column
        else None
    )
    to_place = (
        Place(column=Column(row.to_column), group=row.to_group, position=row.to_position or 0)
        if row.to_column
        else None
    )
    return AuditEntry(
        id=row.id,
        at=row.at,
        actor=Actor(row.actor),
        kind=AuditKind(row.kind),
        card_number=row.card_number,
        from_place=from_place,
        to_place=to_place,
        detail=row.detail,
    )


def document_ref_path(ref: DocumentRef) -> str:
    return ref.path
