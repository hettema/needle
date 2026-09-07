"""Every row on a card says when it was written and by whom, so a project's
own tooling can read the board's record back — Hello Revenue's morning note
lost its DELIVERED sentences when the rows moved from a card file into this
store (plan 08, item 3).

Two columns on the rows themselves rather than a join against the audit at
read time, because the audit's row line is written for a person: it cuts the
text at 140 characters and names the kind and the verb in prose, so a reader
that reconstructed time and writer from it would be parsing a sentence to
recover a fact the row can carry itself.

The backfill reads that audit once, here: a row's time and writer are the
latest audit line that wrote its kind on its card (one-per-card kinds are
rewritten in place, so the latest line is the standing text's), else the
n-th line that wrote the kind, in order; a row no audit line accounts for —
0.1's imported rows — is dated at the card's birth and signed by the import.

Revision ID: 0013
Revises: 0012
Create Date: 2026-09-07
"""

import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

ONE_PER_CARD = ("DELIVERED", "WATCH", "REVIEW", "HANDED OUT")
"""The kinds `infrastructure/store.py::ONE_PER_CARD` rewrites in place, as
they stood when this migration was written; a kind added later is not
backfilled here, since it has no rows older than this migration."""


def upgrade() -> None:
    with op.batch_alter_table("card_rows") as batch:
        batch.add_column(sa.Column("written_at", sa.String(32), nullable=True))
        batch.add_column(sa.Column("writer", sa.String(20), nullable=True))
    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            "SELECT id, project_slug, card_number, kind, position FROM card_rows "
            "ORDER BY project_slug, card_number, position"
        )
    ).all()
    lines = connection.execute(
        sa.text(
            "SELECT project_slug, card_number, at, actor, detail FROM audit "
            "WHERE kind = 'row' ORDER BY id"
        )
    ).all()
    births = {
        (slug, number): (at, "import")
        for slug, number, at in connection.execute(
            sa.text("SELECT project_slug, number, born_at FROM cards")
        ).all()
    }
    written: dict[tuple[str, int, str], list[tuple[str, str]]] = {}
    latest: dict[tuple[str, int, str], tuple[str, str]] = {}
    for slug, number, at, actor, detail in lines:
        wrote = _row_write(detail)
        if wrote is None:
            continue
        kind, fresh = wrote
        key = (slug, number, kind)
        latest[key] = (at, actor)
        if fresh:
            written.setdefault(key, []).append((at, actor))
    seen: dict[tuple[str, int, str], int] = {}
    for row_id, slug, number, kind, _ in rows:
        key = (slug, number, kind)
        if kind in ONE_PER_CARD:
            found = latest.get(key)
        else:
            index = seen.get(key, 0)
            seen[key] = index + 1
            lines_of = written.get(key, [])
            found = lines_of[index] if index < len(lines_of) else None
        at, actor = found or births.get((slug, number), (None, "import"))
        connection.execute(
            sa.text("UPDATE card_rows SET written_at = :at, writer = :writer WHERE id = :id"),
            {"at": at, "writer": actor, "id": row_id},
        )


def _row_write(detail: str) -> tuple[str, bool] | None:
    """The row kind an audit line wrote and whether it was a fresh write:
    `<KIND> written:` (fresh) or `<KIND> rewritten:` (in place), where the
    kind may carry a space (HANDED OUT); the owner's ruling on a verdict
    (`VERDICT accepted:` / `VERDICT overturned:`) writes a RULED row."""
    for verb, fresh in ((" written:", True), (" rewritten:", False)):
        cut = detail.find(verb)
        if cut > 0:
            return detail[:cut], fresh
    if detail.startswith(("VERDICT accepted:", "VERDICT overturned:")):
        return "RULED", True
    return None


def downgrade() -> None:
    with op.batch_alter_table("card_rows") as batch:
        batch.drop_column("writer")
        batch.drop_column("written_at")
