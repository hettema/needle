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
    """A conversation opened from a card's Discuss door: its session id and
    the slot it runs on, so the one list can tell it from hands on the tree."""

    __tablename__ = "discussions"
    __table_args__ = (Index("ix_discussions_card", "project_slug", "card_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_slug: Mapped[str] = mapped_column(String(80))
    card_number: Mapped[int] = mapped_column(Integer)
    session_id: Mapped[str] = mapped_column(String(36))
    slot: Mapped[str] = mapped_column(String(40))
    started_at: Mapped[datetime] = mapped_column(UtcDateTime)


class LaneRow(Base):
    """The board's record of a card's lane: where it lives and what became of
    its work. No foreign key to cards or to the runtime's tables."""

    __tablename__ = "lanes"

    project_slug: Mapped[str] = mapped_column(String(80), primary_key=True)
    card_number: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    path: Mapped[str] = mapped_column(Text)
    branch: Mapped[str | None] = mapped_column(Text, nullable=True)
    tip: Mapped[str | None] = mapped_column(String(40), nullable=True)
    first_seen: Mapped[datetime] = mapped_column(UtcDateTime)
    last_seen: Mapped[datetime] = mapped_column(UtcDateTime)
    gone_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    folded_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    trunk_synced_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    main_synced_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)


class ReadingRow(Base):
    """One reading of a card's WATCH signal, by the board or by the owner."""

    __tablename__ = "readings"
    __table_args__ = (Index("ix_readings_card", "project_slug", "card_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_slug: Mapped[str] = mapped_column(String(80))
    card_number: Mapped[int] = mapped_column(Integer)
    at: Mapped[datetime] = mapped_column(UtcDateTime)
    delivered: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    words: Mapped[str] = mapped_column(Text)


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
