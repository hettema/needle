"""Defects fix themselves: the dial and its turns, the fix lanes it ran, the
rail's size when it was first turned on, and the reading session generalised
to a windowless session that reads a signal or plans a defect.

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-05
"""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The reading session was the one windowless session the board started
    # (plan 09); the dial's planning session is the second (plan 11), and one
    # table with a `work` column is one way to start, list and tend both.
    op.rename_table("reading_sessions", "windowless_sessions")
    op.drop_index("ix_reading_sessions_card", table_name="windowless_sessions")
    with op.batch_alter_table("windowless_sessions") as sessions:
        sessions.add_column(
            sa.Column("work", sa.String(20), nullable=False, server_default="reading")
        )
    with op.batch_alter_table("windowless_sessions") as sessions:
        sessions.alter_column("work", server_default=None)
    op.create_index(
        "ix_windowless_sessions_card", "windowless_sessions", ["project_slug", "card_number"]
    )
    op.create_table(
        "dial",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("on", sa.Boolean(), nullable=False),
        sa.Column("lanes", sa.Integer(), nullable=False),
        sa.Column("changed_at", sa.String(32), nullable=True),
        sa.Column("first_on_at", sa.String(32), nullable=True),
    )
    # Off until the owner turns it: nothing starts by itself on a board that
    # has never been told to.
    op.execute(
        'INSERT INTO dial (id, "on", lanes, changed_at, first_on_at) VALUES (1, 0, 1, NULL, NULL)'
    )
    op.create_table(
        "dial_changes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("at", sa.String(32), nullable=False),
        sa.Column("actor", sa.String(20), nullable=False),
        sa.Column("on", sa.Boolean(), nullable=False),
        sa.Column("lanes", sa.Integer(), nullable=False),
    )
    op.create_table(
        "fix_lanes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_slug", sa.String(80), nullable=False),
        sa.Column("card_number", sa.Integer(), nullable=False),
        sa.Column("stage", sa.String(20), nullable=False),
        sa.Column("planning_started_at", sa.String(32), nullable=False),
        sa.Column("planned_at", sa.String(32), nullable=True),
        sa.Column("started_at", sa.String(32), nullable=True),
        sa.Column("ended_at", sa.String(32), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
    )
    op.create_index("ix_fix_lanes_card", "fix_lanes", ["project_slug", "card_number"])
    op.create_table(
        "rail_at_on",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_slug", sa.String(80), nullable=False),
        sa.Column("filer", sa.String(20), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.UniqueConstraint("project_slug", "filer", name="uq_rail_at_on"),
    )


def downgrade() -> None:
    op.drop_table("rail_at_on")
    op.drop_index("ix_fix_lanes_card", table_name="fix_lanes")
    op.drop_table("fix_lanes")
    op.drop_table("dial_changes")
    op.drop_table("dial")
    op.drop_index("ix_windowless_sessions_card", table_name="windowless_sessions")
    with op.batch_alter_table("windowless_sessions") as sessions:
        sessions.drop_column("work")
    op.rename_table("windowless_sessions", "reading_sessions")
    op.create_index("ix_reading_sessions_card", "reading_sessions", ["project_slug", "card_number"])
