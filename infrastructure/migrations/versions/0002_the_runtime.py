"""The runtime's own records: where a session runs, its rescues, its windows.

Three tables with no foreign key to the board's, so either half can be
reset without the other (plan 02, item 3).

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-04
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "session_slots",
        sa.Column("session_id", sa.String(36), primary_key=True),
        sa.Column("slot", sa.String(40), nullable=False),
        sa.Column("card", sa.Text, nullable=False),
        sa.Column("scope", sa.Text, nullable=False),
        sa.Column("recorded_at", sa.String(32), nullable=False),
    )
    op.create_table(
        "rescues",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("from_slot", sa.String(40), nullable=True),
        sa.Column("from_model", sa.String(20), nullable=True),
        sa.Column("to_slot", sa.String(40), nullable=False),
        sa.Column("to_model", sa.String(20), nullable=True),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("at", sa.String(32), nullable=False),
    )
    op.create_index("ix_rescues_session", "rescues", ["session_id"])
    op.create_table(
        "windows",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("app_id", sa.Text, nullable=False),
        sa.Column("address", sa.String(40), nullable=False),
        sa.Column("opened_at", sa.String(32), nullable=False),
        sa.Column("closed_at", sa.String(32), nullable=True),
    )
    op.create_index("ix_windows_session", "windows", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_windows_session", table_name="windows")
    op.drop_table("windows")
    op.drop_index("ix_rescues_session", table_name="rescues")
    op.drop_table("rescues")
    op.drop_table("session_slots")
