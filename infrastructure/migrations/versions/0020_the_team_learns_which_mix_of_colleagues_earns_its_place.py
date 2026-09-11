"""The team learns which mix of colleagues earns its place (card #58).

Every Start assigns the card one team — the accountable hand alone, a
same-make challenge or a different-make challenge — from the evidence the
corpus, the board and git already hold, and the assignment is written once,
before the work, and never rewritten. This table is the one fact no
document can hold; everything the reading counts is derived.

Revision ID: 0020
Revises: 0019
Create Date: 2026-09-11
"""

import sqlalchemy as sa
from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "compositions",
        sa.Column("project_slug", sa.String(80), primary_key=True),
        sa.Column("card_number", sa.Integer(), primary_key=True),
        sa.Column("route", sa.Text(), nullable=False),
        sa.Column("assigned_at", sa.String(32), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("compositions")
