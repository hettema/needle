"""The board at a glance: a card folded under the card whose plan carries it,
the kind of door a discussion was opened through, and the write stamp the
server reads to hear another process's commit.

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-04
"""

from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("cards") as cards:
        cards.add_column(sa.Column("folded_into", sa.Integer(), nullable=True))
    with op.batch_alter_table("discussions") as discussions:
        discussions.add_column(
            sa.Column("kind", sa.String(20), nullable=False, server_default="board-discuss")
        )
    # The rows before this migration were a card's Discuss or, with no card, the head's Idea.
    op.execute("UPDATE discussions SET kind = 'board-idea' WHERE card_number IS NULL")
    with op.batch_alter_table("discussions") as discussions:
        discussions.alter_column("kind", server_default=None)
    op.create_table(
        "writes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("origin", sa.String(36), nullable=False),
        sa.Column("at", sa.String(32), nullable=False),
    )
    op.execute(
        sa.text("INSERT INTO writes (id, seq, origin, at) VALUES (1, 0, '', :at)").bindparams(
            at=datetime.now(UTC).isoformat()
        )
    )


def downgrade() -> None:
    op.drop_table("writes")
    with op.batch_alter_table("discussions") as discussions:
        discussions.drop_column("kind")
    with op.batch_alter_table("cards") as cards:
        cards.drop_column("folded_into")
