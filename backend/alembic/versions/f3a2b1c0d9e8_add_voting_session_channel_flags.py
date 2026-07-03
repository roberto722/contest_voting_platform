"""add voting session channel flags

Revision ID: f3a2b1c0d9e8
Revises: e1b2c3d4f5a6
Create Date: 2026-06-29 15:35:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f3a2b1c0d9e8"
down_revision: str | None = "e1b2c3d4f5a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "voting_sessions",
        sa.Column("public_voting_open", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "voting_sessions",
        sa.Column("judge_voting_open", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.alter_column("voting_sessions", "public_voting_open", server_default=None)
    op.alter_column("voting_sessions", "judge_voting_open", server_default=None)


def downgrade() -> None:
    op.drop_column("voting_sessions", "judge_voting_open")
    op.drop_column("voting_sessions", "public_voting_open")
