"""Auto-fix stops at the line the owner drew, per board (card #149).

The dial had two settings — on or off, and how many at once — so "on"
meant every verified defect on the column, gravest first, until it was
empty; on Hello Revenue that is 30 cards that reach a client or money and
then 48 that reach only the owner or a session, which he ruled on
2026-09-15 wait for a signal. The line is one more setting on the row that
keeps the switch: a band of the grade's ladder, at or above which the beat
takes a defect. The audit row carries the board's line after each turn,
so a moment's line is read from the audit as the switch is.

NULL is the last rung — every defect, where auto-fix reached before this
— and the same fact as the last rung written out (ruling 3), so every
board keeps doing exactly what it did until the owner moves its line.

Revision ID: 0028
Revises: 0027
Create Date: 2026-09-15
"""

import sqlalchemy as sa
from alembic import op

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("dial") as dial:
        dial.add_column(sa.Column("line", sa.String(20), nullable=True))
    with op.batch_alter_table("dial_changes") as changes:
        changes.add_column(sa.Column("line", sa.String(20), nullable=True))


def downgrade() -> None:
    # Without the line every board takes every defect again, which is the
    # state before this card; the switch, the number and every audit row
    # stand, since the line rode on them and was never its own row.
    with op.batch_alter_table("dial_changes") as changes:
        changes.drop_column("line")
    with op.batch_alter_table("dial") as dial:
        dial.drop_column("line")
