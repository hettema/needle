"""The board's own store: SQLite, one file, outside every project's tree.

Every write is one transaction that carries its audit rows, so the store can
never hold a change without its trace. A move that would change nothing writes
nothing. A refusal raises `StoreRefusal` with the reason in one sentence and
leaves the store as it was; any other failure propagates with the database's
own words, which the page shows verbatim.
"""

import re
import sqlite3
from datetime import datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, delete, event, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from board.import_01 import Import01
from board.moves import GroupLayout, MoveRefused, MoveResult, apply_move
from board.reconcile import Effects
from board.signals import read_or_decline
from domain.audit import AuditEntry, AuditKind
from domain.board import TrunkState
from domain.card import Actor, Card, CardOrigin, DocumentLink, Place
from domain.column import COLUMN_DEFINITIONS, Column
from domain.document import DocumentKind, DocumentRef
from domain.evidence import Evidence
from domain.gate import Gate
from domain.hook import HookEvent, HookKind, HookPosted
from domain.lane import Discussion, LaneRecord
from domain.launch import Rescue
from domain.project import Project
from domain.row import Row, RowKind
from domain.session import SessionSlot
from domain.signal import Reading
from domain.slot import Model, Rung
from domain.watercooler import WatercoolerLine
from domain.window import Window, WindowKind
from infrastructure.schema import (
    AuditRow,
    CardRow,
    CardRowRow,
    DiscussionRow,
    GroupRow,
    HookEventRow,
    LaneRow,
    ProjectRow,
    ReadingRow,
    RescueRow,
    SessionSlotRow,
    TrunkRow,
    WatercoolerRow,
    WindowRow,
)

