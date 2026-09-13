"""A colleague is remembered by the card it was started on, and a note it
was handed is remembered until it is picked up (card #137).

Two facts the board had nowhere to keep. `session_slots.started_on` is the
card the runtime started a session on: one field, written once and never
over, because the field beside it is overwritten by every later write and
so cannot say what started a colleague — which is how a card the owner had
seen finished was reported as under way again the moment someone asked its
old session for help (card #135, 2026-09-12). `calls.handed_at` and
`calls.picked_up_at` are the note half of a call: a colleague that cannot
be resumed — one in a terminal of the owner's own, one mid-turn — is handed
the note instead, and the two stamps are what make a note standing visible
rather than lost.

Every row written before this has no `started_on` and no stamps. Nothing is
backfilled: a reader falls back to the directory, as it does today, rather
than guess which card an old session was started on.

Revision ID: 0025
Revises: 0024
Create Date: 2026-09-13

Numbered 0025/0024 while it runs in its own lane; #139 claimed 0025 first,
so this renumbers to 0026/0025 at the rebase that follows #139's fold.
"""

import sqlalchemy as sa
from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("session_slots") as slots:
        slots.add_column(sa.Column("started_on", sa.Text, nullable=True))
    with op.batch_alter_table("calls") as calls:
        calls.add_column(sa.Column("handed_at", sa.String(32), nullable=True))
        calls.add_column(sa.Column("picked_up_at", sa.String(32), nullable=True))


def downgrade() -> None:
    # A note that was handed over and not picked up has no delivery without
    # the stamps — nothing would ever carry it to its colleague, and a
    # waiter would sit on a row that can no longer arrive. Such calls are
    # ended with the reason rather than left to look open.
    op.execute(
        "UPDATE calls SET ended_at = handed_at, words = "
        "'the note was handed over, and the board that carried notes was rolled back' "
        "WHERE handed_at IS NOT NULL AND picked_up_at IS NULL AND ended_at IS NULL"
    )
    with op.batch_alter_table("calls") as calls:
        calls.drop_column("picked_up_at")
        calls.drop_column("handed_at")
    with op.batch_alter_table("session_slots") as slots:
        slots.drop_column("started_on")
