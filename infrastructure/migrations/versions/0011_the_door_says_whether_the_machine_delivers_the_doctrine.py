"""What a session started in a project reads as its constitution, recorded at
the door: the word (`one-text`, `two-texts`, `none`), the sentence the person
saw, and the injected files behind it.

One JSON column rather than a column per field, because the reading is one
domain object (`domain/entrance.py::Entrance`) and splitting it across columns
would put the word in two places — the column and the sentence — with nothing
holding them in step.

Kept on the project rather than appended to a log because the question is a
state of the machine, not an event of the project: the answer that matters is
the one true now, and the previous answer is in git as the machine's card.

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-05
"""

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("entrance", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "entrance")