_COLUMN_ORDER: dict[str, int] = {d.column.value: i for i, d in enumerate(COLUMN_DEFINITIONS)}
_MIGRATIONS = Path(__file__).parent / "migrations"
ONE_PER_CARD: frozenset[RowKind] = frozenset(
    {RowKind.DELIVERED, RowKind.WATCH, RowKind.REVIEW, RowKind.VERDICT}
)
"""Record rows a card carries once: writing one again replaces it, so a
close written twice never says two things about what shipped, and a card
never carries two verdicts."""
ROW_DETAIL_LENGTH = 140
_CONVERSATION = re.compile(r"conversation\s+([0-9a-f]{8})\b", re.I)
"""How a document names the conversation it was born from: the Idea door's
brief asks the session to write `conversation <short id>` on its `Found by`
line, and the birth row then says so from the board's own record of that
conversation (plan 07, item 1)."""


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

    def placements(self, slug: str) -> dict[int, AuditEntry]:
        """Each card's placement: the audit row that last put it in its column
        (a move, else its birth), in one query. What a read re-tests."""
        with Session(self.engine) as session:
            rows = session.scalars(
                select(AuditRow)
                .where(
                    AuditRow.project_slug == slug,
                    AuditRow.kind.in_([AuditKind.MOVED.value, AuditKind.BORN.value]),
                )
                .order_by(AuditRow.id)
            )
            out: dict[int, AuditEntry] = {}
            for row in rows:
                if row.to_column is not None:
                    out[row.card_number] = _audit_entry(row)
            return out

    # ── writing ────────────────────────────────────────────────────────

    def move(
        self,
        slug: str,
        number: int,
        to: Place,
        actor: Actor,
        at: datetime,
        *,
        detail: str | None = None,
        evidence: Evidence | None = None,
    ) -> Card:
        """Put the card there. A machine move names its reason in `detail`
        and the predicate it satisfied in `evidence` (plan 04, item 1), so a
        later read can ask that predicate again; a move into Executed needs
        a WATCH row naming a signal (plan 03, item 5), whoever moves it."""
        if actor == Actor.MACHINE and not detail:
            raise StoreRefusal("A machine move must say why, in one sentence.")
        if actor == Actor.MACHINE and evidence is None:
            raise StoreRefusal("A machine move must name the evidence it rests on.")
        with Session(self.engine) as session, session.begin():
            if session.get(ProjectRow, slug) is None:
                raise StoreRefusal(f'No project "{slug}" is on the board.')
            _move(session, slug, number, to, actor, at, detail=detail, evidence=evidence)
            session.flush()
            return _card_now(session, slug, number)

    def rule_on_verdict(
        self,
        slug: str,
        number: int,
        at: datetime,
        *,
        accepted: bool,
        word: str | None,
        to: Place | None,
        replace: bool,
        said: str,
    ) -> Card:
        """The owner's ruling on a card's verdict, in one act (plan 05): the
        VERDICT row becomes a RULED row carrying his word, and the card moves
        where the verdict said, or stays. `replace` re-places a card that
        stays by the owner's own hand, so a placement the board doubted
        becomes his word and is trusted from here — that is what accepting
        "stays" on a doubted card means."""
        with Session(self.engine) as session, session.begin():
            card = session.get(CardRow, (slug, number))
            if card is None:
                raise StoreRefusal(f"There is no card #{number} on this board.")
            existing = session.scalars(
                select(CardRowRow)
                .where(CardRowRow.project_slug == slug, CardRowRow.card_number == number)
                .order_by(CardRowRow.position)
            ).all()
            verdict_row = next((r for r in existing if r.kind == RowKind.VERDICT.value), None)
            if verdict_row is None:
                raise StoreRefusal(f"#{number} carries no verdict to rule on.")
            text = verdict_row.text
            session.delete(verdict_row)
            verb = "accepted" if accepted else "overturned"
            ruled = (
                f"accepted: {text}"
                if accepted
                else f"overturned: {word} — the verdict read: {text}"
            )
            session.add(
                CardRowRow(
                    project_slug=slug,
                    card_number=number,
                    position=max([r.position for r in existing], default=-1) + 1,
                    kind=RowKind.RULED.value,
                    text=ruled,
                )
            )
            _audit(
                session,
                slug,
                number,
                at=at,
                actor=Actor.OWNER,
                kind=AuditKind.ROW,
                from_place=None,
                to_place=None,
                detail=f"VERDICT {verb}: {text}" + (f" — his word: {word}" if word else ""),
            )
            session.flush()
            if to is not None:
                _move(session, slug, number, to, Actor.OWNER, at, detail=said, evidence=None)
            elif replace:
                group = session.get(GroupRow, card.group_id)
                assert group is not None
                place = Place(column=Column(group.column), group=group.name, position=card.position)
                _audit(
                    session,
                    slug,
                    number,
                    at=at,
                    actor=Actor.OWNER,
                    kind=AuditKind.MOVED,
                    from_place=place,
                    to_place=place,
                    detail=f"Kept in {_where(place)} — {said}",
                )
            session.flush()
            return _card_now(session, slug, number)

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
                card.link_archived = relinked.archived
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
                conversation = _conversation_named(session, slug, birth.found_by)
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
                detail = f"Born from {birth.document.path}, {how}."
                if conversation is not None:
                    day = conversation.started_at.date().isoformat()
                    detail += (
                        f" Born from a conversation on {day} ({conversation.session_id[:8]} on "
                        f"{conversation.slot}, from the Idea door)."
                    )
                _audit(
                    session,
                    slug,
                    number,
                    at=at,
                    actor=Actor.CORPUS,
                    kind=AuditKind.BORN,
                    from_place=None,
                    to_place=place,
                    detail=detail,
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

    def add_row(self, slug: str, number: int, row: Row, actor: Actor, at: datetime) -> Card:
        """Write a row on the card, with its audit row. DELIVERED, WATCH and
        REVIEW are one per card and a second write replaces the first."""
        with Session(self.engine) as session, session.begin():
            card = session.get(CardRow, (slug, number))
            if card is None:
                raise StoreRefusal(f"There is no card #{number} on this board.")
            existing = session.scalars(
                select(CardRowRow)
                .where(CardRowRow.project_slug == slug, CardRowRow.card_number == number)
                .order_by(CardRowRow.position)
            ).all()
            replaced = (
                next((r for r in existing if r.kind == row.kind.value), None)
                if row.kind in ONE_PER_CARD
                else None
            )
            was: str | None = None
            if replaced is not None:
                was = replaced.text
                replaced.text = row.text
                verb = "rewritten"
            else:
                position = max([r.position for r in existing], default=-1) + 1
                session.add(
                    CardRowRow(
                        project_slug=slug,
                        card_number=number,
                        position=position,
                        kind=row.kind.value,
                        text=row.text,
                    )
                )
                verb = "written"
            shown = (
                row.text
                if len(row.text) <= ROW_DETAIL_LENGTH
                else row.text[: ROW_DETAIL_LENGTH - 1] + "…"
            )
            # A rewrite keeps the whole previous text in the history, not a
            # cut of it: the 54 WATCH rows translated on 2026-09-04 are read
            # from here when the new row is doubted (plan 04, item 3).
            _audit(
                session,
                slug,
                number,
                at=at,
                actor=actor,
                kind=AuditKind.ROW,
                from_place=None,
                to_place=None,
                detail=f"{row.kind.value} {verb}: {shown}"
                + (f" — it read: {was}" if was is not None else ""),
            )
            session.flush()
            return _card_now(session, slug, number)

    def note(
        self, slug: str, number: int, kind: AuditKind, actor: Actor, at: datetime, detail: str
    ) -> None:
        """An audit row that moves nothing: a door opened, a session ended, a
        signal read. The card's history is where the machine says what it did."""
        if not detail:
            raise StoreRefusal("A note on a card must say something.")
        with Session(self.engine) as session, session.begin():
            if session.get(CardRow, (slug, number)) is None:
                raise StoreRefusal(f"There is no card #{number} on this board.")
            _audit(
                session,
                slug,
                number,
                at=at,
                actor=actor,
                kind=kind,
                from_place=None,
                to_place=None,
                detail=detail,
            )

    # ── what sessions push ─────────────────────────────────────────────

    def record_hook_events(
        self, events: list[tuple[HookPosted, str | None, int | None]]
    ) -> list[HookEvent]:
        """Keep every event a hook posted, attributed to (project, card) as
        the caller resolved it from the working directory."""
        out: list[HookEvent] = []
        with Session(self.engine) as session, session.begin():
            for posted, slug, number in events:
                row = HookEventRow(
                    at=posted.at,
                    kind=posted.kind.value,
                    session_id=posted.session_id,
                    cwd=posted.cwd,
                    project_slug=slug,
                    card_number=number,
                    source=posted.source,
                    message=posted.message,
                    reason=posted.reason,
                    error=posted.error,
                    transcript_path=posted.transcript_path,
                )
                session.add(row)
                session.flush()
                out.append(_hook_event(row))
        return out

    def hook_events(self, slug: str, number: int | None = None) -> list[HookEvent]:
        with Session(self.engine) as session:
            query = select(HookEventRow).where(HookEventRow.project_slug == slug)
            if number is not None:
                query = query.where(HookEventRow.card_number == number)
            return [_hook_event(r) for r in session.scalars(query.order_by(HookEventRow.id))]

    def hook_events_of_session(self, session_id: str) -> list[HookEvent]:
        with Session(self.engine) as session:
            rows = session.scalars(
                select(HookEventRow)
                .where(HookEventRow.session_id == session_id)
                .order_by(HookEventRow.id)
            )
            return [_hook_event(r) for r in rows]

    def record_discussion(
        self, slug: str, number: int | None, session_id: str, slot: str, at: datetime
    ) -> Discussion:
        """A conversation opened from the board; `number` is None for an idea."""
        with Session(self.engine) as session, session.begin():
            row = DiscussionRow(
                project_slug=slug,
                card_number=number,
                session_id=session_id,
                slot=slot,
                started_at=at,
            )
            session.add(row)
            session.flush()
            return _discussion(row)

    def discussions(self, slug: str) -> list[Discussion]:
        with Session(self.engine) as session:
            rows = session.scalars(
                select(DiscussionRow)
                .where(DiscussionRow.project_slug == slug)
                .order_by(DiscussionRow.id)
            )
            return [_discussion(r) for r in rows]

    # ── the watercooler ────────────────────────────────────────────────

    def say(
        self, slug: str, number: int | None, actor: Actor, at: datetime, text: str
    ) -> WatercoolerLine:
        """One line on the project's watercooler, from a card's lane or the board."""
        text = text.strip()
        if not text:
            raise StoreRefusal("A watercooler line must say something.")
        with Session(self.engine) as session, session.begin():
            if session.get(ProjectRow, slug) is None:
                raise StoreRefusal(f'No project "{slug}" is on the board.')
            if number is not None and session.get(CardRow, (slug, number)) is None:
                raise StoreRefusal(f"There is no card #{number} on this board.")
            row = WatercoolerRow(
                project_slug=slug, card_number=number, actor=actor.value, at=at, text=text
            )
            session.add(row)
            session.flush()
            return _watercooler_line(row)

    def watercooler(self, slug: str, *, limit: int | None = None) -> list[WatercoolerLine]:
        """The project's lines, oldest first; with `limit`, the newest that many."""
        with Session(self.engine) as session:
            query = select(WatercoolerRow).where(WatercoolerRow.project_slug == slug)
            if limit is not None:
                rows = session.scalars(query.order_by(WatercoolerRow.id.desc()).limit(limit)).all()
                return [_watercooler_line(r) for r in reversed(rows)]
            return [
                _watercooler_line(r) for r in session.scalars(query.order_by(WatercoolerRow.id))
            ]

    # ── the board's record of each lane ────────────────────────────────

    def record_lane(self, record: LaneRecord) -> None:
        with Session(self.engine) as session, session.begin():
            row = session.get(LaneRow, (record.project, record.card_number))
            if row is None:
                row = LaneRow(project_slug=record.project, card_number=record.card_number)
                session.add(row)
            row.name = record.name
            row.path = record.path
            row.branch = record.branch
            row.birth = record.birth
            row.tip = record.tip
            row.first_seen = record.first_seen
            row.last_seen = record.last_seen
            row.gone_at = record.gone_at
            row.folded_at = record.folded_at
            row.trunk_synced_at = record.trunk_synced_at
            row.main_synced_at = record.main_synced_at

    def lanes(self, slug: str) -> list[LaneRecord]:
        with Session(self.engine) as session:
            rows = session.scalars(
                select(LaneRow).where(LaneRow.project_slug == slug).order_by(LaneRow.card_number)
            )
            return [_lane_record(r) for r in rows]

    def lane(self, slug: str, number: int) -> LaneRecord | None:
        with Session(self.engine) as session:
            row = session.get(LaneRow, (slug, number))
            return None if row is None else _lane_record(row)

    def forget_lane(self, slug: str, number: int) -> None:
        """The card is being launched again: its lane record starts over."""
        with Session(self.engine) as session, session.begin():
            row = session.get(LaneRow, (slug, number))
            if row is not None:
                session.delete(row)

    # ── signal readings ────────────────────────────────────────────────

    def record_reading(
        self,
        slug: str,
        number: int,
        at: datetime,
        delivered: bool | None,
        words: str,
        actor: Actor,
    ) -> Reading:
        with Session(self.engine) as session, session.begin():
            row = ReadingRow(
                project_slug=slug, card_number=number, at=at, delivered=delivered, words=words
            )
            session.add(row)
            said = {True: "delivered", False: "not delivered", None: "unreadable"}[delivered]
            _audit(
                session,
                slug,
                number,
                at=at,
                actor=actor,
                kind=AuditKind.SIGNAL,
                from_place=None,
                to_place=None,
                detail=f"Signal read as {said}: {words}",
            )
            session.flush()
            return _reading(row)

    def readings(self, slug: str, number: int) -> list[Reading]:
        with Session(self.engine) as session:
            rows = session.scalars(
                select(ReadingRow)
                .where(ReadingRow.project_slug == slug, ReadingRow.card_number == number)
                .order_by(ReadingRow.id.desc())
            )
            return [_reading(r) for r in rows]

    def last_readings(self, slug: str) -> dict[int, Reading]:
        with Session(self.engine) as session:
            rows = session.scalars(
                select(ReadingRow).where(ReadingRow.project_slug == slug).order_by(ReadingRow.id)
            )
            out: dict[int, Reading] = {}
            for row in rows:
                out[row.card_number] = _reading(row)
            return out

    # ── the trunk ──────────────────────────────────────────────────────

    def record_trunk(self, slug: str, state: TrunkState) -> None:
        with Session(self.engine) as session, session.begin():
            row = session.get(TrunkRow, slug)
            if row is None:
                row = TrunkRow(project_slug=slug, behind=0)
                session.add(row)
            row.level = state.level
            row.behind = state.behind
            row.note = state.note
            row.read_at = state.read_at

    def trunk(self, slug: str) -> TrunkState:
        with Session(self.engine) as session:
            row = session.get(TrunkRow, slug)
            if row is None:
                return TrunkState(level=None, behind=0, note=None, read_at=None)
            return TrunkState(
                level=row.level, behind=row.behind, note=row.note, read_at=row.read_at
            )

    # ── the runtime's records ──────────────────────────────────────────
    # Three tables with no foreign key to the board's: where a session runs,
    # the rescues it has had, the windows it was given. Clearing a session's
    # rescues never touches its slot (plan 02, item 3).

    def record_session_slot(self, record: SessionSlot) -> None:
        """Where a session runs, written only by the thing that started or moved it."""
        with Session(self.engine) as session, session.begin():
            row = session.get(SessionSlotRow, record.session_id)
            if row is None:
                session.add(
                    SessionSlotRow(
                        session_id=record.session_id,
                        slot=record.slot,
                        card=record.card,
                        scope=record.scope,
                        recorded_at=record.recorded_at,
                    )
                )
            else:
                row.slot = record.slot
                row.card = record.card
                row.scope = record.scope
                row.recorded_at = record.recorded_at

    def session_slot(self, session_id: str) -> SessionSlot | None:
        with Session(self.engine) as session:
            row = session.get(SessionSlotRow, session_id)
            return None if row is None else _session_slot(row)

    def session_slots(self) -> list[SessionSlot]:
        with Session(self.engine) as session:
            rows = session.scalars(select(SessionSlotRow).order_by(SessionSlotRow.recorded_at))
            return [_session_slot(r) for r in rows]

    def record_rescue(
        self, session_id: str, from_rung: Rung | None, to_rung: Rung, reason: str, at: datetime
    ) -> Rescue:
        with Session(self.engine) as session, session.begin():
            row = RescueRow(
                session_id=session_id,
                from_slot=from_rung.slot if from_rung else None,
                from_model=from_rung.model.value if from_rung and from_rung.model else None,
                to_slot=to_rung.slot,
                to_model=to_rung.model.value if to_rung.model else None,
                reason=reason,
                at=at,
            )
            session.add(row)
            session.flush()
            return _rescue(row)

    def rescues(self, session_id: str) -> list[Rescue]:
        with Session(self.engine) as session:
            rows = session.scalars(
                select(RescueRow).where(RescueRow.session_id == session_id).order_by(RescueRow.id)
            )
            return [_rescue(r) for r in rows]

    def clear_rescues(self, session_id: str) -> int:
        """Forget a session's rescue history. Its slot record is untouched."""
        with Session(self.engine) as session, session.begin():
            result = session.execute(delete(RescueRow).where(RescueRow.session_id == session_id))
            return int(result.rowcount or 0)

    def record_window(
        self, session_id: str, kind: WindowKind, app_id: str, address: str, at: datetime
    ) -> Window:
        with Session(self.engine) as session, session.begin():
            row = WindowRow(
                session_id=session_id,
                kind=kind.value,
                app_id=app_id,
                address=address,
                opened_at=at,
                closed_at=None,
            )
            session.add(row)
            session.flush()
            return _window(row)

    def windows(self, session_id: str | None = None, *, open_only: bool = False) -> list[Window]:
        with Session(self.engine) as session:
            query = select(WindowRow).order_by(WindowRow.id)
            if session_id is not None:
                query = query.where(WindowRow.session_id == session_id)
            if open_only:
                query = query.where(WindowRow.closed_at.is_(None))
            return [_window(r) for r in session.scalars(query)]

    def window_closed(self, window_id: int, at: datetime) -> None:
        """The runtime found the window gone. It records the close; it never causes one."""
        with Session(self.engine) as session, session.begin():
            row = session.get(WindowRow, window_id)
            if row is not None and row.closed_at is None:
                row.closed_at = at


# ── helpers ────────────────────────────────────────────────────────────


def _session_slot(row: SessionSlotRow) -> SessionSlot:
    return SessionSlot(
        session_id=row.session_id,
        slot=row.slot,
        card=row.card,
        scope=row.scope,
        recorded_at=row.recorded_at,
    )


def _rescue(row: RescueRow) -> Rescue:
    return Rescue(
        id=row.id,
        session_id=row.session_id,
        from_rung=(
            Rung(slot=row.from_slot, model=Model(row.from_model) if row.from_model else None)
            if row.from_slot
            else None
        ),
        to_rung=Rung(slot=row.to_slot, model=Model(row.to_model) if row.to_model else None),
        reason=row.reason,
        at=row.at,
    )


def _window(row: WindowRow) -> Window:
    return Window(
        id=row.id,
        session_id=row.session_id,
        kind=WindowKind(row.kind),
        app_id=row.app_id,
        address=row.address,
        opened_at=row.opened_at,
        closed_at=row.closed_at,
    )


def _hook_event(row: HookEventRow) -> HookEvent:
    return HookEvent(
        id=row.id,
        kind=HookKind(row.kind),
        session_id=row.session_id,
        cwd=row.cwd,
        at=row.at,
        source=row.source,
        message=row.message,
        reason=row.reason,
        error=row.error,
        transcript_path=row.transcript_path,
        project=row.project_slug,
        card_number=row.card_number,
    )


def _watercooler_line(row: WatercoolerRow) -> WatercoolerLine:
    return WatercoolerLine(
        id=row.id,
        project=row.project_slug,
        card_number=row.card_number,
        actor=Actor(row.actor),
        at=row.at,
        text=row.text,
    )


def _conversation_named(session: Session, slug: str, found_by: str | None) -> Discussion | None:
    """The idea conversation a document's `Found by` line names, when the
    board's own record holds one with that short id on this project."""
    match = _CONVERSATION.search(found_by or "")
    if match is None:
        return None
    short = match.group(1).lower()
    rows = session.scalars(
        select(DiscussionRow)
        .where(DiscussionRow.project_slug == slug, DiscussionRow.session_id.like(f"{short}%"))
        .order_by(DiscussionRow.id.desc())
    ).all()
    return _discussion(rows[0]) if rows else None


def _discussion(row: DiscussionRow) -> Discussion:
    return Discussion(
        id=row.id,
        project=row.project_slug,
        card_number=row.card_number,
        session_id=row.session_id,
        slot=row.slot,
        started_at=row.started_at,
    )


def _lane_record(row: LaneRow) -> LaneRecord:
    return LaneRecord(
        project=row.project_slug,
        card_number=row.card_number,
        name=row.name,
        path=row.path,
        branch=row.branch,
        birth=row.birth,
        tip=row.tip,
        first_seen=row.first_seen,
        last_seen=row.last_seen,
        gone_at=row.gone_at,
        folded_at=row.folded_at,
        trunk_synced_at=row.trunk_synced_at,
        main_synced_at=row.main_synced_at,
    )


def _reading(row: ReadingRow) -> Reading:
    return Reading(
        id=row.id, card_number=row.card_number, at=row.at, delivered=row.delivered, words=row.words
    )


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


def _card_now(session: Session, slug: str, number: int) -> Card:
    """The card as the transaction now holds it."""
    row = session.get(CardRow, (slug, number))
    assert row is not None
    group = session.get(GroupRow, row.group_id)
    assert group is not None
    return _card(row, group, _rows_by_card(session, slug, number).get(number, []))


def _move(
    session: Session,
    slug: str,
    number: int,
    to: Place,
    actor: Actor,
    at: datetime,
    *,
    detail: str | None,
    evidence: Evidence | None,
) -> MoveResult:
    """The move inside a transaction: the Executed guard, the landing group,
    the positions and the audit row. A move that changes nothing writes nothing."""
    if to.column == Column.EXECUTED:
        rows = _rows_by_card(session, slug, number).get(number, [])
        watch = next((r.text for r in rows if r.kind == RowKind.WATCH), None)
        signal, why = read_or_decline(watch)
        if signal is None:
            raise StoreRefusal(
                f"#{number} cannot enter Executed: {why}. Done is a closed loop, and "
                "the loop starts with the signal named."
            )
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
        said = _describe_move(result.from_place, result.to_place)
        _audit(
            session,
            slug,
            number,
            at=at,
            actor=actor,
            kind=AuditKind.MOVED,
            from_place=result.from_place,
            to_place=result.to_place,
            detail=f"{said} — {detail}" if detail else said,
            evidence=evidence,
        )
    return result


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
    evidence: Evidence | None = None,
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
            evidence=evidence.value if evidence else None,
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
        evidence=Evidence(row.evidence) if row.evidence else None,
    )


def document_ref_path(ref: DocumentRef) -> str:
    return ref.path
