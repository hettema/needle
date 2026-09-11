"""A session's message is held once (card #124, item 2).

A hook that heard no answer within its two seconds re-sent its whole
queue on every firing, and the board recorded the batch again each time:
on the laptop's store, 47,001 of 49,938 hook events were echoes of 1,728
groups. The echoes fold to one row each, keeping the first — the row every
card's history and every loop's read already stood on — and a unique index
over (session, kind, moment) holds it from here, whoever posts.

Revision ID: 0019
Revises: 0018
Create Date: 2026-09-11
"""

from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "DELETE FROM hook_events WHERE id NOT IN ("
        "SELECT MIN(id) FROM hook_events GROUP BY session_id, kind, at)"
    )
    op.create_index(
        "ux_hook_events_moment", "hook_events", ["session_id", "kind", "at"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ux_hook_events_moment", table_name="hook_events")
