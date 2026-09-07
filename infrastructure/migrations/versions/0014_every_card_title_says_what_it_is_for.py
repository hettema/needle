"""A card's title is read cold at its birth, and a title the owner could
not place is a machine fact on the face that holds Start closed until a
reading passes (card #74, item 3).

One table: one row per reading of a card's title and essence, bound by a
fingerprint to the text it judged, with the reader's words and the words
that failed. Kept apart from `triages` because a title reading lands on
every plan and idea and is not a decision off the owner's rail; a row here
never routes anything and never carries a decision identity.

Revision ID: 0014
Revises: 0013
Create Date: 2026-09-07
"""

import sqlalchemy as sa
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "title_readings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_slug", sa.String(80), nullable=False),
        sa.Column("card_number", sa.Integer(), nullable=False),
        sa.Column("at", sa.String(32), nullable=False),
        sa.Column("verdict", sa.String(20), nullable=False),
        sa.Column("words", sa.Text(), nullable=False),
        sa.Column("failed", sa.Text(), nullable=False),
        sa.Column("title_fingerprint", sa.String(64), nullable=False),
        sa.Column("session_id", sa.String(36), nullable=True),
    )
    op.create_index("ix_title_readings_card", "title_readings", ["project_slug", "card_number"])


def downgrade() -> None:
    op.drop_index("ix_title_readings_card", table_name="title_readings")
    op.drop_table("title_readings")
