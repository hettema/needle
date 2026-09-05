"""A defect's mark is verified before it routes, and an unmarked one is
nobody's yet: the independent readings and what each bound itself to, the
short corpus lanes that apply a split or a ruling, and the decision identity
a fix lane now carries.

Revision ID: 0012
Revises: 0011
Create Date: 2026-09-05
"""

import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "triages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_slug", sa.String(80), nullable=False),
        sa.Column("card_number", sa.Integer(), nullable=False),
        sa.Column("at", sa.String(32), nullable=False),
        sa.Column("actor", sa.String(20), nullable=False),
        sa.Column("result", sa.String(20), nullable=False),
        sa.Column("words", sa.Text(), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("parent", sa.String(32), nullable=True),
        sa.Column("direction", sa.String(40), nullable=True),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("source_path", sa.Text(), nullable=True),
        sa.Column("source_fingerprint", sa.String(64), nullable=True),
        sa.Column("document_fingerprint", sa.String(64), nullable=False),
        sa.Column("session_id", sa.String(36), nullable=True),
    )
    op.create_index("ix_triages_card", "triages", ["project_slug", "card_number"])
    op.create_index("ix_triages_decision", "triages", ["decision"])
    op.create_table(
        "corpus_lanes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_slug", sa.String(80), nullable=False),
        sa.Column("card_number", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("path", sa.Text(), nullable=True),
        sa.Column("session_id", sa.String(36), nullable=True),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("opened_at", sa.String(32), nullable=False),
        sa.Column("ended_at", sa.String(32), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
    )
    op.create_index("ix_corpus_lanes_card", "corpus_lanes", ["project_slug", "card_number"])
    with op.batch_alter_table("fix_lanes") as batch:
        batch.add_column(sa.Column("decision", sa.String(32), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("fix_lanes") as batch:
        batch.drop_column("decision")
    op.drop_index("ix_corpus_lanes_card", table_name="corpus_lanes")
    op.drop_table("corpus_lanes")
    op.drop_index("ix_triages_decision", table_name="triages")
    op.drop_index("ix_triages_card", table_name="triages")
    op.drop_table("triages")
