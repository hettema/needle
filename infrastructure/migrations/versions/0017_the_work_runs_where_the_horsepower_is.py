"""The work runs where the horsepower is, and the board feels like it is on
your laptop (card #83).

Three tables and one column. The machines the board knows, one row each,
registered like a project; the least memory each had available per day,
which is the mark the plan's loop reads to decide 32 or 64 GB; the build
timings measured by hand on each machine; and, on the runtime's record of
where a session runs, which machine it was started on, so a lane the system
killed is counted against the machine that killed it.

Revision ID: 0017
Revises: 0016
Create Date: 2026-09-09
"""

import sqlalchemy as sa
from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "machines",
        sa.Column("name", sa.String(40), primary_key=True),
        sa.Column("machine_id", sa.String(64), nullable=False, unique=True),
        sa.Column("host", sa.String(200), nullable=True),
        sa.Column("desktop", sa.Boolean(), nullable=False),
        sa.Column("ground", sa.Text(), nullable=True),
        sa.Column("command", sa.Text(), nullable=False),
        sa.Column("added_at", sa.String(32), nullable=False),
    )
    op.create_table(
        "high_water",
        sa.Column("machine", sa.String(40), primary_key=True),
        sa.Column("day", sa.String(10), primary_key=True),
        sa.Column("least_available", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("at", sa.String(32), nullable=False),
    )
    op.create_table(
        "timings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("machine", sa.String(40), nullable=False),
        sa.Column("what", sa.String(40), nullable=False),
        sa.Column("seconds", sa.Float(), nullable=False),
        sa.Column("at", sa.String(32), nullable=False),
    )
    op.create_index("ix_timings_machine", "timings", ["machine", "what"])
    op.add_column(
        "session_slots", sa.Column("machine", sa.String(40), nullable=False, server_default="")
    )


def downgrade() -> None:
    with op.batch_alter_table("session_slots") as batch:
        batch.drop_column("machine")
    op.drop_index("ix_timings_machine", table_name="timings")
    op.drop_table("timings")
    op.drop_table("high_water")
    op.drop_table("machines")
