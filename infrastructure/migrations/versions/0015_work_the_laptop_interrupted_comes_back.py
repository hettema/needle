"""Work the laptop interrupted comes back by itself, and the board says truly
how it ended (card #68): what the board knows about a lane's deaths, its
parks and its recoveries lives here and not in one process's head.

Four tables. `sightings`: a session seen alive in a lane, with the space and
the boot it ran in — the discriminator between a row that died and one not
yet born, and the evidence a death is named from. `deaths`: why a process is
gone, named at the end and rewritten while unsettled. `parks`: what the
board waits on before it brings a lane back, at most one standing per card.
`recoveries`: each attempt to bring a lane back, written before its launch,
at most one open per card, so one interruption has one replacement across a
server that dies between the launch and its record.

Revision ID: 0015
Revises: 0014
Create Date: 2026-09-09
"""

import sqlalchemy as sa
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sightings",
        sa.Column("session_id", sa.String(36), primary_key=True),
        sa.Column("project_slug", sa.String(80), nullable=False),
        sa.Column("card_number", sa.Integer(), nullable=False),
        sa.Column("pid", sa.Integer(), nullable=False),
        sa.Column("scope", sa.Text(), nullable=True),
        sa.Column("boot_id", sa.String(40), nullable=True),
        sa.Column("first_seen", sa.String(32), nullable=False),
        sa.Column("last_seen", sa.String(32), nullable=False),
        sa.Column("released_at", sa.String(32), nullable=True),
        sa.Column("scoped_at", sa.String(32), nullable=True),
    )
    op.create_index("ix_sightings_card", "sightings", ["project_slug", "card_number"])
    op.create_table(
        "deaths",
        sa.Column("session_id", sa.String(36), primary_key=True),
        sa.Column("project_slug", sa.String(80), nullable=False),
        sa.Column("card_number", sa.Integer(), nullable=False),
        sa.Column("cause", sa.String(60), nullable=False),
        sa.Column("words", sa.Text(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False),
        sa.Column("last_alive_at", sa.String(32), nullable=True),
        sa.Column("named_at", sa.String(32), nullable=False),
        sa.Column("settled", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_deaths_card", "deaths", ["project_slug", "card_number"])
    op.create_table(
        "parks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_slug", sa.String(80), nullable=False),
        sa.Column("card_number", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("cause", sa.String(60), nullable=False),
        sa.Column("words", sa.Text(), nullable=False),
        sa.Column("waits_on", sa.String(20), nullable=False),
        sa.Column("until", sa.String(32), nullable=True),
        sa.Column("held_since", sa.String(32), nullable=True),
        sa.Column("started_at", sa.String(32), nullable=False),
        sa.Column("lifted_at", sa.String(32), nullable=True),
        sa.Column("lifted_words", sa.Text(), nullable=True),
    )
    op.create_index("ix_parks_card", "parks", ["project_slug", "card_number"])
    op.create_index(
        "ux_parks_standing",
        "parks",
        ["project_slug", "card_number"],
        unique=True,
        sqlite_where=sa.text("lifted_at IS NULL"),
    )
    op.create_table(
        "recoveries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_slug", sa.String(80), nullable=False),
        sa.Column("card_number", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("cause", sa.String(60), nullable=False),
        sa.Column("words", sa.Text(), nullable=False),
        sa.Column("started_at", sa.String(32), nullable=False),
        sa.Column("replacement", sa.String(36), nullable=True),
        sa.Column("verdict", sa.String(20), nullable=True),
        sa.Column("ended_at", sa.String(32), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
    )
    op.create_index("ix_recoveries_card", "recoveries", ["project_slug", "card_number"])
    op.create_index(
        "ux_recoveries_open",
        "recoveries",
        ["project_slug", "card_number"],
        unique=True,
        sqlite_where=sa.text("verdict IS NULL"),
    )


def downgrade() -> None:
    for table in ("recoveries", "parks", "deaths", "sightings"):
        op.drop_table(table)
