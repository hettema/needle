"""Auto-fix is switched on per board, not for every board at once (card #80).

The dial's one row becomes the machine's — it keeps the number of fix lanes
and turns no board on — and every board's switch is its own row keyed by
slug, born off. A turn's audit row says which board it turned; a change of
the number names no board. The rows from before this migration name no
board and turned every board, which is what they did.

Revision ID: 0022
Revises: 0021
Create Date: 2026-09-12
"""

import sqlalchemy as sa
from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("dial") as dial:
        dial.add_column(sa.Column("project_slug", sa.String(80), nullable=True))
        dial.alter_column("on", existing_type=sa.Boolean(), nullable=True)
        dial.alter_column("lanes", existing_type=sa.Integer(), nullable=True)
        dial.create_unique_constraint("uq_dial_project", ["project_slug"])
    # The one row carries its number over as the machine's and turns no
    # board on: a board is on only once the owner turns its own switch. The
    # boards whose rail plan 11 recorded at the one dial's first on were
    # first on at that moment, and their rows say so — off, with the
    # baseline's date — so `needle fixes` reads "was N at its switch's
    # first on" against a first-on that exists.
    op.execute(
        'INSERT INTO dial (project_slug, "on", lanes, changed_at, first_on_at) '
        "SELECT DISTINCT r.project_slug, 0, NULL, d.changed_at, d.first_on_at "
        "FROM rail_at_on r, dial d WHERE d.id = 1"
    )
    # The machine's row keeps its dates: `changed_at` is when the number
    # was last set, and `first_on_at` is history the downgrade puts back.
    op.execute('UPDATE dial SET "on" = NULL WHERE id = 1')
    with op.batch_alter_table("dial_changes") as changes:
        changes.add_column(sa.Column("project_slug", sa.String(80), nullable=True))
        changes.alter_column("on", existing_type=sa.Boolean(), nullable=True)


def downgrade() -> None:
    # Back to the one dial: off, with its dates — from its own row, or from
    # a board's row when an earlier shape of this migration moved them.
    op.execute(
        "UPDATE dial SET changed_at = (SELECT MAX(changed_at) FROM dial WHERE "
        "project_slug IS NOT NULL) WHERE id = 1 AND changed_at IS NULL"
    )
    op.execute(
        "UPDATE dial SET first_on_at = (SELECT MIN(first_on_at) FROM dial WHERE "
        "project_slug IS NOT NULL) WHERE id = 1 AND first_on_at IS NULL"
    )
    op.execute("DELETE FROM dial WHERE project_slug IS NOT NULL")
    op.execute('UPDATE dial SET "on" = 0, lanes = COALESCE(lanes, 1) WHERE id = 1')
    op.execute('DELETE FROM dial_changes WHERE project_slug IS NOT NULL OR "on" IS NULL')
    with op.batch_alter_table("dial_changes") as changes:
        changes.alter_column("on", existing_type=sa.Boolean(), nullable=False)
        changes.drop_column("project_slug")
    with op.batch_alter_table("dial") as dial:
        dial.drop_constraint("uq_dial_project", type_="unique")
        dial.alter_column("lanes", existing_type=sa.Integer(), nullable=False)
        dial.alter_column("on", existing_type=sa.Boolean(), nullable=False)
        dial.drop_column("project_slug")
