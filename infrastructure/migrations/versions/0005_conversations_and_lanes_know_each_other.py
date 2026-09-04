"""Conversations and lanes know each other: the watercooler, and a
discussion about no card yet.

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-04
"""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "watercooler",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_slug", sa.String(80), nullable=False),
        sa.Column("card_number", sa.Integer(), nullable=True),
        sa.Column("actor", sa.String(20), nullable=False),
        sa.Column("at", sa.String(32), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
    )
    op.create_index("ix_watercooler_project", "watercooler", ["project_slug"])
    with op.batch_alter_table("discussions") as discussions:
        discussions.alter_column("card_number", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("discussions") as discussions:
        discussions.alter_column("card_number", existing_type=sa.Integer(), nullable=False)
    op.drop_index("ix_watercooler_project", table_name="watercooler")
    op.drop_table("watercooler")
