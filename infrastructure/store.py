"""The board's own store: SQLite, one file, outside every project's tree.

Every write is one transaction that carries its audit rows, so the store can
never hold a change without its trace. A move that would change nothing writes
nothing. A refusal raises `StoreRefusal` with the reason in one sentence and
leaves the store as it was; any other failure propagates with the database's
own words, which the page shows verbatim.
"""

import json
import re
import sqlite3
import threading
import uuid
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, delete, event, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from board.import_01 import Import01
from board.moves import GroupLayout, MoveRefused, MoveResult, apply_move
from board.reconcile import PROMOTED_FROM, Effects
from board.signals import read_or_decline
from domain.audit import AuditEntry, AuditKind
from domain.board import TrunkState
from domain.call import Call, HowKnown
from domain.card import Actor, Card, CardOrigin, DocumentLink, Place, RowRecord
from domain.column import COLUMN_DEFINITIONS, DEFECTS_RAIL, DEFECTS_RAIL_POSITION, Column
from domain.dial import Dial, DialChange, Filer, FixLane, FixStage, RailCount
from domain.document import DOCUMENT_FOLDER, DocumentKind, DocumentRef, SuggestionKind
from domain.ending import Cause, Death, Park, Recovery, Sighting
from domain.entrance import Entrance
from domain.evidence import Evidence
from domain.focus import (
    Acceptance,
    AcceptedMove,
    Decline,
    FocusCall,
    FocusCheck,
    FocusRecheck,
    FocusRuling,
    FocusVerdict,
    Leverage,
    LeverageReading,
    Likelihood,
    MeasureReading,
    MeasureSide,
    ReadingKind,
    RecheckOutcome,
)
from domain.gate import Gate
from domain.hook import HeardMark, HookEvent, HookKind, HookPosted
from domain.lane import Discussion, LaneRecord
from domain.launch import Rescue
from domain.machine import HighWater, Machine, Timing
from domain.project import Project
from domain.row import Row, RowKind
from domain.session import SessionSlot
from domain.signal import Reading, SessionWork, WindowlessSession
from domain.slot import Rung
from domain.triage import (
    CorpusLane,
    CorpusLaneKind,
    Direction,
    TitleReading,
    TitleVerdict,
    Triage,
    TriageResult,
)
from domain.watercooler import WatercoolerLine
from domain.window import Window, WindowKind
from infrastructure.schema import (
    AuditRow,
    CallRow,
    CardRow,
    CardRowRow,
    CloneRow,
    CorpusLaneRow,
    DeathRow,
    DialChangeRow,
    DialRow,
    DiscussionRow,
    FixLaneRow,
    FocusCallRow,
    FocusCheckRow,
    FocusMeasureRow,
    FocusRecheckRow,
    FocusRulingRow,
    GroupRow,
    HeardNoteRow,
    HeardRow,
    HighWaterRow,
    HookEventRow,
    LaneRow,
    LeverageBatchRow,
    LeverageDeclineRow,
    LeverageReadingRow,
    MachineRow,
    ParkRow,
    ProjectRow,
    RailAtOnRow,
    ReadingRow,
    RecoveryRow,
    RescueRow,
    SessionSlotRow,
    SightingRow,
    TimingRow,
    TitleReadingRow,
    TriageRow,
    TrunkRow,
    WatercoolerRow,
    WindowlessSessionRow,
    WindowRow,
    WriteStampRow,
)

_COLUMN_ORDER: dict[str, int] = {d.column.value: i for i, d in enumerate(COLUMN_DEFINITIONS)}
_MIGRATIONS = Path(__file__).parent / "migrations"
ONE_PER_CARD: frozenset[RowKind] = frozenset(
    {
        RowKind.DELIVERED,
        RowKind.WATCH,
        RowKind.REVIEW,
        RowKind.VERDICT,
        RowKind.HANDED_OUT,
        RowKind.TRIAGED,
        RowKind.SPLIT,
    }
)
"""Record rows a card carries once: writing one again replaces it, so a
close written twice never says two things about what shipped, and a card
never carries two verdicts or two handout tallies. A defect read four times
would otherwise carry four `TRIAGED` rows saying four things about who
fixes it; the rewrite keeps every previous text in the card's history, and
the readings themselves are a table (plan 59, item 3)."""
ROW_DETAIL_LENGTH = 140
_END = 1_000_000
"""A position past any group's end: the move clamps it to the last slot."""
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


_STAMP = text(
    "UPDATE writes SET seq = seq + 1, origin = :origin, at = :at WHERE id = 1 RETURNING seq"
)


