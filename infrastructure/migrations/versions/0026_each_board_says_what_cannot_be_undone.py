"""Each board says what cannot be undone there, at the turn that bounds it
(card #139, item 2).

Turning auto-fix on was deciding two things at once: what enters execution
without the owner, and — on a project that deploys from its stable branch —
what reaches customers without him. The declaration rides with the ruling
it bounds, so it lives beside the switch rather than in a settings concept
of its own: the paths in that project whose change cannot be taken back,
and where its standing hold on releasing is written.

Every board on before this migration keeps working and reads as undeclared,
which is NULL here and not an empty declaration: undeclared releases
everything, exactly as it did yesterday, and the head says so in those
words rather than claiming the owner declared nothing.

Revision ID: 0026
Revises: 0025
Create Date: 2026-09-13
"""

import sqlalchemy as sa
from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("dial") as dial:
        dial.add_column(sa.Column("cannot_undo", sa.Text(), nullable=True))
        dial.add_column(sa.Column("hold_file", sa.String(400), nullable=True))
        dial.add_column(sa.Column("declared_at", sa.String(32), nullable=True))
    with op.batch_alter_table("dial_changes") as changes:
        changes.add_column(sa.Column("declared", sa.Text(), nullable=True))
    # Which card's fold was refused the promotion, so the board never guesses
    # which one's release is the one waiting (item 3).
    with op.batch_alter_table("lanes") as lanes:
        lanes.add_column(sa.Column("release_held_at", sa.String(32), nullable=True))


def downgrade() -> None:
    # The declaration is the only thing that holds a release, so dropping it
    # means every board releases everything again. That is the state before
    # this card and it is the honest downgrade; the audit lines in
    # dial_changes go with it, which is why the owner re-declares at his next
    # turn rather than inheriting a half-remembered bound (card #80 lost its
    # per-board audit rows the same way, and that is a defect on its card).
    with op.batch_alter_table("lanes") as lanes:
        lanes.drop_column("release_held_at")
    with op.batch_alter_table("dial_changes") as changes:
        changes.drop_column("declared")
    with op.batch_alter_table("dial") as dial:
        dial.drop_column("declared_at")
        dial.drop_column("hold_file")
        dial.drop_column("cannot_undo")
