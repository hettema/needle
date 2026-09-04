"""A running lane hears the board: where each lane's hearing stands, so the
board tells a lane each fact once and a restart forgets nothing.

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-04
"""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "heard",
        sa.Column("project_slug", sa.String(80), primary_key=True),
        sa.Column("card_number", sa.Integer(), primary_key=True),
        sa.Column("watercooler_id", sa.Integer(), nullable=False),
        sa.Column("collision", sa.Text(), nullable=True),
        sa.Column("at", sa.String(32), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("heard")
