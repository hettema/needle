"""A reading says what ground it read: a defect's mark, or a card parked
on the owner (card #82).

Every card in Decision moment is read a second time, cold, and the board
acts on the result. The reading is plan 59's reading on wider ground, not
a second reader, so its result lands in the same table through the same
verb; the row gains the ground it read, because routing reads a mark's
verification and must never read a parked card's result as one. Every
reading before this migration read a mark.

Revision ID: 0024
Revises: 0023
Create Date: 2026-09-12
"""

import sqlalchemy as sa
from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("triages") as triages:
        triages.add_column(
            sa.Column("ground", sa.String(20), nullable=False, server_default="mark")
        )


def downgrade() -> None:
    # A parked card's readings cannot be told from a mark's without the
    # column, and routing would read them as a mark's verification: they
    # are removed rather than left to lie.
    op.execute("DELETE FROM triages WHERE ground = 'parked'")
    with op.batch_alter_table("triages") as triages:
        triages.drop_column("ground")
