"""A machine's clone of a project is one record (card #83, item 3).

The board levels every other machine's clone of every project on its beat
and says which is not level on that machine's line of the head. The
terminal's `needle machines` runs in its own process and read an empty
list while the page warned (Codex's ninth pass), so the levelling's
finding is a row per machine and project, read by both.

Revision ID: 0018
Revises: 0017
Create Date: 2026-09-10
"""

import sqlalchemy as sa
from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "clones",
        sa.Column("machine", sa.String(40), primary_key=True),
        sa.Column("project", sa.String(80), primary_key=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("at", sa.String(32), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("clones")
