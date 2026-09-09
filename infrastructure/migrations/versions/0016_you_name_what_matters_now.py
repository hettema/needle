"""You name what matters now, a colleague finds what holds it back, and the
board sorts every card by whether it moves that (card #87).

Eight tables, every one a version-bound fact: the owner's ruling on a focus
document by its fingerprint; a reader of the other make's verdict on a
proposal; the scheduled recheck's word; the machine readings of the two
measures; the calls the loop made in fresh threads and how each ended;
one reading per card per version of both texts; the batches an acceptance
made with every card's place before it; and the moves he left unticked.
The store holds the rulings and the readings and never the reasoning —
the reasoning is `docs/FOCUS.md`, in the project's own repository.

Revision ID: 0016
Revises: 0015
Create Date: 2026-09-09
"""

import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "focus_rulings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_slug", sa.String(80), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("what_matters", sa.Text(), nullable=False),
        sa.Column("chosen_at", sa.String(32), nullable=False),
    )
    op.create_index("ix_focus_rulings_project", "focus_rulings", ["project_slug"])
    op.create_table(
        "focus_checks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_slug", sa.String(80), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("at", sa.String(32), nullable=False),
        sa.Column("verdict", sa.String(20), nullable=False),
        sa.Column("line", sa.Text(), nullable=False),
        sa.Column("how_known", sa.String(20), nullable=True),
        sa.Column("session_id", sa.String(36), nullable=True),
    )
    op.create_index("ix_focus_checks_project", "focus_checks", ["project_slug"])
    op.create_table(
        "focus_rechecks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_slug", sa.String(80), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("at", sa.String(32), nullable=False),
        sa.Column("outcome", sa.String(30), nullable=False),
        sa.Column("words", sa.Text(), nullable=False),
        sa.Column("session_id", sa.String(36), nullable=True),
    )
    op.create_index("ix_focus_rechecks_project", "focus_rechecks", ["project_slug"])
    op.create_table(
        "focus_measures",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_slug", sa.String(80), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("side", sa.String(20), nullable=False),
        sa.Column("at", sa.String(32), nullable=False),
        sa.Column("delivered", sa.Boolean(), nullable=True),
        sa.Column("words", sa.Text(), nullable=False),
        sa.Column("baseline", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_focus_measures_project", "focus_measures", ["project_slug", "fingerprint"])
    op.create_table(
        "focus_calls",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_slug", sa.String(80), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("card_number", sa.Integer(), nullable=True),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("document_fingerprint", sa.String(64), nullable=True),
        sa.Column("call_id", sa.Integer(), nullable=True),
        sa.Column("session_id", sa.String(36), nullable=True),
        sa.Column("opened_at", sa.String(32), nullable=False),
        sa.Column("ended_at", sa.String(32), nullable=True),
        sa.Column("landed", sa.Boolean(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
    )
    op.create_index("ix_focus_calls_project", "focus_calls", ["project_slug"])
    op.create_table(
        "leverage_readings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_slug", sa.String(80), nullable=False),
        sa.Column("card_number", sa.Integer(), nullable=False),
        sa.Column("at", sa.String(32), nullable=False),
        sa.Column("leverage", sa.String(40), nullable=False),
        sa.Column("likelihood", sa.String(10), nullable=True),
        sa.Column("words", sa.Text(), nullable=False),
        sa.Column("focus_fingerprint", sa.String(64), nullable=False),
        sa.Column("document_fingerprint", sa.String(64), nullable=False),
        sa.Column("session_id", sa.String(36), nullable=True),
    )
    op.create_index(
        "ix_leverage_readings_card", "leverage_readings", ["project_slug", "card_number"]
    )
    op.create_table(
        "leverage_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_slug", sa.String(80), nullable=False),
        sa.Column("at", sa.String(32), nullable=False),
        sa.Column("focus_fingerprint", sa.String(64), nullable=False),
        sa.Column("moves", sa.JSON(), nullable=False),
        sa.Column("put_back_at", sa.String(32), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
    )
    op.create_index("ix_leverage_batches_project", "leverage_batches", ["project_slug"])
    op.create_table(
        "leverage_declines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_slug", sa.String(80), nullable=False),
        sa.Column("card_number", sa.Integer(), nullable=False),
        sa.Column("focus_fingerprint", sa.String(64), nullable=False),
        sa.Column("document_fingerprint", sa.String(64), nullable=False),
        sa.Column("leverage", sa.String(40), nullable=False),
        sa.Column("at", sa.String(32), nullable=False),
    )
    op.create_index(
        "ix_leverage_declines_card", "leverage_declines", ["project_slug", "card_number"]
    )


def downgrade() -> None:
    for name, index in (
        ("leverage_declines", "ix_leverage_declines_card"),
        ("leverage_batches", "ix_leverage_batches_project"),
        ("leverage_readings", "ix_leverage_readings_card"),
        ("focus_calls", "ix_focus_calls_project"),
        ("focus_measures", "ix_focus_measures_project"),
        ("focus_rechecks", "ix_focus_rechecks_project"),
        ("focus_checks", "ix_focus_checks_project"),
        ("focus_rulings", "ix_focus_rulings_project"),
    ):
        op.drop_index(index, table_name=name)
        op.drop_table(name)
