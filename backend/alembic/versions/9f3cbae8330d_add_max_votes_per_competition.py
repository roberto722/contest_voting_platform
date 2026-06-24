"""add max_votes_per_competition

Revision ID: 9f3cbae8330d
Revises: 5e2baf77d31d
Create Date: 2026-06-19 22:30:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "9f3cbae8330d"
down_revision: str | None = "5e2baf77d31d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "competitions",
        sa.Column(
            "max_votes_per_competition",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )


def downgrade() -> None:
    op.drop_column("competitions", "max_votes_per_competition")
