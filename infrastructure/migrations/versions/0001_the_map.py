"""The map: projects, groups, cards, their rows, and the audit trail.

Revision ID: 0001
Revises:
Create Date: 2026-09-03
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("slug", sa.String(80), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("path", sa.Text, nullable=False),
        sa.Column("registered_at", sa.String(32), nullable=False),
        sa.Column("next_card_number", sa.Integer, nullable=False),
        sa.Column("imported_01_at", sa.String(32), nullable=True),
    )
    op.create_table(
        "groups",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("project_slug", sa.String(80), sa.ForeignKey("projects.slug"), nullable=False),
        sa.Column("column", sa.String(40), nullable=False),
        sa.Column("name", sa.String(200), nullable=True),
        sa.Column("position", sa.Integer, nullable=False),
        sa.UniqueConstraint("project_slug", "column", "name", name="uq_group"),
    )
    op.create_table(
        "cards",
        sa.Column("project_slug", sa.String(80), sa.ForeignKey("projects.slug"), primary_key=True),
        sa.Column("number", sa.Integer, primary_key=True),
        sa.Column("group_id", sa.Integer, sa.ForeignKey("groups.id"), nullable=False),
        sa.Column("position", sa.Integer, nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("gate", sa.String(10), nullable=True),
        sa.Column("tags", sa.JSON, nullable=False),
        sa.Column("deep", sa.Text, nullable=False),
        sa.Column("citations", sa.JSON, nullable=False),
        sa.Column("link_kind", sa.String(20), nullable=True),
        sa.Column("link_stem", sa.Text, nullable=True),
        sa.Column("link_title", sa.Text, nullable=True),
        sa.Column("link_archived", sa.Boolean, nullable=True),
        sa.Column("origin", sa.String(20), nullable=False),
        sa.Column("born_at", sa.String(32), nullable=False),
    )
    op.create_table(
        "card_rows",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("project_slug", sa.String(80), nullable=False),
        sa.Column("card_number", sa.Integer, nullable=False),
        sa.Column("position", sa.Integer, nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.ForeignKeyConstraint(
            ["project_slug", "card_number"], ["cards.project_slug", "cards.number"]
        ),
    )
    op.create_table(
        "audit",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("project_slug", sa.String(80), nullable=False),
        sa.Column("card_number", sa.Integer, nullable=False),
        sa.Column("at", sa.String(32), nullable=False),
        sa.Column("actor", sa.String(20), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("from_column", sa.String(40), nullable=True),
        sa.Column("from_group", sa.String(200), nullable=True),
        sa.Column("from_position", sa.Integer, nullable=True),
        sa.Column("to_column", sa.String(40), nullable=True),
        sa.Column("to_group", sa.String(200), nullable=True),
        sa.Column("to_position", sa.Integer, nullable=True),
        sa.Column("detail", sa.Text, nullable=False),
    )
    op.create_index("ix_audit_card", "audit", ["project_slug", "card_number"])
    op.create_index("ix_card_rows_card", "card_rows", ["project_slug", "card_number"])


def downgrade() -> None:
    op.drop_index("ix_card_rows_card", table_name="card_rows")
    op.drop_index("ix_audit_card", table_name="audit")
    op.drop_table("audit")
    op.drop_table("card_rows")
    op.drop_table("cards")
    op.drop_table("groups")
    op.drop_table("projects")