class Store:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.engine = open_engine(self.path)
        migrate(self.engine)
        self.origin = str(uuid.uuid4())
        """This store's own id, stamped on every commit it makes."""
        self._own_seqs: list[int] = []
        """The stamp of every commit this store made, until the poller has counted it."""
        self._own_lock = threading.Lock()
        self._session = sessionmaker(self.engine)
        event.listen(self._session, "before_commit", self._stamp)
        event.listen(self._session, "after_commit", self._count_own)

    def close(self) -> None:
        """Release every pooled connection. A store is closed by whoever opened it."""
        self.engine.dispose()

    # ── the write stamp ────────────────────────────────────────────────
    # Every commit, from any process, bumps one counter and names its
    # writer (plan 06, item 6). The server polls the counter once a second
    # and subtracts its own commits, so a `needle row` from a lane's process
    # is on the page within a second and the server's own writes never make
    # it re-read itself: the file watcher this replaces heard its own lane
    # loop write lane records, re-read, wrote again, and bumped the page's
    # version twice a second for as long as it ran (measured 2026-09-04).

    def _stamp(self, session: Session) -> None:
        now = datetime.now(UTC).isoformat()
        seq = session.execute(_STAMP, {"origin": self.origin, "at": now}).scalar_one_or_none()
        if seq is None:
            # The row is made by the migration; a store that lost it is not a
            # store that cannot be written, so it is made again here.
            session.execute(
                text("INSERT INTO writes (id, seq, origin, at) VALUES (1, 1, :origin, :at)"),
                {"origin": self.origin, "at": now},
            )
            seq = 1
        session.info["stamp"] = int(seq)

    def _count_own(self, session: Session) -> None:
        seq = session.info.pop("stamp", None)
        if seq is not None:
            with self._own_lock:
                self._own_seqs.append(seq)

    def write_stamp(self) -> tuple[int, str]:
        """How many commits the store has taken, and who made the last one."""
        with self._session() as session:
            row = session.get(WriteStampRow, 1)
            return (row.seq, row.origin) if row is not None else (0, "")

    def own_commits_upto(self, seq: int) -> int:
        """How many of this store's own commits carry a stamp at or below
        `seq`; those are forgotten, so each is counted once."""
        with self._own_lock:
            counted = sum(1 for s in self._own_seqs if s <= seq)
            self._own_seqs = [s for s in self._own_seqs if s > seq]
        return counted

    # ── projects ───────────────────────────────────────────────────────

    def add_project(self, project: Project) -> None:
        with self._session() as session, session.begin():
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

    def note_entrance(self, slug: str, entrance: Entrance) -> None:
        """Record what a session started in this project reads as its
        constitution, as the door last read it. Overwrites: the answer that
        matters is the one true now (migration 0011)."""
        with self._session() as session, session.begin():
            row = session.get(ProjectRow, slug)
            if row is None:
                raise StoreRefusal(f'No project "{slug}" is on the board.')
            row.entrance = entrance.model_dump(mode="json")

    def projects(self) -> list[Project]:
        with self._session() as session:
            rows = session.scalars(select(ProjectRow).order_by(ProjectRow.registered_at)).all()
            return [_project(r) for r in rows]

    def project(self, slug: str) -> Project:
        with self._session() as session:
            row = session.get(ProjectRow, slug)
            if row is None:
                raise StoreRefusal(f'No project "{slug}" is on the board.')
            return _project(row)

    def has_import(self, slug: str) -> bool:
        with self._session() as session:
            row = session.get(ProjectRow, slug)
            return row is not None and row.imported_01_at is not None

    # ── reading ────────────────────────────────────────────────────────

    def layout(self, slug: str) -> list[GroupLayout]:
        with self._session() as session:
            return _layout(session, slug)

    def cards(self, slug: str) -> list[Card]:
        with self._session() as session:
            groups = {
                g.id: g
                for g in session.scalars(select(GroupRow).where(GroupRow.project_slug == slug))
            }
            rows = _rows_by_card(session, slug)
            cards = session.scalars(select(CardRow).where(CardRow.project_slug == slug)).all()
            return [_card(c, groups[c.group_id], rows.get(c.number, [])) for c in cards]

    def card(self, slug: str, number: int) -> Card | None:
        with self._session() as session:
            row = session.get(CardRow, (slug, number))
            if row is None:
                return None
            group = session.get(GroupRow, row.group_id)
            assert group is not None
            rows = _rows_by_card(session, slug, number).get(number, [])
            return _card(row, group, rows)

    def history(self, slug: str, number: int) -> list[AuditEntry]:
        with self._session() as session:
            rows = session.scalars(
                select(AuditRow)
                .where(AuditRow.project_slug == slug, AuditRow.card_number == number)
                .order_by(AuditRow.id.desc())
            ).all()
            return [_audit_entry(r) for r in rows]

    def placements(self, slug: str) -> dict[int, AuditEntry]:
        """Each card's placement: the audit row that last put it in its column
        (a move, else its birth), in one query. What a read re-tests."""
        with self._session() as session:
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

    def answers(self, slug: str) -> dict[int, AuditEntry]:
        """Each card's latest `answered` row, in one query. The owner's
        ruling on a parked defect lives here (plan 59, item 5), and the
        board asks after it on every read: one query per project, never one
        per card, because a board with six hundred cards reads four times a
        second."""
        with self._session() as session:
            rows = session.scalars(
                select(AuditRow)
                .where(
                    AuditRow.project_slug == slug,
                    AuditRow.kind == AuditKind.ANSWERED.value,
                )
                .order_by(AuditRow.id)
            )
            return {row.card_number: _audit_entry(row) for row in rows}

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
        with self._session() as session, session.begin():
            if session.get(ProjectRow, slug) is None:
                raise StoreRefusal(f'No project "{slug}" is on the board.')
            card = session.get(CardRow, (slug, number))
            if card is not None and card.folded_into is not None:
                raise StoreRefusal(
                    f"#{number} is folded into #{card.folded_into}; move that card and this "
                    "one follows."
                )
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
        with self._session() as session, session.begin():
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
                    written_at=at,
                    writer=Actor.OWNER.value,
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
        with self._session() as session, session.begin():
            project = session.get(ProjectRow, slug)
            if project is None:
                raise StoreRefusal(f'No project "{slug}" is on the board.')
            for renamed in effects.renamed:
                card = session.get(CardRow, (slug, renamed.card_number))
                assert card is not None
                card.link_stem = renamed.document.stem
                card.link_title = renamed.document.title
                into_done = renamed.document.path.startswith(
                    DOCUMENT_FOLDER[renamed.document.kind] + "/done/"
                )
                card.link_archived = into_done
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
                    f"{renamed.document.path}; {renamed.how}."
                    + (" It sits in done/ now." if into_done else "")
                    + _retitle(card, renamed.document.title),
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
                    detail=f"Linked to {relinked.document.path}, {relinked.why}."
                    + _retitle(card, relinked.document.title),
                )
                if card.folded_into is not None:
                    # A plan naming a folded card by number wants that card
                    # to carry it: the card stands on its own again.
                    was = card.folded_into
                    card.folded_into = None
                    session.flush()
                    _audit(
                        session,
                        slug,
                        card.number,
                        at=at,
                        actor=Actor.CORPUS,
                        kind=AuditKind.FOLDED_INTO,
                        from_place=None,
                        to_place=None,
                        detail=f"Unfolded from #{was}: {relinked.document.path} names this card.",
                    )
                group = session.get(GroupRow, card.group_id)
                assert group is not None
                if relinked.promote and Column(group.column) in PROMOTED_FROM:
                    _move(
                        session,
                        slug,
                        card.number,
                        Place(column=Column.PLANNED, group=None, position=_END),
                        Actor.CORPUS,
                        at,
                        detail=f"a plan appeared for it ({relinked.document.path}); a plan "
                        "appearing is what promotes a card",
                        evidence=None,
                    )
            for folded in effects.folded:
                _fold(session, slug, folded.card_number, folded.into, folded.plan, at)
            for rehomed in effects.rehomed:
                if rehomed.into_rail:
                    _landing_group(session, slug, Column.BACKLOG, rail=True)
                _move(
                    session,
                    slug,
                    rehomed.card_number,
                    Place(
                        column=Column.BACKLOG,
                        group=DEFECTS_RAIL if rehomed.into_rail else None,
                        position=_END,
                    ),
                    Actor.CORPUS,
                    at,
                    detail=f"its document says Kind: {rehomed.kind.value}; "
                    + (
                        "a defect reads on the defects rail"
                        if rehomed.into_rail
                        else "an idea reads below the rail"
                    ),
                    evidence=None,
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
            for retitled in effects.retitled:
                card = session.get(CardRow, (slug, retitled.card_number))
                assert card is not None
                said = _retitle(card, retitled.title)
                if not said:
                    continue
                _audit(
                    session,
                    slug,
                    card.number,
                    at=at,
                    actor=Actor.CORPUS,
                    kind=AuditKind.RETITLED,
                    from_place=None,
                    to_place=None,
                    detail="Its document's title changed." + said,
                )
            for birth in effects.born:
                group = _landing_group(
                    session,
                    slug,
                    birth.column,
                    rail=birth.column == Column.BACKLOG and birth.kind == SuggestionKind.DEFECT,
                )
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
                place = Place(column=birth.column, group=group.name, position=position)
                how = "at registration" if origin == CardOrigin.FOUNDING else "after registration"
                detail = f"Born from {birth.document.path}, {how}."
                if group.name == DEFECTS_RAIL:
                    detail += " Its document says Kind: defect, so it reads on the defects rail."
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
        with self._session() as session, session.begin():
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
                            written_at=at,
                            writer=Actor.IMPORT.value,
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
        with self._session() as session, session.begin():
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
                replaced.written_at = at
                replaced.writer = actor.value
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
                        written_at=at,
                        writer=actor.value,
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

    def rows_written(self, slug: str, *, since: datetime | None = None) -> list[RowRecord]:
        """Every row standing on every card of the project, with when it was
        written and by whom (plan 08, item 3), oldest first; `since` keeps
        only rows written at or after that moment. Read-only: the record a
        project's own tooling reads, never the board's page."""
        with self._session() as session:
            query = (
                select(CardRowRow, CardRow, GroupRow)
                .join(
                    CardRow,
                    (CardRow.project_slug == CardRowRow.project_slug)
                    & (CardRow.number == CardRowRow.card_number),
                )
                .join(GroupRow, GroupRow.id == CardRow.group_id)
                .where(CardRowRow.project_slug == slug)
                .order_by(CardRowRow.written_at, CardRowRow.card_number, CardRowRow.position)
            )
            if since is not None:
                query = query.where(CardRowRow.written_at >= since)
            return [
                RowRecord(
                    card=row.card_number,
                    title=card.title,
                    column=Column(group.column),
                    kind=RowKind(row.kind),
                    text=row.text,
                    at=row.written_at,
                    by=Actor(row.writer) if row.writer else None,
                )
                for row, card, group in session.execute(query).all()
            ]

    def note(
        self, slug: str, number: int, kind: AuditKind, actor: Actor, at: datetime, detail: str
    ) -> None:
        """An audit row that moves nothing: a door opened, a session ended, a
        signal read. The card's history is where the machine says what it did."""
        if not detail:
            raise StoreRefusal("A note on a card must say something.")
        with self._session() as session, session.begin():
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
        with self._session() as session, session.begin():
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
        with self._session() as session:
            query = select(HookEventRow).where(HookEventRow.project_slug == slug)
            if number is not None:
                query = query.where(HookEventRow.card_number == number)
            return [_hook_event(r) for r in session.scalars(query.order_by(HookEventRow.id))]

    def hook_events_of_session(self, session_id: str) -> list[HookEvent]:
        with self._session() as session:
            rows = session.scalars(
                select(HookEventRow)
                .where(HookEventRow.session_id == session_id)
                .order_by(HookEventRow.id)
            )
            return [_hook_event(r) for r in rows]

    def record_discussion(
        self,
        slug: str,
        number: int | None,
        session_id: str,
        slot: str,
        at: datetime,
        kind: WindowKind = WindowKind.DISCUSS,
    ) -> Discussion:
        """A conversation opened from the board; `number` is None for an idea,
        and `kind` is the door it came through."""
        with self._session() as session, session.begin():
            row = DiscussionRow(
                project_slug=slug,
                card_number=number,
                kind=kind.value,
                session_id=session_id,
                slot=slot,
                started_at=at,
            )
            session.add(row)
            session.flush()
            return _discussion(row)

    def discussions(self, slug: str) -> list[Discussion]:
        with self._session() as session:
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
        with self._session() as session, session.begin():
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

    def watercooler(
        self, slug: str, *, limit: int | None = None, after: int = 0
    ) -> list[WatercoolerLine]:
        """The project's lines, oldest first; with `limit`, the newest that
        many; with `after`, only the lines past that id — what a running
        lane has not heard (plan 10), read on every tool call."""
        with self._session() as session:
            query = select(WatercoolerRow).where(
                WatercoolerRow.project_slug == slug, WatercoolerRow.id > after
            )
            if limit is not None:
                rows = session.scalars(query.order_by(WatercoolerRow.id.desc()).limit(limit)).all()
                return [_watercooler_line(r) for r in reversed(rows)]
            return [
                _watercooler_line(r) for r in session.scalars(query.order_by(WatercoolerRow.id))
            ]

    # ── the board's record of each lane ────────────────────────────────

    def record_lane(self, record: LaneRecord) -> None:
        with self._session() as session, session.begin():
            row = session.get(LaneRow, (record.project, record.card_number))
            if row is None:
                row = LaneRow(project_slug=record.project, card_number=record.card_number)
                session.add(row)
            row.name = record.name
            row.path = record.path
            row.branch = record.branch
            row.machine = record.machine
            row.birth = record.birth
            row.tip = record.tip
            row.first_seen = record.first_seen
            row.last_seen = record.last_seen
            row.gone_at = record.gone_at
            row.folded_at = record.folded_at
            row.trunk_synced_at = record.trunk_synced_at
            row.main_synced_at = record.main_synced_at

    def lanes(self, slug: str) -> list[LaneRecord]:
        with self._session() as session:
            rows = session.scalars(
                select(LaneRow).where(LaneRow.project_slug == slug).order_by(LaneRow.card_number)
            )
            return [_lane_record(r) for r in rows]

    def lane(self, slug: str, number: int) -> LaneRecord | None:
        with self._session() as session:
            row = session.get(LaneRow, (slug, number))
            return None if row is None else _lane_record(row)

    def retire_into(self, slug: str, number: int, into: int, *, why: str, at: datetime) -> Card:
        """A card the board should never have born — its document was another
        card's, renamed before the board could follow a rename (plan 08,
        item 1: Needle's #11 into #18, omarchy's #13 into #15) — is retired
        into that card: its rows move onto the survivor (a one-per-card kind
        the survivor already carries stays in the audit line only), its
        history is re-homed under the survivor's number so the merged story
        reads in one place, the retired number keeps one line saying where it
        went (the shape 0.1's retired numbers have), and the card row is gone.
        Refused while anything but rows and history is keyed to the retired
        number — a lane, a reading, a session, a triage, a card folded under
        it — because such a card is not a duplicate the board can absorb."""
        if number == into:
            raise StoreRefusal(f"#{number} cannot be retired into itself.")
        with self._session() as session, session.begin():
            card = session.get(CardRow, (slug, number))
            survivor = session.get(CardRow, (slug, into))
            if card is None or survivor is None:
                missing = number if card is None else into
                raise StoreRefusal(f"There is no card #{missing} on this board.")
            keyed = {
                "a lane": session.get(LaneRow, (slug, number)) is not None,
                "a signal reading": _any(session, ReadingRow, slug, number),
                "a session": _any(session, WindowlessSessionRow, slug, number),
                "a triage": _any(session, TriageRow, slug, number),
                "a corpus lane": _any(session, CorpusLaneRow, slug, number),
                "a fix lane": _any(session, FixLaneRow, slug, number),
                "a card folded under it": session.scalar(
                    select(CardRow.number).where(
                        CardRow.project_slug == slug, CardRow.folded_into == number
                    )
                )
                is not None,
            }
            held = [name for name, present in keyed.items() if present]
            if held:
                raise StoreRefusal(
                    f"#{number} is not a duplicate the board can retire: it has {', '.join(held)}."
                )
            rows = session.scalars(
                select(CardRowRow)
                .where(CardRowRow.project_slug == slug, CardRowRow.card_number == number)
                .order_by(CardRowRow.position)
            ).all()
            theirs = session.scalars(
                select(CardRowRow)
                .where(CardRowRow.project_slug == slug, CardRowRow.card_number == into)
                .order_by(CardRowRow.position)
            ).all()
            position = max([r.position for r in theirs], default=-1) + 1
            kept: list[str] = []
            left: list[str] = []
            for row in rows:
                kind = RowKind(row.kind)
                if kind in ONE_PER_CARD and any(t.kind == row.kind for t in theirs):
                    left.append(f"{row.kind}: {row.text}")
                    session.delete(row)
                    continue
                row.card_number = into
                row.position = position
                position += 1
                kept.append(row.kind)
            group = session.get(GroupRow, card.group_id)
            assert group is not None
            was = Place(column=Column(group.column), group=group.name, position=card.position)
            born = card.born_at
            # The survivor stands for the retired card's document too: its
            # citations join the survivor's, so the record shows the old path
            # was this card's (tools/renames_kept.py reads exactly that).
            survivor.citations = [
                *survivor.citations,
                *[c for c in card.citations if c not in survivor.citations],
            ]
            # The retired card's lines stay under its own number and are
            # quoted here, never re-homed: `placements` reads the last MOVED
            # line per number by id, and omarchy's #13 was moved to Not now
            # after #15 reached Done, so a re-homed line would have made the
            # board say the owner placed #15 in Not now (review pass 2).
            story = session.scalars(
                select(AuditRow)
                .where(AuditRow.project_slug == slug, AuditRow.card_number == number)
                .order_by(AuditRow.id)
            ).all()
            told = " · ".join(
                f"{line.at.date().isoformat()} {line.kind}: {line.detail}" for line in story
            )
            session.delete(card)
            session.flush()
            detail = (
                f"Absorbed #{number} ({card.title!r}, born {born.date().isoformat()}, sat in "
                f"{_where(was)}): {why}"
                + (f" Its rows {', '.join(kept)} moved onto this card." if kept else "")
                + (" Not carried, this card already has one: " + "; ".join(left) if left else "")
                + f" Its history, {len(story)} lines: {told}"
            )
            _audit(
                session,
                slug,
                into,
                at=at,
                actor=Actor.SESSION,
                kind=AuditKind.RETIRED,
                from_place=None,
                to_place=None,
                detail=detail,
            )
            _audit(
                session,
                slug,
                number,
                at=at,
                actor=Actor.SESSION,
                kind=AuditKind.RETIRED,
                from_place=was,
                to_place=None,
                detail=f"Retired into #{into}: {why}",
            )
            _renumber(session, group.id)
            return _card_now(session, slug, into)

    def forget_lane(self, slug: str, number: int) -> None:
        """The card is being launched again: its lane record starts over, and
        so does its hearing — the new lane's brief carries the watercooler."""
        with self._session() as session, session.begin():
            row = session.get(LaneRow, (slug, number))
            if row is not None:
                session.delete(row)
            heard = session.get(HeardRow, (slug, number))
            if heard is not None:
                session.delete(heard)
            session.execute(
                delete(HeardNoteRow)
                .where(HeardNoteRow.project_slug == slug)
                .where(HeardNoteRow.card_number == number)
            )

    # ── what a running lane has heard ──────────────────────────────────

    def heard_mark(self, slug: str, number: int) -> HeardMark | None:
        with self._session() as session:
            row = session.get(HeardRow, (slug, number))
            return None if row is None else _heard_mark(row)

    def mark_heard(self, mark: HeardMark) -> None:
        """The lane was told: the mark moves to what it has now heard."""
        with self._session() as session, session.begin():
            row = session.get(HeardRow, (mark.project, mark.card_number))
            if row is None:
                row = HeardRow(project_slug=mark.project, card_number=mark.card_number)
                session.add(row)
            row.watercooler_id = mark.watercooler_id
            row.collision = mark.collision
            row.at = mark.at
            row.text = mark.text

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
        with self._session() as session, session.begin():
            row = ReadingRow(
                project_slug=slug,
                card_number=number,
                at=at,
                delivered=delivered,
                words=words,
                actor=actor.value,
            )
            session.add(row)
            # A session's None is a finding — it read and could not tell;
            # the machine's None is a reading that could not be made.
            said = {True: "delivered", False: "not delivered", None: "unreadable"}[delivered]
            if delivered is None and actor == Actor.SESSION:
                said = "cannot tell"
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
        with self._session() as session:
            rows = session.scalars(
                select(ReadingRow)
                .where(ReadingRow.project_slug == slug, ReadingRow.card_number == number)
                .order_by(ReadingRow.id.desc())
            )
            return [_reading(r) for r in rows]

    def last_readings(self, slug: str) -> dict[int, Reading]:
        with self._session() as session:
            rows = session.scalars(
                select(ReadingRow).where(ReadingRow.project_slug == slug).order_by(ReadingRow.id)
            )
            out: dict[int, Reading] = {}
            for row in rows:
                out[row.card_number] = _reading(row)
            return out

    def heard_notes(self, slug: str, number: int) -> dict[str, datetime]:
        """Per note on the machine's watercooler, the change the lane last
        heard or made (plan 17, item 2)."""
        with self._session() as session:
            rows = session.scalars(
                select(HeardNoteRow)
                .where(HeardNoteRow.project_slug == slug)
                .where(HeardNoteRow.card_number == number)
            )
            return {r.path: r.at for r in rows}

    def stamp_notes(self, slug: str, number: int, stamps: dict[str, datetime]) -> None:
        with self._session() as session, session.begin():
            for path, at in stamps.items():
                row = session.get(HeardNoteRow, (slug, number, path))
                if row is None:
                    session.add(
                        HeardNoteRow(project_slug=slug, card_number=number, path=path, at=at)
                    )
                else:
                    row.at = at

    # ── calls to a colleague (plan 17) ─────────────────────────────────

    def record_call(
        self,
        *,
        session_id: str,
        slot: str,
        name: str,
        note: str,
        answer: str,
        brief: str,
        caller: str,
        at: datetime,
    ) -> Call:
        with self._session() as session, session.begin():
            row = CallRow(
                session_id=session_id,
                slot=slot,
                name=name,
                note=note,
                answer=answer,
                brief=brief,
                caller=caller,
                called_at=at,
                moved=None,
                ended_at=None,
                words=None,
            )
            session.add(row)
            session.flush()
            return _call(row)

    def call(self, call_id: int) -> Call | None:
        with self._session() as session:
            row = session.get(CallRow, call_id)
            return None if row is None else _call(row)

    def calls(self, *, open_only: bool = False, since: datetime | None = None) -> list[Call]:
        """Every call, oldest first; with `open_only`, those not yet ended;
        with `since`, those made at or after it."""
        with self._session() as session:
            query = select(CallRow)
            if open_only:
                query = query.where(CallRow.ended_at.is_(None))
            if since is not None:
                query = query.where(CallRow.called_at >= since)
            return [_call(r) for r in session.scalars(query.order_by(CallRow.id))]

    def move_call(self, call_id: int, session_id: str, slot: str, words: str) -> None:
        """The colleague now runs as another session: the call follows the
        forked id and remembers the move in the runtime's words."""
        with self._session() as session, session.begin():
            row = session.get(CallRow, call_id)
            if row is not None:
                row.session_id = session_id
                row.slot = slot
                row.moved = words

    def end_call(self, call_id: int, at: datetime, words: str) -> None:
        with self._session() as session, session.begin():
            row = session.get(CallRow, call_id)
            if row is not None and row.ended_at is None:
                row.ended_at = at
                row.words = words

    # ── the windowless sessions the board starts (plans 09 and 11) ─────

    def open_windowless_session(
        self,
        slug: str,
        number: int,
        work: SessionWork,
        session_id: str,
        slot: str,
        at: datetime,
    ) -> WindowlessSession:
        """One open session per card and kind, refused here rather than
        remembered by every caller (plan 59, item 3). Both callers before
        this checked first and then opened, which is a check and an act with
        a beat in between; a second triager is exactly the duplicate the
        seat cannot have, so the invariant lives at the door of the table."""
        with self._session() as session, session.begin():
            standing = session.scalars(
                select(WindowlessSessionRow).where(
                    WindowlessSessionRow.project_slug == slug,
                    WindowlessSessionRow.card_number == number,
                    WindowlessSessionRow.work == work.value,
                    WindowlessSessionRow.ended_at.is_(None),
                )
            ).first()
            if standing is not None:
                raise StoreRefusal(
                    f"#{number} already has a {work.value} session open "
                    f"({standing.session_id[:8]}, since {standing.started_at.isoformat()})."
                )
            row = WindowlessSessionRow(
                project_slug=slug,
                card_number=number,
                work=work.value,
                session_id=session_id,
                slot=slot,
                started_at=at,
                ended_at=None,
            )
            session.add(row)
            session.flush()
            return _windowless_session(row)

    def end_windowless_session(self, windowless_id: int, at: datetime) -> None:
        with self._session() as session, session.begin():
            row = session.get(WindowlessSessionRow, windowless_id)
            if row is not None and row.ended_at is None:
                row.ended_at = at

    def move_windowless_session(self, windowless_id: int, session_id: str, slot: str) -> None:
        """The session now runs as another: a resume forks the id (verified
        live 2026-09-04), so the record follows the one that lives."""
        with self._session() as session, session.begin():
            row = session.get(WindowlessSessionRow, windowless_id)
            if row is not None:
                row.session_id = session_id
                row.slot = slot

    def windowless_sessions(
        self, slug: str, *, work: SessionWork | None = None, open_only: bool = False
    ) -> list[WindowlessSession]:
        """Every windowless session of the project, oldest first; with
        `work`, those started for that work; with `open_only`, those whose
        finding or plan has not landed and whose process the loop has not
        yet found gone."""
        with self._session() as session:
            query = select(WindowlessSessionRow).where(WindowlessSessionRow.project_slug == slug)
            if work is not None:
                query = query.where(WindowlessSessionRow.work == work.value)
            if open_only:
                query = query.where(WindowlessSessionRow.ended_at.is_(None))
            rows = session.scalars(query.order_by(WindowlessSessionRow.id))
            return [_windowless_session(r) for r in rows]

    def open_windowless_sessions(
        self, slug: str, work: SessionWork
    ) -> dict[int, WindowlessSession]:
        """The session of that work in flight on each card, by card number."""
        open_now = self.windowless_sessions(slug, work=work, open_only=True)
        return {r.card_number: r for r in open_now}

    # ── the dial (plan 11) ─────────────────────────────────────────────

    def dial(self) -> Dial:
        with self._session() as session:
            row = session.get(DialRow, 1)
            if row is None:
                return Dial(on=False, lanes=1, changed_at=None, first_on_at=None)
            return _dial(row)

    def turn_dial(self, *, on: bool, lanes: int, actor: Actor, at: datetime) -> Dial:
        """The owner turns the dial: the setting, and one row of its record.
        A turn that changes nothing writes nothing. The first turn to on
        stamps `first_on_at`, the moment the rail is measured against."""
        if lanes < 0:
            raise StoreRefusal("The dial's number of fix lanes cannot be below zero.")
        with self._session() as session, session.begin():
            row = session.get(DialRow, 1)
            if row is None:
                row = DialRow(id=1, on=False, lanes=1, changed_at=None, first_on_at=None)
                session.add(row)
            if row.on == on and row.lanes == lanes:
                return _dial(row)
            row.on = on
            row.lanes = lanes
            row.changed_at = at
            if on and row.first_on_at is None:
                row.first_on_at = at
            session.add(DialChangeRow(at=at, actor=actor.value, on=on, lanes=lanes))
            session.flush()
            return _dial(row)

    def dial_changes(self) -> list[DialChange]:
        with self._session() as session:
            rows = session.scalars(select(DialChangeRow).order_by(DialChangeRow.id))
            return [
                DialChange(id=r.id, at=r.at, actor=Actor(r.actor), on=r.on, lanes=r.lanes)
                for r in rows
            ]

    def record_rail_at_on(self, counts: list[RailCount]) -> bool:
        """The rail as it stood when the dial was first turned on, once: a
        second call writes nothing and answers False."""
        with self._session() as session, session.begin():
            if session.scalar(select(RailAtOnRow)) is not None:
                return False
            for rail in counts:
                for filer, count in rail.counts.items():
                    session.add(
                        RailAtOnRow(project_slug=rail.project, filer=filer.value, count=count)
                    )
            return True

    def rail_at_on(self) -> list[RailCount]:
        with self._session() as session:
            rows = session.scalars(select(RailAtOnRow).order_by(RailAtOnRow.id)).all()
            by_project: dict[str, dict[Filer, int]] = {}
            for row in rows:
                by_project.setdefault(row.project_slug, {})[Filer(row.filer)] = row.count
            return [
                RailCount(project=slug, counts=counts, total=sum(counts.values()))
                for slug, counts in by_project.items()
            ]

    # ── the readings that verify a mark (plan 59) ──────────────────────

    def record_triage(
        self,
        slug: str,
        number: int,
        *,
        at: datetime,
        actor: Actor,
        result: TriageResult,
        words: str,
        decision: str,
        parent: str | None,
        direction: Direction | None,
        source_ref: str | None,
        source_path: str | None,
        source_fingerprint: str | None,
        document_fingerprint: str,
        session_id: str | None,
    ) -> Triage:
        """One reading's result, kept whole. Never replaced: a card's
        readings are a history, so the audit the loop asks for can see a
        mark that was verified one way and then another."""
        with self._session() as session, session.begin():
            if session.get(CardRow, (slug, number)) is None:
                raise StoreRefusal(f"There is no card #{number} on this board.")
            row = TriageRow(
                project_slug=slug,
                card_number=number,
                at=at,
                actor=actor.value,
                result=result.value,
                words=words,
                decision=decision,
                parent=parent,
                direction=direction.value if direction is not None else None,
                source_ref=source_ref,
                source_path=source_path,
                source_fingerprint=source_fingerprint,
                document_fingerprint=document_fingerprint,
                session_id=session_id,
            )
            session.add(row)
            session.flush()
            return _triage(row)

    def triages(self, slug: str | None = None, number: int | None = None) -> list[Triage]:
        """Every reading, oldest first; of one project or one card when named."""
        with self._session() as session:
            query = select(TriageRow)
            if slug is not None:
                query = query.where(TriageRow.project_slug == slug)
            if number is not None:
                query = query.where(TriageRow.card_number == number)
            return [_triage(r) for r in session.scalars(query.order_by(TriageRow.id))]

    def triage(self, slug: str, number: int) -> Triage | None:
        """The newest reading on one card: what routing is read from when
        the board is asked about one card rather than a whole project."""
        with self._session() as session:
            row = session.scalars(
                select(TriageRow)
                .where(TriageRow.project_slug == slug, TriageRow.card_number == number)
                .order_by(TriageRow.id.desc())
            ).first()
            return _triage(row) if row is not None else None

    def latest_triages(self, slug: str) -> dict[int, Triage]:
        """The newest reading on each of the project's cards: what routing
        is read from."""
        latest: dict[int, Triage] = {}
        for triage in self.triages(slug):
            latest[triage.card_number] = triage
        return latest

    # ── the cold readings of a title (card #74, item 3) ────────────────

    def record_title_reading(
        self,
        slug: str,
        number: int,
        *,
        at: datetime,
        verdict: TitleVerdict,
        words: str,
        failed: list[str],
        title_fingerprint: str,
        session_id: str | None,
    ) -> TitleReading:
        """One reading of a card's title, kept whole and never replaced: the
        readings are a history, and a title that failed twice before it
        passed is a fact about the writer's register the loop can read."""
        with self._session() as session, session.begin():
            if session.get(CardRow, (slug, number)) is None:
                raise StoreRefusal(f"There is no card #{number} on this board.")
            row = TitleReadingRow(
                project_slug=slug,
                card_number=number,
                at=at,
                verdict=verdict.value,
                words=words,
                failed=json.dumps(failed),
                title_fingerprint=title_fingerprint,
                session_id=session_id,
            )
            session.add(row)
            session.flush()
            return _title_reading(row)

    def title_readings(self, slug: str, number: int | None = None) -> list[TitleReading]:
        """Every title reading of a project, oldest first; of one card when named."""
        with self._session() as session:
            query = select(TitleReadingRow).where(TitleReadingRow.project_slug == slug)
            if number is not None:
                query = query.where(TitleReadingRow.card_number == number)
            return [_title_reading(r) for r in session.scalars(query.order_by(TitleReadingRow.id))]

    def latest_title_readings(self, slug: str) -> dict[int, TitleReading]:
        """The newest title reading on each of the project's cards: what the
        face and the Start door read."""
        latest: dict[int, TitleReading] = {}
        for reading in self.title_readings(slug):
            latest[reading.card_number] = reading
        return latest

    # ── the short lanes that write the corpus (plan 59, items 4 and 5) ──

    def open_corpus_lane(
        self,
        slug: str,
        number: int,
        *,
        kind: CorpusLaneKind,
        decision: str,
        name: str,
        path: str | None,
        session_id: str | None,
        attempt: int,
        at: datetime,
    ) -> CorpusLane:
        with self._session() as session, session.begin():
            row = CorpusLaneRow(
                project_slug=slug,
                card_number=number,
                kind=kind.value,
                decision=decision,
                name=name,
                path=path,
                session_id=session_id,
                attempt=attempt,
                opened_at=at,
                ended_at=None,
                note=None,
            )
            session.add(row)
            session.flush()
            return _corpus_lane(row, applied=False)

    def end_corpus_lane(self, corpus_lane_id: int, at: datetime, note: str) -> None:
        with self._session() as session, session.begin():
            row = session.get(CorpusLaneRow, corpus_lane_id)
            if row is None:
                raise StoreRefusal(f"There is no corpus lane {corpus_lane_id}.")
            if row.ended_at is None:
                row.ended_at = at
            row.note = note

    def corpus_lanes(
        self, slug: str | None = None, *, decision: str | None = None, open_only: bool = False
    ) -> list[CorpusLane]:
        with self._session() as session:
            query = select(CorpusLaneRow)
            if slug is not None:
                query = query.where(CorpusLaneRow.project_slug == slug)
            if decision is not None:
                query = query.where(CorpusLaneRow.decision == decision)
            if open_only:
                query = query.where(CorpusLaneRow.ended_at.is_(None))
            rows = session.scalars(query.order_by(CorpusLaneRow.id))
            return [_corpus_lane(r, applied=False) for r in rows]

    # ── the fix lanes the dial ran (plan 11) ───────────────────────────

    def open_fix_lane(
        self, slug: str, number: int, at: datetime, *, decision: str | None = None
    ) -> FixLane:
        with self._session() as session, session.begin():
            row = FixLaneRow(
                project_slug=slug,
                card_number=number,
                stage=FixStage.PLANNING.value,
                planning_started_at=at,
                planned_at=None,
                started_at=None,
                ended_at=None,
                note=None,
                decision=decision,
            )
            session.add(row)
            session.flush()
            return _fix_lane(row)

    def stage_fix_lane(
        self, fix_lane_id: int, stage: FixStage, at: datetime, *, note: str | None = None
    ) -> FixLane:
        """Move a fix lane to its next stage, stamping the stage's own time.
        A note says why when the stage is one that ends the dial's part."""
        with self._session() as session, session.begin():
            row = session.get(FixLaneRow, fix_lane_id)
            if row is None:
                raise StoreRefusal(f"There is no fix lane {fix_lane_id}.")
            row.stage = stage.value
            if stage == FixStage.PLANNED:
                row.planned_at = at
            elif stage == FixStage.STARTED:
                row.started_at = at
            elif stage in (FixStage.FOLDED, FixStage.ASKED, FixStage.ENDED):
                row.ended_at = at
            if note is not None:
                row.note = note
            session.flush()
            return _fix_lane(row)

    def fix_lanes(self, slug: str | None = None) -> list[FixLane]:
        """Every fix lane the dial ran, oldest first; of one project when named."""
        with self._session() as session:
            query = select(FixLaneRow)
            if slug is not None:
                query = query.where(FixLaneRow.project_slug == slug)
            rows = session.scalars(query.order_by(FixLaneRow.id))
            return [_fix_lane(r) for r in rows]

    # ── the trunk ──────────────────────────────────────────────────────

    def record_trunk(self, slug: str, state: TrunkState) -> None:
        with self._session() as session, session.begin():
            row = session.get(TrunkRow, slug)
            if row is None:
                row = TrunkRow(project_slug=slug, behind=0)
                session.add(row)
            row.level = state.level
            row.behind = state.behind
            row.note = state.note
            row.read_at = state.read_at

    def trunk(self, slug: str) -> TrunkState:
        with self._session() as session:
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
        with self._session() as session, session.begin():
            row = session.get(SessionSlotRow, record.session_id)
            if row is None:
                session.add(
                    SessionSlotRow(
                        session_id=record.session_id,
                        slot=record.slot,
                        card=record.card,
                        scope=record.scope,
                        recorded_at=record.recorded_at,
                        machine=record.machine,
                    )
                )
            else:
                row.slot = record.slot
                row.card = record.card
                row.scope = record.scope
                row.recorded_at = record.recorded_at
                if record.machine:
                    row.machine = record.machine

    def session_slot(self, session_id: str) -> SessionSlot | None:
        with self._session() as session:
            row = session.get(SessionSlotRow, session_id)
            return None if row is None else _session_slot(row)

    def session_slots(self) -> list[SessionSlot]:
        with self._session() as session:
            rows = session.scalars(select(SessionSlotRow).order_by(SessionSlotRow.recorded_at))
            return [_session_slot(r) for r in rows]

    # ── machines ───────────────────────────────────────────────────────
    # The machines the board knows (card #83), registered like projects, and
    # what the loop measures on each: the least memory per day, and the
    # build timings written by hand.

    def add_machine(self, machine: Machine) -> None:
        """Register a machine; a second row under the same name or the same
        identity is refused, so one machine is never two rows."""
        with self._session() as session, session.begin():
            if session.get(MachineRow, machine.name) is not None:
                raise StoreRefusal(f'A machine named "{machine.name}" is already on the board.')
            same_id = session.scalar(
                select(MachineRow).where(MachineRow.machine_id == machine.machine_id)
            )
            if same_id is not None:
                raise StoreRefusal(
                    f"That machine is already on the board as {same_id.name!r} "
                    f"(machine id {machine.machine_id})."
                )
            session.add(
                MachineRow(
                    name=machine.name,
                    machine_id=machine.machine_id,
                    host=machine.host,
                    desktop=machine.desktop,
                    ground=machine.ground,
                    command=machine.command,
                    added_at=machine.added_at,
                )
            )

    def remove_machine(self, name: str) -> bool:
        """Forget a machine; its readings stay under its name. False when
        no such machine is on the board. Refused while a lane or a session
        record still names it: forgetting a machine with work on it would
        route that work's stops and reads to this machine (Codex's reading
        of card #83's second pass)."""
        with self._session() as session, session.begin():
            row = session.get(MachineRow, name)
            if row is None:
                return False
            lanes = session.scalar(
                select(LaneRow).where(LaneRow.machine == name, LaneRow.gone_at.is_(None))
            )
            if lanes is not None:
                raise StoreRefusal(
                    f"{name} still holds the lane of {lanes.project_slug} #{lanes.card_number}; "
                    "fold or remove it first"
                )
            # A session record is history once it is old; a recent one may
            # be a session still running there whose worktree the loop has
            # not read yet, or a reading that has no worktree at all (Codex's
            # fourth pass: a start writes its record before the lane is
            # discovered). A day is the bound: a session that ran a day ago
            # and is still alive is a lane, and the lane guard above holds.
            recent = session.scalar(
                select(SessionSlotRow)
                .where(
                    SessionSlotRow.machine == name,
                    SessionSlotRow.recorded_at >= datetime.now(UTC) - timedelta(days=1),
                )
                .order_by(SessionSlotRow.recorded_at.desc())
            )
            if recent is not None:
                raise StoreRefusal(
                    f"{name} had a session started on it in the last day "
                    f"({recent.session_id[:8]}…, {recent.card}); a machine with work on it is "
                    "not forgotten until a day has passed"
                )
            # Its clone rows go with it: a shortfall recorded for a machine
            # the board forgot is nobody's (Codex's tenth pass).
            for clone in session.scalars(select(CloneRow).where(CloneRow.machine == name)):
                session.delete(clone)
            session.delete(row)
            return True

    def lane_paths_by_machine(self) -> dict[str, str]:
        """Every lane worktree still on disk somewhere, by path, with the
        machine it was last seen on: what seeds the runtime's routing after
        a restart (card #83)."""
        with self._session() as session:
            rows = session.scalars(
                select(LaneRow).where(LaneRow.gone_at.is_(None), LaneRow.machine != "")
            )
            return {r.path: r.machine for r in rows}

    def machines(self) -> list[Machine]:
        with self._session() as session:
            rows = session.scalars(select(MachineRow).order_by(MachineRow.added_at))
            return [_machine(r) for r in rows]

    def set_machine_host(self, name: str, host: str | None) -> bool:
        """How the board reaches a machine, rewritten: the board moved, so
        the machine it used to run on is now one it reaches over ssh (card
        #83, item 3). False when no such machine is on the board."""
        with self._session() as session, session.begin():
            row = session.get(MachineRow, name)
            if row is None:
                return False
            row.host = host
            return True

    def note_high_water(self, machine: str, *, available: int, total: int, at: datetime) -> bool:
        """One reading of a machine's memory: kept when it is the day's
        lowest, else dropped. True when the mark moved. One conditional
        update, never a read-compare-write: two servers reading the same
        machine on the same day would otherwise raise the mark back
        (Codex's reading of card #83's second pass, reproduced in memory)."""
        day = at.astimezone(UTC).date().isoformat()
        for _ in range(2):
            with self._session() as session, session.begin():
                moved = session.execute(
                    text(
                        "UPDATE high_water SET least_available = :available, total = :total, "
                        "at = :at WHERE machine = :machine AND day = :day "
                        "AND least_available > :available"
                    ),
                    {
                        "available": available,
                        "total": total,
                        "at": at.astimezone(UTC).isoformat(),
                        "machine": machine,
                        "day": day,
                    },
                ).rowcount
                if moved:
                    return True
                if session.get(HighWaterRow, (machine, day)) is not None:
                    return False
            try:
                with self._session() as session, session.begin():
                    session.add(
                        HighWaterRow(
                            machine=machine, day=day, least_available=available, total=total, at=at
                        )
                    )
                return True
            except IntegrityError:
                continue  # another writer made the day's row first: compare against it
        return False

    def high_water(self, machine: str, *, since: datetime | None = None) -> HighWater | None:
        """The day on which the machine had the least memory available, over
        the days since `since` (every day when None); None with no reading."""
        with self._session() as session:
            query = select(HighWaterRow).where(HighWaterRow.machine == machine)
            if since is not None:
                query = query.where(HighWaterRow.day >= since.astimezone(UTC).date().isoformat())
            rows = list(session.scalars(query))
        if not rows:
            return None
        lowest = min(rows, key=lambda r: (r.least_available, r.day))
        return _high_water(lowest)

    def high_waters(self, machine: str) -> list[HighWater]:
        """Every day's mark for the machine, oldest first."""
        with self._session() as session:
            rows = session.scalars(
                select(HighWaterRow)
                .where(HighWaterRow.machine == machine)
                .order_by(HighWaterRow.day)
            )
            return [_high_water(r) for r in rows]

    def record_timing(self, timing: Timing) -> None:
        with self._session() as session, session.begin():
            session.add(
                TimingRow(
                    machine=timing.machine, what=timing.what, seconds=timing.seconds, at=timing.at
                )
            )

    def record_clones(self, machine: str, projects: dict[str, str | None], at: datetime) -> bool:
        """What the board found levelling one machine's clones this pass:
        per project, why the clone is not level, or None — the machine's
        whole set, so a project no longer on the board leaves no row
        behind (Codex's tenth pass). Nothing is written for a machine the
        board no longer knows: a levelling that began before the machine
        was forgotten would otherwise put its rows back (the eleventh
        pass). True when the words changed for any project."""
        changed = False
        with self._session() as session, session.begin():
            if session.get(MachineRow, machine) is None:
                return False
            for row in session.scalars(select(CloneRow).where(CloneRow.machine == machine)):
                if row.project not in projects:
                    changed = changed or row.note is not None
                    session.delete(row)
            for project, note in projects.items():
                row = session.get(CloneRow, (machine, project))
                if row is None:
                    session.add(CloneRow(machine=machine, project=project, note=note, at=at))
                    changed = changed or note is not None
                    continue
                if row.note != note:
                    changed = True
                row.note = note
                row.at = at
        return changed

    def clones(self, machine: str) -> list[str]:
        """The projects whose clone on the machine was not level at the last
        levelling, as `project: why`, for the machine's line."""
        with self._session() as session:
            rows = session.scalars(
                select(CloneRow)
                .where(CloneRow.machine == machine, CloneRow.note.is_not(None))
                .order_by(CloneRow.project)
            )
            return [f"{r.project}: {r.note}" for r in rows]

    def timings(self, machine: str | None = None) -> list[Timing]:
        """Every timing written, oldest first; one machine's when named."""
        with self._session() as session:
            query = select(TimingRow).order_by(TimingRow.at, TimingRow.id)
            if machine is not None:
                query = query.where(TimingRow.machine == machine)
            return [
                Timing(machine=r.machine, what=r.what, seconds=r.seconds, at=r.at)
                for r in session.scalars(query)
            ]

    def killed_on(self, machine: str, *, since: datetime, here: str) -> list[Death]:
        """The deaths the system's memory killer caused on a machine since
        `since` (card #83, item 5): a death whose session's slot record
        names the machine, or names none and the board's own machine is
        `here`. Read by the loop's daily count."""
        with self._session() as session:
            rows = list(
                session.scalars(
                    select(DeathRow).where(
                        DeathRow.cause.in_([Cause.LANE_KILLED.value, Cause.DAEMON_KILLED.value])
                    )
                )
            )
            ids = [d.session_id for d in rows]
            slots = {
                r.session_id: r.machine
                for r in session.scalars(
                    select(SessionSlotRow).where(SessionSlotRow.session_id.in_(ids))
                )
            }
            seen = {
                r.session_id: r.machine
                for r in session.scalars(select(SightingRow).where(SightingRow.session_id.in_(ids)))
            }
        found: list[Death] = []
        for row in rows:
            when = row.last_alive_at or row.named_at
            if when < since:
                continue
            # The sighting says where the process was seen; the slot record
            # where it was started; a record older than either is this
            # machine's.
            where = seen.get(row.session_id) or slots.get(row.session_id) or here
            if where == machine:
                found.append(_death(row))
        return found

    def record_rescue(
        self, session_id: str, from_rung: Rung | None, to_rung: Rung, reason: str, at: datetime
    ) -> Rescue:
        with self._session() as session, session.begin():
            row = RescueRow(
                session_id=session_id,
                from_slot=from_rung.slot if from_rung else None,
                from_model=from_rung.model if from_rung else None,
                to_slot=to_rung.slot,
                to_model=to_rung.model,
                reason=reason,
                at=at,
            )
            session.add(row)
            session.flush()
            return _rescue(row)

    def rescues(self, session_id: str) -> list[Rescue]:
        with self._session() as session:
            rows = session.scalars(
                select(RescueRow).where(RescueRow.session_id == session_id).order_by(RescueRow.id)
            )
            return [_rescue(r) for r in rows]

    def clear_rescues(self, session_id: str) -> int:
        """Forget a session's rescue history. Its slot record is untouched."""
        with self._session() as session, session.begin():
            result = session.execute(delete(RescueRow).where(RescueRow.session_id == session_id))
            return int(result.rowcount or 0)

    # ── how a lane's session ended, and what the board does about it (plan 68) ──

    def record_sighting(self, sighting: Sighting) -> None:
        """A session seen alive in a lane, on this pass. Written once per
        life and refreshed in place: the first sighting keeps its time, the
        last moves with every read, and the space and boot follow the read."""
        with self._session() as session, session.begin():
            row = session.get(SightingRow, sighting.session_id)
            if row is None:
                session.add(
                    SightingRow(
                        session_id=sighting.session_id,
                        project_slug=sighting.project,
                        card_number=sighting.card_number,
                        pid=sighting.pid,
                        scope=sighting.scope,
                        boot_id=sighting.boot_id,
                        first_seen=sighting.first_seen,
                        last_seen=sighting.last_seen,
                        released_at=sighting.released_at,
                        scoped_at=sighting.scoped_at,
                        machine=sighting.machine,
                    )
                )
                return
            if row.pid != sighting.pid or row.boot_id != sighting.boot_id:
                # A different process under the same id is a new life: the
                # once-per-life acts and the first sighting start again.
                row.first_seen = sighting.first_seen
                row.released_at = None
                row.scoped_at = None
            row.pid = sighting.pid
            row.scope = sighting.scope
            row.boot_id = sighting.boot_id
            row.last_seen = sighting.last_seen
            if sighting.machine:
                row.machine = sighting.machine
            if sighting.released_at is not None:
                row.released_at = sighting.released_at
            if sighting.scoped_at is not None:
                row.scoped_at = sighting.scoped_at

    def forget_death(self, session_id: str) -> None:
        """A session seen alive again has no death: the row a previous
        life earned is removed, so a new life is named on its own."""
        with self._session() as session, session.begin():
            session.execute(delete(DeathRow).where(DeathRow.session_id == session_id))

    def sighting(self, session_id: str) -> Sighting | None:
        with self._session() as session:
            row = session.get(SightingRow, session_id)
            return None if row is None else _sighting(row)

    def sightings(self, slug: str) -> dict[str, Sighting]:
        """Every session this project's lanes were seen alive with, by id."""
        with self._session() as session:
            rows = session.scalars(select(SightingRow).where(SightingRow.project_slug == slug))
            return {r.session_id: _sighting(r) for r in rows}

    def record_death(self, death: Death) -> None:
        """Why a session's process is gone; rewritten in place while the
        cause was not settled, so a later read that names it revises the
        epitaph the first read wrote."""
        with self._session() as session, session.begin():
            row = session.get(DeathRow, death.session_id)
            if row is None:
                session.add(
                    DeathRow(
                        session_id=death.session_id,
                        project_slug=death.project,
                        card_number=death.card_number,
                        cause=death.cause.value,
                        words=death.words,
                        evidence=death.evidence,
                        last_alive_at=death.last_alive_at,
                        named_at=death.named_at,
                        settled=death.settled,
                    )
                )
                return
            row.cause = death.cause.value
            row.words = death.words
            row.evidence = death.evidence
            row.last_alive_at = death.last_alive_at
            row.named_at = death.named_at
            row.settled = death.settled

    def deaths(self, slug: str) -> dict[str, Death]:
        with self._session() as session:
            rows = session.scalars(select(DeathRow).where(DeathRow.project_slug == slug))
            return {r.session_id: _death(r) for r in rows}

    def open_park(
        self,
        slug: str,
        number: int,
        *,
        session_id: str,
        cause: Cause,
        words: str,
        waits_on: str,
        until: datetime | None,
        held_since: datetime | None,
        at: datetime,
    ) -> Park:
        """A park on a card's lane. Refused while one stands: the refusal is
        what makes the park note land once across a restart of the server
        and across a `needle` command that builds its own loop."""
        with self._session() as session, session.begin():
            row = ParkRow(
                project_slug=slug,
                card_number=number,
                session_id=session_id,
                cause=cause.value,
                words=words,
                waits_on=waits_on,
                until=until,
                held_since=held_since,
                started_at=at,
                lifted_at=None,
                lifted_words=None,
            )
            session.add(row)
            try:
                session.flush()
            except IntegrityError as clash:
                raise StoreRefusal(f"A park already stands on #{number}.") from clash
            return _park(row)

    def hold_park(self, park_id: int, held_since: datetime | None) -> Park:
        """When a memory park's floor was first read satisfied; None when the
        floor stopped holding and the wait starts over."""
        with self._session() as session, session.begin():
            row = session.get(ParkRow, park_id)
            if row is None:
                raise StoreRefusal(f"There is no park {park_id}.")
            row.held_since = held_since
            session.flush()
            return _park(row)

    def lift_park(self, park_id: int, at: datetime, words: str) -> Park:
        with self._session() as session, session.begin():
            row = session.get(ParkRow, park_id)
            if row is None:
                raise StoreRefusal(f"There is no park {park_id}.")
            row.lifted_at = at
            row.lifted_words = words
            session.flush()
            return _park(row)

    def parks(self, slug: str, *, standing_only: bool = False) -> list[Park]:
        with self._session() as session:
            query = select(ParkRow).where(ParkRow.project_slug == slug)
            if standing_only:
                query = query.where(ParkRow.lifted_at.is_(None))
            rows = session.scalars(query.order_by(ParkRow.id))
            return [_park(r) for r in rows]

    def open_recovery(
        self,
        slug: str,
        number: int,
        *,
        session_id: str,
        cause: Cause,
        words: str,
        at: datetime,
        horizon_seconds: float | None = None,
    ) -> Recovery:
        """The row a launch is preceded by. Refused while one is open on the
        card: two processes, or one process twice across a restart, cannot
        both launch a replacement for one interruption. With a horizon, also
        refused while an attempt for the same cause started inside it — the
        one durable claim on the once-per-cause rule, so a reader that
        counted before another's attempt landed cannot launch a second."""
        with self._session() as session, session.begin():
            if horizon_seconds is not None:
                floor = at - timedelta(seconds=horizon_seconds)
                taken = session.scalars(
                    select(RecoveryRow).where(
                        RecoveryRow.project_slug == slug,
                        RecoveryRow.card_number == number,
                        RecoveryRow.cause == cause.value,
                        RecoveryRow.started_at > floor,
                    )
                ).first()
                if taken is not None:
                    raise StoreRefusal(
                        f"An attempt for this cause on #{number} started inside the horizon."
                    )
            row = RecoveryRow(
                project_slug=slug,
                card_number=number,
                session_id=session_id,
                cause=cause.value,
                words=words,
                started_at=at,
                replacement=None,
                verdict=None,
                ended_at=None,
                note=None,
            )
            session.add(row)
            try:
                session.flush()
            except IntegrityError as clash:
                raise StoreRefusal(f"A recovery is already open on #{number}.") from clash
            return _recovery(row)

    def close_recovery(
        self,
        recovery_id: int,
        *,
        verdict: str,
        replacement: str | None,
        at: datetime,
        note: str | None,
    ) -> Recovery:
        with self._session() as session, session.begin():
            row = session.get(RecoveryRow, recovery_id)
            if row is None:
                raise StoreRefusal(f"There is no recovery {recovery_id}.")
            row.verdict = verdict
            row.replacement = replacement
            row.ended_at = at
            row.note = note
            session.flush()
            return _recovery(row)

    def recoveries(self, slug: str, number: int | None = None) -> list[Recovery]:
        with self._session() as session:
            query = select(RecoveryRow).where(RecoveryRow.project_slug == slug)
            if number is not None:
                query = query.where(RecoveryRow.card_number == number)
            rows = session.scalars(query.order_by(RecoveryRow.id))
            return [_recovery(r) for r in rows]

    def record_window(
        self, session_id: str, kind: WindowKind, app_id: str, address: str, at: datetime
    ) -> Window:
        with self._session() as session, session.begin():
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
        with self._session() as session:
            query = select(WindowRow).order_by(WindowRow.id)
            if session_id is not None:
                query = query.where(WindowRow.session_id == session_id)
            if open_only:
                query = query.where(WindowRow.closed_at.is_(None))
            return [_window(r) for r in session.scalars(query)]

    def window_closed(self, window_id: int, at: datetime) -> None:
        """The runtime found the window gone. It records the close; it never causes one."""
        with self._session() as session, session.begin():
            row = session.get(WindowRow, window_id)
            if row is not None and row.closed_at is None:
                row.closed_at = at

    # ── a project's focus, and every card against it (card #87) ───────

    def record_focus_ruling(
        self, slug: str, *, fingerprint: str, what_matters: str, at: datetime
    ) -> FocusRuling:
        """The owner's click: use this document, at this fingerprint. Never
        replaced — a history, like the dial's turns — and the newest stands."""
        with self._session() as session, session.begin():
            if session.get(ProjectRow, slug) is None:
                raise StoreRefusal(f'No project "{slug}" is on the board.')
            row = FocusRulingRow(
                project_slug=slug, fingerprint=fingerprint, what_matters=what_matters, chosen_at=at
            )
            session.add(row)
            session.flush()
            return _focus_ruling(row)

    def focus_ruling(self, slug: str) -> FocusRuling | None:
        with self._session() as session:
            row = session.scalars(
                select(FocusRulingRow)
                .where(FocusRulingRow.project_slug == slug)
                .order_by(FocusRulingRow.id.desc())
            ).first()
            return _focus_ruling(row) if row is not None else None

    def focus_rulings(self, slug: str) -> list[FocusRuling]:
        with self._session() as session:
            rows = session.scalars(
                select(FocusRulingRow)
                .where(FocusRulingRow.project_slug == slug)
                .order_by(FocusRulingRow.id)
            )
            return [_focus_ruling(r) for r in rows]

    def record_focus_check(
        self,
        slug: str,
        *,
        fingerprint: str,
        at: datetime,
        verdict: FocusVerdict,
        line: str,
        how_known: HowKnown | None,
        session_id: str | None,
    ) -> FocusCheck:
        with self._session() as session, session.begin():
            row = FocusCheckRow(
                project_slug=slug,
                fingerprint=fingerprint,
                at=at,
                verdict=verdict.value,
                line=line,
                how_known=how_known.value if how_known is not None else None,
                session_id=session_id,
            )
            session.add(row)
            session.flush()
            return _focus_check(row)

    def focus_checks(self, slug: str) -> list[FocusCheck]:
        with self._session() as session:
            rows = session.scalars(
                select(FocusCheckRow)
                .where(FocusCheckRow.project_slug == slug)
                .order_by(FocusCheckRow.id)
            )
            return [_focus_check(r) for r in rows]

    def focus_check(self, slug: str, fingerprint: str) -> FocusCheck | None:
        """The newest reading of this document, by its fingerprint: a
        re-edited document has none until it is read again."""
        with self._session() as session:
            row = session.scalars(
                select(FocusCheckRow)
                .where(FocusCheckRow.project_slug == slug, FocusCheckRow.fingerprint == fingerprint)
                .order_by(FocusCheckRow.id.desc())
            ).first()
            return _focus_check(row) if row is not None else None

    def record_focus_recheck(
        self,
        slug: str,
        *,
        fingerprint: str,
        at: datetime,
        outcome: RecheckOutcome,
        words: str,
        session_id: str | None,
    ) -> FocusRecheck:
        with self._session() as session, session.begin():
            row = FocusRecheckRow(
                project_slug=slug,
                fingerprint=fingerprint,
                at=at,
                outcome=outcome.value,
                words=words,
                session_id=session_id,
            )
            session.add(row)
            session.flush()
            return _focus_recheck(row)

    def focus_recheck(self, slug: str) -> FocusRecheck | None:
        """The newest recheck on the project, whatever document it read;
        the reader matches the fingerprint."""
        with self._session() as session:
            row = session.scalars(
                select(FocusRecheckRow)
                .where(FocusRecheckRow.project_slug == slug)
                .order_by(FocusRecheckRow.id.desc())
            ).first()
            return _focus_recheck(row) if row is not None else None

    def focus_rechecks(self, slug: str) -> list[FocusRecheck]:
        with self._session() as session:
            rows = session.scalars(
                select(FocusRecheckRow)
                .where(FocusRecheckRow.project_slug == slug)
                .order_by(FocusRecheckRow.id)
            )
            return [_focus_recheck(r) for r in rows]

    def record_measure_reading(
        self,
        slug: str,
        *,
        fingerprint: str,
        side: MeasureSide,
        at: datetime,
        delivered: bool | None,
        words: str,
    ) -> MeasureReading:
        """One reading of one measure; the first on this document and side
        is the baseline every later one is read against."""
        with self._session() as session, session.begin():
            first = (
                session.scalar(
                    select(FocusMeasureRow.id).where(
                        FocusMeasureRow.project_slug == slug,
                        FocusMeasureRow.fingerprint == fingerprint,
                        FocusMeasureRow.side == side.value,
                    )
                )
                is None
            )
            row = FocusMeasureRow(
                project_slug=slug,
                fingerprint=fingerprint,
                side=side.value,
                at=at,
                delivered=delivered,
                words=words,
                baseline=first,
            )
            session.add(row)
            session.flush()
            return _measure_reading(row)

    def measure_readings(self, slug: str, fingerprint: str) -> list[MeasureReading]:
        with self._session() as session:
            rows = session.scalars(
                select(FocusMeasureRow)
                .where(
                    FocusMeasureRow.project_slug == slug,
                    FocusMeasureRow.fingerprint == fingerprint,
                )
                .order_by(FocusMeasureRow.id)
            )
            return [_measure_reading(r) for r in rows]

    def open_focus_call(
        self,
        slug: str,
        *,
        kind: ReadingKind,
        card_number: int | None,
        fingerprint: str,
        document_fingerprint: str | None,
        call_id: int | None,
        session_id: str | None,
        at: datetime,
        ended: str | None = None,
    ) -> FocusCall:
        """A call the loop made, open until its answer lands or it dies;
        `ended` records a call that never came alive as ended at once."""
        with self._session() as session, session.begin():
            row = FocusCallRow(
                project_slug=slug,
                kind=kind.value,
                card_number=card_number,
                fingerprint=fingerprint,
                document_fingerprint=document_fingerprint,
                call_id=call_id,
                session_id=session_id,
                opened_at=at,
                ended_at=at if ended is not None else None,
                landed=False,
                note=ended,
            )
            session.add(row)
            session.flush()
            return _focus_call(row)

    def end_focus_call(
        self, focus_call_id: int, at: datetime, *, landed: bool, note: str | None
    ) -> None:
        with self._session() as session, session.begin():
            row = session.get(FocusCallRow, focus_call_id)
            if row is not None and row.ended_at is None:
                row.ended_at = at
                row.landed = landed
                row.note = note

    def focus_calls(
        self, slug: str, *, kind: ReadingKind | None = None, open_only: bool = False
    ) -> list[FocusCall]:
        with self._session() as session:
            query = select(FocusCallRow).where(FocusCallRow.project_slug == slug)
            if kind is not None:
                query = query.where(FocusCallRow.kind == kind.value)
            if open_only:
                query = query.where(FocusCallRow.ended_at.is_(None))
            return [_focus_call(r) for r in session.scalars(query.order_by(FocusCallRow.id))]

    def record_leverage_reading(
        self,
        slug: str,
        number: int,
        *,
        at: datetime,
        leverage: Leverage,
        likelihood: Likelihood | None,
        words: str,
        focus_fingerprint: str,
        document_fingerprint: str,
        session_id: str | None,
    ) -> LeverageReading:
        """One reading of one card against the focus, kept whole and never
        replaced."""
        with self._session() as session, session.begin():
            if session.get(CardRow, (slug, number)) is None:
                raise StoreRefusal(f"There is no card #{number} on this board.")
            row = LeverageReadingRow(
                project_slug=slug,
                card_number=number,
                at=at,
                leverage=leverage.value,
                likelihood=likelihood.value if likelihood is not None else None,
                words=words,
                focus_fingerprint=focus_fingerprint,
                document_fingerprint=document_fingerprint,
                session_id=session_id,
            )
            session.add(row)
            session.flush()
            return _leverage_reading(row)

    def leverage_readings(self, slug: str, number: int | None = None) -> list[LeverageReading]:
        with self._session() as session:
            query = select(LeverageReadingRow).where(LeverageReadingRow.project_slug == slug)
            if number is not None:
                query = query.where(LeverageReadingRow.card_number == number)
            return [
                _leverage_reading(r) for r in session.scalars(query.order_by(LeverageReadingRow.id))
            ]

    def latest_leverage_readings(self, slug: str) -> dict[int, LeverageReading]:
        """The newest reading on each card: what the lens reads."""
        latest: dict[int, LeverageReading] = {}
        for reading in self.leverage_readings(slug):
            latest[reading.card_number] = reading
        return latest

    def record_acceptance(
        self,
        slug: str,
        *,
        at: datetime,
        focus_fingerprint: str,
        moves: list[AcceptedMove],
        note: str | None,
    ) -> Acceptance:
        with self._session() as session, session.begin():
            row = LeverageBatchRow(
                project_slug=slug,
                at=at,
                focus_fingerprint=focus_fingerprint,
                moves=[m.model_dump(mode="json") for m in moves],
                put_back_at=None,
                note=note,
            )
            session.add(row)
            session.flush()
            return _acceptance(row)

    def note_acceptance(self, acceptance_id: int, note: str | None) -> None:
        with self._session() as session, session.begin():
            row = session.get(LeverageBatchRow, acceptance_id)
            if row is not None:
                row.note = note

    def put_back_acceptance(self, acceptance_id: int, at: datetime) -> None:
        with self._session() as session, session.begin():
            row = session.get(LeverageBatchRow, acceptance_id)
            if row is not None and row.put_back_at is None:
                row.put_back_at = at

    def acceptances(self, slug: str) -> list[Acceptance]:
        with self._session() as session:
            rows = session.scalars(
                select(LeverageBatchRow)
                .where(LeverageBatchRow.project_slug == slug)
                .order_by(LeverageBatchRow.id)
            )
            return [_acceptance(r) for r in rows]

    def latest_acceptance(self, slug: str) -> Acceptance | None:
        with self._session() as session:
            row = session.scalars(
                select(LeverageBatchRow)
                .where(LeverageBatchRow.project_slug == slug)
                .order_by(LeverageBatchRow.id.desc())
            ).first()
            return _acceptance(row) if row is not None else None

    def record_decline(
        self,
        slug: str,
        number: int,
        *,
        focus_fingerprint: str,
        document_fingerprint: str,
        leverage: Leverage,
        at: datetime,
    ) -> Decline:
        with self._session() as session, session.begin():
            row = LeverageDeclineRow(
                project_slug=slug,
                card_number=number,
                focus_fingerprint=focus_fingerprint,
                document_fingerprint=document_fingerprint,
                leverage=leverage.value,
                at=at,
            )
            session.add(row)
            session.flush()
            return _decline(row)

    def declines(self, slug: str) -> list[Decline]:
        with self._session() as session:
            rows = session.scalars(
                select(LeverageDeclineRow)
                .where(LeverageDeclineRow.project_slug == slug)
                .order_by(LeverageDeclineRow.id)
            )
            return [_decline(r) for r in rows]

    def owner_moves_since(self, slug: str, since: datetime) -> list[AuditEntry]:
        """Every move the owner made on the project after `since`: how the
        board knows a hand move retired an acceptance's put-back."""
        with self._session() as session:
            rows = session.scalars(
                select(AuditRow)
                .where(
                    AuditRow.project_slug == slug,
                    AuditRow.kind == AuditKind.MOVED.value,
                    AuditRow.actor == Actor.OWNER.value,
                    AuditRow.at > since,
                )
                .order_by(AuditRow.id)
            )
            return [_audit_entry(r) for r in rows]


# ── helpers ────────────────────────────────────────────────────────────


def _session_slot(row: SessionSlotRow) -> SessionSlot:
    return SessionSlot(
        session_id=row.session_id,
        slot=row.slot,
        card=row.card,
        scope=row.scope,
        recorded_at=row.recorded_at,
        machine=row.machine or "",
    )


def _machine(row: MachineRow) -> Machine:
    return Machine(
        name=row.name,
        machine_id=row.machine_id,
        host=row.host,
        desktop=row.desktop,
        ground=row.ground,
        command=row.command,
        added_at=row.added_at,
    )


def _high_water(row: HighWaterRow) -> HighWater:
    return HighWater(
        machine=row.machine,
        day=date.fromisoformat(row.day),
        least_available=row.least_available,
        total=row.total,
        at=row.at,
    )


def _rescue(row: RescueRow) -> Rescue:
    return Rescue(
        id=row.id,
        session_id=row.session_id,
        from_rung=(
            Rung(slot=row.from_slot, model=row.from_model or None) if row.from_slot else None
        ),
        to_rung=Rung(slot=row.to_slot, model=row.to_model or None),
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
        kind=WindowKind(row.kind),
        session_id=row.session_id,
        slot=row.slot,
        started_at=row.started_at,
    )


def _heard_mark(row: HeardRow) -> HeardMark:
    return HeardMark(
        project=row.project_slug,
        card_number=row.card_number,
        watercooler_id=row.watercooler_id,
        collision=row.collision,
        at=row.at,
        text=row.text,
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
        machine=row.machine or "",
    )


def _reading(row: ReadingRow) -> Reading:
    return Reading(
        id=row.id,
        card_number=row.card_number,
        at=row.at,
        delivered=row.delivered,
        words=row.words,
        actor=Actor(row.actor),
    )


def _call(row: CallRow) -> Call:
    return Call(
        id=row.id,
        session_id=row.session_id,
        slot=row.slot,
        name=row.name,
        note=row.note,
        answer=row.answer,
        brief=row.brief,
        caller=row.caller,
        called_at=row.called_at,
        moved=row.moved,
        ended_at=row.ended_at,
        words=row.words,
    )


def _windowless_session(row: WindowlessSessionRow) -> WindowlessSession:
    return WindowlessSession(
        id=row.id,
        project=row.project_slug,
        card_number=row.card_number,
        work=SessionWork(row.work),
        session_id=row.session_id,
        slot=row.slot,
        started_at=row.started_at,
        ended_at=row.ended_at,
    )


def _dial(row: DialRow) -> Dial:
    return Dial(on=row.on, lanes=row.lanes, changed_at=row.changed_at, first_on_at=row.first_on_at)


def _fix_lane(row: FixLaneRow) -> FixLane:
    return FixLane(
        id=row.id,
        project=row.project_slug,
        card_number=row.card_number,
        stage=FixStage(row.stage),
        planning_started_at=row.planning_started_at,
        planned_at=row.planned_at,
        started_at=row.started_at,
        ended_at=row.ended_at,
        note=row.note,
        decision=row.decision,
    )


def _triage(row: TriageRow) -> Triage:
    return Triage(
        id=row.id,
        project=row.project_slug,
        card_number=row.card_number,
        at=row.at,
        actor=Actor(row.actor),
        result=TriageResult(row.result),
        words=row.words,
        decision=row.decision,
        parent=row.parent,
        direction=Direction(row.direction) if row.direction is not None else None,
        source_ref=row.source_ref,
        source_path=row.source_path,
        source_fingerprint=row.source_fingerprint,
        document_fingerprint=row.document_fingerprint,
        session_id=row.session_id,
    )


def _title_reading(row: TitleReadingRow) -> TitleReading:
    return TitleReading(
        id=row.id,
        project=row.project_slug,
        card_number=row.card_number,
        at=row.at,
        verdict=TitleVerdict(row.verdict),
        words=row.words,
        failed=list(json.loads(row.failed)),
        title_fingerprint=row.title_fingerprint,
        session_id=row.session_id,
    )


def _corpus_lane(row: CorpusLaneRow, *, applied: bool) -> CorpusLane:
    return CorpusLane(
        id=row.id,
        project=row.project_slug,
        card_number=row.card_number,
        kind=CorpusLaneKind(row.kind),
        decision=row.decision,
        name=row.name,
        path=row.path,
        session_id=row.session_id,
        attempt=row.attempt,
        opened_at=row.opened_at,
        ended_at=row.ended_at,
        note=row.note,
        applied=applied,
    )


def _project(row: ProjectRow) -> Project:
    return Project(
        slug=row.slug,
        name=row.name,
        path=row.path,
        registered_at=row.registered_at,
        entrance=Entrance.model_validate(row.entrance) if row.entrance is not None else None,
    )


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
        folded_into=row.folded_into,
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


def _retitle(card: CardRow, title: str) -> str:
    """The face follows the document (plan 08, item 1): a card born from the
    corpus takes its document's title, and the history keeps the one it
    read. Returns the sentence for the audit row, empty when nothing
    changed. A card imported from 0.1 keeps its own title: that title was
    the owner's words for the card, which no document ever held (74 of
    Hello Revenue's 132 imported cards differ from their plan's title, and
    the plans are the older, mechanism-named ones)."""
    if card.origin == CardOrigin.IMPORTED.value or card.title == title:
        return ""
    was = card.title
    card.title = title
    return f' Its face now reads "{title}"; it read "{was}".'


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
    elif to.column == Column.BACKLOG and to.group == DEFECTS_RAIL:
        # A defect pulled back from Not now lands on the rail, which a
        # Backlog with no other defect may not have yet (card #87, item 5).
        _landing_group(session, slug, to.column, rail=True)
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
        session.flush()
        _follow(session, slug, number, at, actor, evidence)
    return result


def _follow(
    session: Session,
    slug: str,
    number: int,
    at: datetime,
    actor: Actor,
    evidence: Evidence | None,
) -> None:
    """The cards folded under a card go where it goes, by the same hand and on
    the same evidence: their work is its plan's (plan 06, item 5)."""
    leader = session.get(CardRow, (slug, number))
    assert leader is not None
    group = session.get(GroupRow, leader.group_id)
    assert group is not None
    to = Place(column=Column(group.column), group=group.name, position=leader.position)
    followers = session.scalars(
        select(CardRow).where(CardRow.project_slug == slug, CardRow.folded_into == number)
    ).all()
    for follower in followers:
        was_group = session.get(GroupRow, follower.group_id)
        assert was_group is not None
        was = Place(
            column=Column(was_group.column), group=was_group.name, position=follower.position
        )
        if was.column == to.column and was.group == to.group:
            follower.position = leader.position
            continue
        follower.group_id = leader.group_id
        follower.position = leader.position
        _audit(
            session,
            slug,
            follower.number,
            at=at,
            actor=actor,
            kind=AuditKind.MOVED,
            from_place=was,
            to_place=to,
            detail=f"{_describe_move(was, to)} — followed #{number}, into which it is folded",
            evidence=evidence,
        )


def _fold(
    session: Session, slug: str, number: int, into: int, plan: DocumentRef, at: datetime
) -> None:
    """Fold a card under the card whose plan carries its suggestion: it leaves
    its group, sits with that card and follows it from here."""
    card = session.get(CardRow, (slug, number))
    leader = session.get(CardRow, (slug, into))
    assert card is not None and leader is not None
    was_group = session.get(GroupRow, card.group_id)
    to_group = session.get(GroupRow, leader.group_id)
    assert was_group is not None and to_group is not None
    was = Place(column=Column(was_group.column), group=was_group.name, position=card.position)
    to = Place(column=Column(to_group.column), group=to_group.name, position=leader.position)
    card.folded_into = into
    card.group_id = leader.group_id
    card.position = leader.position
    session.flush()
    layout = _layout(session, slug)
    old = next((g for g in layout if g.column == was.column and g.name == was.group), None)
    if old is not None:
        _write_positions(session, slug, old)
    _audit(
        session,
        slug,
        number,
        at=at,
        actor=Actor.CORPUS,
        kind=AuditKind.FOLDED_INTO,
        from_place=was,
        to_place=to,
        detail=f"Folded into #{into}: its suggestion is carried by {plan.path}, whose card "
        f"that is; it follows #{into} and closes with it.",
    )


def _layout(session: Session, slug: str) -> list[GroupLayout]:
    """The columns' groups and the cards that stand in them, in position
    order. A folded card is not in the layout: it sits under its leader and
    takes no position of its own, so a move cannot land between it and the
    cards the page shows."""
    groups = session.scalars(select(GroupRow).where(GroupRow.project_slug == slug)).all()
    groups = sorted(groups, key=lambda g: (_COLUMN_ORDER[g.column], g.position))
    cards = session.scalars(
        select(CardRow)
        .where(CardRow.project_slug == slug, CardRow.folded_into.is_(None))
        .order_by(CardRow.position)
    ).all()
    numbers: dict[int, list[int]] = {g.id: [] for g in groups}
    for card in cards:
        numbers[card.group_id].append(card.number)
    return [
        GroupLayout(column=Column(g.column), name=g.name, numbers=numbers[g.id]) for g in groups
    ]


def _landing_group(session: Session, slug: str, column: Column, *, rail: bool = False) -> GroupRow:
    """The column's unnamed group, made at the column's end when it has none;
    with `rail`, Backlog's defects rail, made before every named group when
    it has none (plan 06, item 2).

    A card born from the corpus, or moved to a column without naming a group,
    lands here: below the owner's named groups, never above them — except a
    defect, which reads on the rail above them.
    """
    name = DEFECTS_RAIL if rail else None
    existing = session.scalar(
        select(GroupRow).where(
            GroupRow.project_slug == slug,
            GroupRow.column == column.value,
            GroupRow.name.is_(None) if name is None else GroupRow.name == name,
        )
    )
    if existing is not None:
        return existing
    siblings = session.scalars(
        select(GroupRow).where(GroupRow.project_slug == slug, GroupRow.column == column.value)
    ).all()
    position = (
        DEFECTS_RAIL_POSITION if rail else max([g.position for g in siblings], default=-1) + 1
    )
    group = GroupRow(project_slug=slug, column=column.value, name=name, position=position)
    session.add(group)
    session.flush()
    return group


def _any(session: Session, table: type, slug: str, number: int) -> bool:
    """Whether the table holds any row keyed to the card."""
    return (
        session.scalar(
            select(table.id).where(table.project_slug == slug, table.card_number == number)
        )
        is not None
    )


def _renumber(session: Session, group_id: int) -> None:
    """Close the gap a card leaving the group left in its positions."""
    cards = session.scalars(
        select(CardRow).where(CardRow.group_id == group_id).order_by(CardRow.position)
    ).all()
    for position, card in enumerate(cards):
        card.position = position


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


def _sighting(row: SightingRow) -> Sighting:
    return Sighting(
        session_id=row.session_id,
        project=row.project_slug,
        card_number=row.card_number,
        pid=row.pid,
        scope=row.scope,
        boot_id=row.boot_id,
        first_seen=row.first_seen,
        last_seen=row.last_seen,
        released_at=row.released_at,
        scoped_at=row.scoped_at,
        machine=row.machine or "",
    )


def _death(row: DeathRow) -> Death:
    return Death(
        session_id=row.session_id,
        project=row.project_slug,
        card_number=row.card_number,
        cause=Cause(row.cause),
        words=row.words,
        evidence=row.evidence,
        last_alive_at=row.last_alive_at,
        named_at=row.named_at,
        settled=row.settled,
    )


def _park(row: ParkRow) -> Park:
    return Park(
        id=row.id,
        project=row.project_slug,
        card_number=row.card_number,
        session_id=row.session_id,
        cause=Cause(row.cause),
        words=row.words,
        waits_on=row.waits_on,
        until=row.until,
        held_since=row.held_since,
        started_at=row.started_at,
        lifted_at=row.lifted_at,
        lifted_words=row.lifted_words,
    )


def _recovery(row: RecoveryRow) -> Recovery:
    return Recovery(
        id=row.id,
        project=row.project_slug,
        card_number=row.card_number,
        session_id=row.session_id,
        cause=Cause(row.cause),
        words=row.words,
        started_at=row.started_at,
        replacement=row.replacement,
        verdict=row.verdict,
        ended_at=row.ended_at,
        note=row.note,
    )


def _focus_ruling(row: FocusRulingRow) -> FocusRuling:
    return FocusRuling(
        id=row.id,
        project=row.project_slug,
        fingerprint=row.fingerprint,
        what_matters=row.what_matters,
        chosen_at=row.chosen_at,
    )


def _focus_check(row: FocusCheckRow) -> FocusCheck:
    return FocusCheck(
        id=row.id,
        project=row.project_slug,
        fingerprint=row.fingerprint,
        at=row.at,
        verdict=FocusVerdict(row.verdict),
        line=row.line,
        how_known=HowKnown(row.how_known) if row.how_known else None,
        session_id=row.session_id,
    )


def _focus_recheck(row: FocusRecheckRow) -> FocusRecheck:
    return FocusRecheck(
        id=row.id,
        project=row.project_slug,
        fingerprint=row.fingerprint,
        at=row.at,
        outcome=RecheckOutcome(row.outcome),
        words=row.words,
        session_id=row.session_id,
    )


def _measure_reading(row: FocusMeasureRow) -> MeasureReading:
    return MeasureReading(
        id=row.id,
        project=row.project_slug,
        fingerprint=row.fingerprint,
        side=MeasureSide(row.side),
        at=row.at,
        delivered=row.delivered,
        words=row.words,
        baseline=row.baseline,
    )


def _focus_call(row: FocusCallRow) -> FocusCall:
    return FocusCall(
        id=row.id,
        project=row.project_slug,
        kind=ReadingKind(row.kind),
        card_number=row.card_number,
        fingerprint=row.fingerprint,
        document_fingerprint=row.document_fingerprint,
        call_id=row.call_id,
        session_id=row.session_id,
        opened_at=row.opened_at,
        ended_at=row.ended_at,
        landed=row.landed,
        note=row.note,
    )


def _leverage_reading(row: LeverageReadingRow) -> LeverageReading:
    return LeverageReading(
        id=row.id,
        project=row.project_slug,
        card_number=row.card_number,
        at=row.at,
        leverage=Leverage(row.leverage),
        likelihood=Likelihood(row.likelihood) if row.likelihood else None,
        words=row.words,
        focus_fingerprint=row.focus_fingerprint,
        document_fingerprint=row.document_fingerprint,
        session_id=row.session_id,
    )


def _acceptance(row: LeverageBatchRow) -> Acceptance:
    return Acceptance(
        id=row.id,
        project=row.project_slug,
        at=row.at,
        focus_fingerprint=row.focus_fingerprint,
        moves=[AcceptedMove.model_validate(m) for m in row.moves],
        put_back_at=row.put_back_at,
        note=row.note,
    )


def _decline(row: LeverageDeclineRow) -> Decline:
    return Decline(
        id=row.id,
        project=row.project_slug,
        card_number=row.card_number,
        focus_fingerprint=row.focus_fingerprint,
        document_fingerprint=row.document_fingerprint,
        leverage=Leverage(row.leverage),
        at=row.at,
    )
