"""The doors and the loops: what sessions push, the discussions, the board's
record of each lane, the signal readings, and the trunk's state.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-04
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hook_events",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("at", sa.String(32), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("cwd", sa.Text, nullable=False),
        sa.Column("project_slug", sa.String(80), nullable=True),
        sa.Column("card_number", sa.Integer, nullable=True),
        sa.Column("source", sa.String(40), nullable=True),
        sa.Column("message", sa.Text, nullable=True),
        sa.Column("reason", sa.String(80), nullable=True),
        sa.Column("error", sa.String(80), nullable=True),
        sa.Column("transcript_path", sa.Text, nullable=True),
    )
    op.create_index("ix_hook_events_card", "hook_events", ["project_slug", "card_number"])
    op.create_index("ix_hook_events_session", "hook_events", ["session_id"])
    op.create_table(
        "discussions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("project_slug", sa.String(80), nullable=False),
        sa.Column("card_number", sa.Integer, nullable=False),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("slot", sa.String(40), nullable=False),
        sa.Column("started_at", sa.String(32), nullable=False),
    )
    op.create_index("ix_discussions_card", "discussions", ["project_slug", "card_number"])
    op.create_table(
        "lanes",
        sa.Column("project_slug", sa.String(80), primary_key=True),
        sa.Column("card_number", sa.Integer, primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("path", sa.Text, nullable=False),
        sa.Column("branch", sa.Text, nullable=True),
        sa.Column("tip", sa.String(40), nullable=True),
        sa.Column("first_seen", sa.String(32), nullable=False),
        sa.Column("last_seen", sa.String(32), nullable=False),
        sa.Column("gone_at", sa.String(32), nullable=True),
        sa.Column("folded_at", sa.String(32), nullable=True),
        sa.Column("trunk_synced_at", sa.String(32), nullable=True),
        sa.Column("main_synced_at", sa.String(32), nullable=True),
    )
    op.create_table(
        "readings",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("project_slug", sa.String(80), nullable=False),
        sa.Column("card_number", sa.Integer, nullable=False),
        sa.Column("at", sa.String(32), nullable=False),
        sa.Column("delivered", sa.Boolean, nullable=True),
        sa.Column("words", sa.Text, nullable=False),
    )
    op.create_index("ix_readings_card", "readings", ["project_slug", "card_number"])
    op.create_table(
        "trunks",
        sa.Column("project_slug", sa.String(80), primary_key=True),
        sa.Column("level", sa.Boolean, nullable=True),
        sa.Column("behind", sa.Integer, nullable=False),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("read_at", sa.String(32), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("trunks")
    op.drop_index("ix_readings_card", table_name="readings")
    op.drop_table("readings")
    op.drop_table("lanes")
    op.drop_index("ix_discussions_card", table_name="discussions")
    op.drop_table("discussions")
    op.drop_index("ix_hook_events_session", table_name="hook_events")
    op.drop_index("ix_hook_events_card", table_name="hook_events")
    op.drop_table("hook_events")
