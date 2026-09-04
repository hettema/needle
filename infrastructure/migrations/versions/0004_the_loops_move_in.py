"""The loops move in: every machine move names the predicate it satisfied.

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-04
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("audit") as audit:
        audit.add_column(sa.Column("evidence", sa.String(30), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("audit") as audit:
        audit.drop_column("evidence")
