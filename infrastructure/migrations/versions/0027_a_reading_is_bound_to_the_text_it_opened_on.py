"""A reading is bound to the text it opened on (card #138, item 2).

The seat read the same two Hello Revenue cards 850 times in a day because
its only brake counted readings that died, and a reading that lands a
result is not a death. The fuse that stops that class counts every reading
the board opens on one card's text, landed or not — and a reading that
dies leaves no row saying which text it read, so the binding has to be
written when the reading opens, not when it lands. One nullable column on
the session record: the fingerprint of what that reader reads — a mark's
document and source, a title, or a parked card's record.

Every reading from before this migration reads as bound to no text, and so
counts against none: a card whose readings died three times before today
is read again, up to the cap, which is the honest state — those readings'
text is unknown, and the cap is what bounds the cost.

Revision ID: 0027
Revises: 0026
Create Date: 2026-09-14
"""

import sqlalchemy as sa
from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("windowless_sessions") as sessions:
        sessions.add_column(sa.Column("text_fingerprint", sa.String(64), nullable=True))


def downgrade() -> None:
    # The binding is what the fuse counts by; without it every reading
    # counts against no text, and the seat is back to the death cap alone —
    # the state before this card, losslessly, since nothing else read the
    # column.
    with op.batch_alter_table("windowless_sessions") as sessions:
        sessions.drop_column("text_fingerprint")
