"""The tables, as SQLAlchemy sees them. The migration under `migrations/` is
the same schema written as steps; a test refuses the two drifting apart."""

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    TypeDecorator,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class UtcDateTime(TypeDecorator[datetime]):
    """An aware UTC datetime stored as ISO text; SQLite keeps no zone itself."""

    impl = String(32)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: object) -> str | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("The store takes aware datetimes only.")
        return value.astimezone(UTC).isoformat()

    def process_result_value(self, value: str | None, dialect: object) -> datetime | None:
        if value is None:
            return None
        return datetime.fromisoformat(value).astimezone(UTC)


class Base(DeclarativeBase):
    pass


class ProjectRow(Base):
    __tablename__ = "projects"

    slug: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    path: Mapped[str] = mapped_column(Text)
    registered_at: Mapped[datetime] = mapped_column(UtcDateTime)
    next_card_number: Mapped[int] = mapped_column(Integer)
    imported_01_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)


class GroupRow(Base):
    __tablename__ = "groups"
    __table_args__ = (UniqueConstraint("project_slug", "column", "name", name="uq_group"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_slug: Mapped[str] = mapped_column(ForeignKey("projects.slug"))
    column: Mapped[str] = mapped_column(String(40))
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    position: Mapped[int] = mapped_column(Integer)


class CardRow(Base):
    __tablename__ = "cards"

    project_slug: Mapped[str] = mapped_column(ForeignKey("projects.slug"), primary_key=True)
    number: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"))
    position: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(Text)
    gate: Mapped[str | None] = mapped_column(String(10), nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSON)
    deep: Mapped[str] = mapped_column(Text)
    citations: Mapped[list[str]] = mapped_column(JSON)
    link_kind: Mapped[str | None] = mapped_column(String(20), nullable=True)
    link_stem: Mapped[str | None] = mapped_column(Text, nullable=True)
    link_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    link_archived: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    origin: Mapped[str] = mapped_column(String(20))
    born_at: Mapped[datetime] = mapped_column(UtcDateTime)
    folded_into: Mapped[int | None] = mapped_column(Integer, nullable=True)
    """The card this one is folded under (plan 06, item 5); its group follows that card's."""


class CardRowRow(Base):
    """A labelled row on a card. The class name is the table's: rows of cards."""

    __tablename__ = "card_rows"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_slug", "card_number"], ["cards.project_slug", "cards.number"]
        ),
        Index("ix_card_rows_card", "project_slug", "card_number"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_slug: Mapped[str] = mapped_column(String(80))
    card_number: Mapped[int] = mapped_column(Integer)
    position: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(20))
    text: Mapped[str] = mapped_column(Text)


class SessionSlotRow(Base):
    """Where a session the runtime started or moved runs. No foreign key to
    cards: the runtime's records and the board's can be reset apart."""

    __tablename__ = "session_slots"

    session_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    slot: Mapped[str] = mapped_column(String(40))
    card: Mapped[str] = mapped_column(Text)
    scope: Mapped[str] = mapped_column(Text)
    recorded_at: Mapped[datetime] = mapped_column(UtcDateTime)


class RescueRow(Base):
    """One move of a session between rungs. Separate from session_slots so
    clearing a session's history never clears its slot."""

    __tablename__ = "rescues"
    __table_args__ = (Index("ix_rescues_session", "session_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36))
    from_slot: Mapped[str | None] = mapped_column(String(40), nullable=True)
    from_model: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_slot: Mapped[str] = mapped_column(String(40))
    to_model: Mapped[str | None] = mapped_column(String(20), nullable=True)
    reason: Mapped[str] = mapped_column(Text)
    at: Mapped[datetime] = mapped_column(UtcDateTime)


class WindowRow(Base):
    """A window the runtime opened and proved, by the compositor's address."""

    __tablename__ = "windows"
    __table_args__ = (Index("ix_windows_session", "session_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36))
    kind: Mapped[str] = mapped_column(String(20))
    app_id: Mapped[str] = mapped_column(Text)
    address: Mapped[str] = mapped_column(String(40))
    opened_at: Mapped[datetime] = mapped_column(UtcDateTime)
    closed_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)


class HookEventRow(Base):
    """One hook firing, as posted by a session. Attributed to a card by its
    working directory when that is a lane of a registered project."""

    __tablename__ = "hook_events"
    __table_args__ = (
        Index("ix_hook_events_card", "project_slug", "card_number"),
        Index("ix_hook_events_session", "session_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    at: Mapped[datetime] = mapped_column(UtcDateTime)
    kind: Mapped[str] = mapped_column(String(20))
    session_id: Mapped[str] = mapped_column(String(36))
    cwd: Mapped[str] = mapped_column(Text)
    project_slug: Mapped[str | None] = mapped_column(String(80), nullable=True)
    card_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str | None] = mapped_column(String(40), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error: Mapped[str | None] = mapped_column(String(80), nullable=True)
    transcript_path: Mapped[str | None] = mapped_column(Text, nullable=True)


class DiscussionRow(Base):
    """A conversation opened from the board — a card's Discuss door, or the
    head's Idea door about no card yet — by its session id and the slot it
    runs on, so the one list can tell it from hands on a tree."""

    __tablename__ = "discussions"
    __table_args__ = (Index("ix_discussions_card", "project_slug", "card_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_slug: Mapped[str] = mapped_column(String(80))
    card_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    kind: Mapped[str] = mapped_column(String(20))
    """The window kind it was opened through: board-discuss, board-idea or board-plan."""
    session_id: Mapped[str] = mapped_column(String(36))
    slot: Mapped[str] = mapped_column(String(40))
    started_at: Mapped[datetime] = mapped_column(UtcDateTime)


class WriteStampRow(Base):
    """One row: how many transactions have committed to this store, from any
    process, and who committed last. Every write stamps it, so the server
    can tell a commit from another process (a session's `needle row`, a
    `needle add`) from its own and act on it within a second, with no file
    watching and no change to the writers (plan 06, item 6)."""

    __tablename__ = "writes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seq: Mapped[int] = mapped_column(Integer)
    origin: Mapped[str] = mapped_column(String(36))
    """The writing `Store`'s own id, one per process."""
    at: Mapped[datetime] = mapped_column(UtcDateTime)


class WatercoolerRow(Base):
    """One line of a project's watercooler: what a lane, or the board, said
    to every other lane (plan 07, item 2). No foreign key to cards: the
    board's own lines name no card."""

    __tablename__ = "watercooler"
    __table_args__ = (Index("ix_watercooler_project", "project_slug"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_slug: Mapped[str] = mapped_column(String(80))
    card_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actor: Mapped[str] = mapped_column(String(20))
    at: Mapped[datetime] = mapped_column(UtcDateTime)
    text: Mapped[str] = mapped_column(Text)


class LaneRow(Base):
    """The board's record of a card's lane: where it lives and what became of
    its work. No foreign key to cards or to the runtime's tables."""

    __tablename__ = "lanes"

    project_slug: Mapped[str] = mapped_column(String(80), primary_key=True)
    card_number: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    path: Mapped[str] = mapped_column(Text)
    branch: Mapped[str | None] = mapped_column(Text, nullable=True)
    birth: Mapped[str | None] = mapped_column(String(40), nullable=True)
    tip: Mapped[str | None] = mapped_column(String(40), nullable=True)
    first_seen: Mapped[datetime] = mapped_column(UtcDateTime)
    last_seen: Mapped[datetime] = mapped_column(UtcDateTime)
    gone_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    folded_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    trunk_synced_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    main_synced_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)


class HeardRow(Base):
    """Where a running lane's hearing stands (plan 10, item 1): the newest
    watercooler line it was told and the drift sentence it was last told, so
    the board says each fact once and a restart forgets nothing. No foreign
    key to cards or lanes: the mark is cleared with the lane record when the
    card is launched again."""

    __tablename__ = "heard"

    project_slug: Mapped[str] = mapped_column(String(80), primary_key=True)
    card_number: Mapped[int] = mapped_column(Integer, primary_key=True)
    watercooler_id: Mapped[int] = mapped_column(Integer)
    collision: Mapped[str | None] = mapped_column(Text, nullable=True)
    at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)


class ReadingRow(Base):
    """One reading of a card's WATCH signal, by the board, by a reading
    session's finding, or by the owner."""

    __tablename__ = "readings"
    __table_args__ = (Index("ix_readings_card", "project_slug", "card_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_slug: Mapped[str] = mapped_column(String(80))
    card_number: Mapped[int] = mapped_column(Integer)
    at: Mapped[datetime] = mapped_column(UtcDateTime)
    delivered: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    words: Mapped[str] = mapped_column(Text)
    actor: Mapped[str] = mapped_column(String(20))
    """Who read it (plan 09): the rail asks the owner about a session's
    cannot-tell, never about a machine's unreadable."""


class WindowlessSessionRow(Base):
    """A session the board started with no window and no worktree: to read
    one card's signal (plan 09, item 1) or to plan a marked defect under the
    dial (plan 11, item 4). Open while it runs, ended when its finding or
    its plan lands or its process is gone. The loops read the open rows to
    list the session on its card and to start no second one."""

    __tablename__ = "windowless_sessions"
    __table_args__ = (Index("ix_windowless_sessions_card", "project_slug", "card_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_slug: Mapped[str] = mapped_column(String(80))
    card_number: Mapped[int] = mapped_column(Integer)
    work: Mapped[str] = mapped_column(String(20))
    """`reading` or `planning`: what the session was started to do."""
    session_id: Mapped[str] = mapped_column(String(36))
    slot: Mapped[str] = mapped_column(String(40))
    started_at: Mapped[datetime] = mapped_column(UtcDateTime)
    ended_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)


class DialRow(Base):
    """One row: the owner's standing ruling on defects (plan 11, item 3).
    On or off and the number of fix lanes, kept here so a restart keeps his
    setting; every turn is a row in `dial_changes`."""

    __tablename__ = "dial"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    on: Mapped[bool] = mapped_column(Boolean)
    lanes: Mapped[int] = mapped_column(Integer)
    changed_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    first_on_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)


class DialChangeRow(Base):
    """One turn of the dial: who, when, to what. The audit table is per card
    and the dial is about no card, so its record is its own."""

    __tablename__ = "dial_changes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    at: Mapped[datetime] = mapped_column(UtcDateTime)
    actor: Mapped[str] = mapped_column(String(20))
    on: Mapped[bool] = mapped_column(Boolean)
    lanes: Mapped[int] = mapped_column(Integer)


class FixLaneRow(Base):
    """One defect the dial took (plan 11, item 4): the stage it is at, from
    its planning session to its fold, and when each stage began. What the
    loop counts against the number, and what `needle fixes` reads."""

    __tablename__ = "fix_lanes"
    __table_args__ = (Index("ix_fix_lanes_card", "project_slug", "card_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_slug: Mapped[str] = mapped_column(String(80))
    card_number: Mapped[int] = mapped_column(Integer)
    stage: Mapped[str] = mapped_column(String(20))
    planning_started_at: Mapped[datetime] = mapped_column(UtcDateTime)
    planned_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class RailAtOnRow(Base):
    """The defects rail of each project at the moment the dial was first
    turned on, by who filed each card (plan 11, item 6): the baseline the
    thirty-lane look reads the rail against."""

    __tablename__ = "rail_at_on"
    __table_args__ = (UniqueConstraint("project_slug", "filer", name="uq_rail_at_on"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_slug: Mapped[str] = mapped_column(String(80))
    filer: Mapped[str] = mapped_column(String(20))
    count: Mapped[int] = mapped_column(Integer)


class TrunkRow(Base):
    """A project's main checkout against origin/develop, as last kept."""

    __tablename__ = "trunks"

    project_slug: Mapped[str] = mapped_column(String(80), primary_key=True)
    level: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    behind: Mapped[int] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)


class AuditRow(Base):
    """One row per change. No foreign key to cards: a card's history outlives it."""

    __tablename__ = "audit"
    __table_args__ = (Index("ix_audit_card", "project_slug", "card_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_slug: Mapped[str] = mapped_column(String(80))
    card_number: Mapped[int] = mapped_column(Integer)
    at: Mapped[datetime] = mapped_column(UtcDateTime)
    actor: Mapped[str] = mapped_column(String(20))
    kind: Mapped[str] = mapped_column(String(20))
    from_column: Mapped[str | None] = mapped_column(String(40), nullable=True)
    from_group: Mapped[str | None] = mapped_column(String(200), nullable=True)
    from_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    to_column: Mapped[str | None] = mapped_column(String(40), nullable=True)
    to_group: Mapped[str | None] = mapped_column(String(200), nullable=True)
    to_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detail: Mapped[str] = mapped_column(Text)
    evidence: Mapped[str | None] = mapped_column(String(30), nullable=True)


class CallRow(Base):
    """A call to a colleague (plan 17): which session was called warm, with
    which note and where the answer lands, and how it went. Follows the
    forked id when the runtime moves the colleague; ended with the
    runtime's words when the colleague is blocked, moved or ends without
    its note, so a waiter reads the truth instead of a ceiling."""

    __tablename__ = "calls"
    __table_args__ = (Index("ix_calls_session", "session_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36))
    slot: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(200))
    note: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    brief: Mapped[str] = mapped_column(Text)
    caller: Mapped[str] = mapped_column(Text)
    called_at: Mapped[datetime] = mapped_column(UtcDateTime)
    moved: Mapped[str | None] = mapped_column(Text, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    words: Mapped[str | None] = mapped_column(Text, nullable=True)


class HeardNoteRow(Base):
    """Where a lane's hearing of the machine's watercooler stands (plan 17,
    item 2): per note, the change the lane last heard or made. A note the
    lane wrote is stamped at the write, so it never hears its own; a later
    change by another party moves the file past the stamp and is heard.
    Cleared with the lane record, as the heard mark is."""

    __tablename__ = "heard_notes"

    project_slug: Mapped[str] = mapped_column(String(80), primary_key=True)
    card_number: Mapped[int] = mapped_column(Integer, primary_key=True)
    path: Mapped[str] = mapped_column(Text, primary_key=True)
    at: Mapped[datetime] = mapped_column(UtcDateTime)
