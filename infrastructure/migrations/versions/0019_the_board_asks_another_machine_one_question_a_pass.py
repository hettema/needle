"""The board asks another machine one question a pass (card #123, item 4).

Every pass records four times — collection per machine, how long the lock
was held, the first door's wait and its effect — so a pass that holds the
lock for seconds is loud where the owner looks. In the store because the
terminal's `needle beats --last` runs in its own process and is what the
plan's daily loop reads.

Revision ID: 0019
Revises: 0018
Create Date: 2026-09-11
"""

import sqlalchemy as sa
from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "beats",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("at", sa.String(32), nullable=False),
        sa.Column("collection", sa.Text(), nullable=False),
        sa.Column("lock_seconds", sa.Float(), nullable=False),
        sa.Column("door", sa.String(40), nullable=True),
        sa.Column("door_wait", sa.Float(), nullable=True),
        sa.Column("door_seconds", sa.Float(), nullable=True),
    )
    op.create_index("ix_beats_at", "beats", ["at"])


def downgrade() -> None:
    op.drop_index("ix_beats_at", table_name="beats")
    op.drop_table("beats")
