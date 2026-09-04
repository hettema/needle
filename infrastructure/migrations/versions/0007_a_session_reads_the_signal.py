"""A session reads the signal: who made each reading, and the sessions the
board starts to read a card's signal, open while they run.

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-04
"""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("readings") as readings:
        readings.add_column(
            sa.Column("actor", sa.String(20), nullable=False, server_default="machine")
        )
    # Before this migration the actor lived only on the audit row; the owner's
    # readings are the ones the door wrote in his words.
    op.execute("UPDATE readings SET actor = 'owner' WHERE words LIKE 'the owner read it as %'")
    with op.batch_alter_table("readings") as readings:
        readings.alter_column("actor", server_default=None)
    op.create_table(
        "reading_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_slug", sa.String(80), nullable=False),
        sa.Column("card_number", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("slot", sa.String(40), nullable=False),
        sa.Column("started_at", sa.String(32), nullable=False),
        sa.Column("ended_at", sa.String(32), nullable=True),
    )
    op.create_index("ix_reading_sessions_card", "reading_sessions", ["project_slug", "card_number"])


def downgrade() -> None:
    op.drop_index("ix_reading_sessions_card", table_name="reading_sessions")
    op.drop_table("reading_sessions")
    with op.batch_alter_table("readings") as readings:
        readings.drop_column("actor")
