"""Defects get their own column, and the reading that verifies one grades it
(card #100).

The defects were a machine-kept group at the top of Backlog, named
"Defects" at position -1 (plan 06, item 2). They are a column of their own
now, before Backlog: the group row that was the strip becomes the Defects
column's unnamed group, so every card in it keeps its group and its
position and no card moves. A reading's row gains the grade the same
reading lands (item 2): what breaks, who it reaches, how often, each with
the reading's words. A reading from before this migration has none, and
the board reads that defect again.

Revision ID: 0023
Revises: 0022
Create Date: 2026-09-12
"""

import sqlalchemy as sa
from alembic import op

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("triages") as triages:
        triages.add_column(sa.Column("breaks", sa.String(20), nullable=True))
        triages.add_column(sa.Column("breaks_words", sa.Text(), nullable=True))
        triages.add_column(sa.Column("reach", sa.String(20), nullable=True))
        triages.add_column(sa.Column("reach_words", sa.Text(), nullable=True))
        triages.add_column(sa.Column("often", sa.String(20), nullable=True))
        triages.add_column(sa.Column("often_words", sa.Text(), nullable=True))
    # The strip becomes the column's one group. Its cards keep their group
    # id, so their positions and their folded followers are untouched.
    op.execute(
        "UPDATE groups SET \"column\" = 'Defects', name = NULL, position = 0 "
        "WHERE \"column\" = 'Backlog' AND name = 'Defects'"
    )


def downgrade() -> None:
    # Back to the strip: the Defects column's unnamed group returns to
    # Backlog as its rail, before every named group. A Defects column with
    # more than one group — none exists at this migration — keeps only the
    # unnamed one as the strip; the rest are left where they are.
    op.execute(
        "UPDATE groups SET \"column\" = 'Backlog', name = 'Defects', position = -1 "
        "WHERE \"column\" = 'Defects' AND name IS NULL"
    )
    with op.batch_alter_table("triages") as triages:
        triages.drop_column("often_words")
        triages.drop_column("often")
        triages.drop_column("reach_words")
        triages.drop_column("reach")
        triages.drop_column("breaks_words")
        triages.drop_column("breaks")
