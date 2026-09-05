"""Asking a colleague takes a minute, not ten, and nobody waits blind: the
calls a session makes to a running colleague, and where each lane's
hearing of the machine's watercooler stands.

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-05
"""

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "calls",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("slot", sa.String(40), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("brief", sa.Text(), nullable=False),
        sa.Column("caller", sa.Text(), nullable=False),
        sa.Column("called_at", sa.String(32), nullable=False),
        sa.Column("moved", sa.Text(), nullable=True),
        sa.Column("ended_at", sa.String(32), nullable=True),
        sa.Column("words", sa.Text(), nullable=True),
    )
    op.create_index("ix_calls_session", "calls", ["session_id"])
    op.create_table(
        "heard_notes",
        sa.Column("project_slug", sa.String(80), primary_key=True),
        sa.Column("card_number", sa.Integer(), primary_key=True),
        sa.Column("path", sa.Text(), primary_key=True),
        sa.Column("at", sa.String(32), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("heard_notes")
    op.drop_index("ix_calls_session", table_name="calls")
    op.drop_table("calls")
