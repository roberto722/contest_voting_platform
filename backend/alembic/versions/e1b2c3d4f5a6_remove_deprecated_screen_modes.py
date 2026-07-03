"""remove deprecated screen modes

Revision ID: e1b2c3d4f5a6
Revises: d6a4f2c9b8e1
Create Date: 2026-06-25 18:10:00.000000
"""

from collections.abc import Sequence

from alembic import op


revision: str = "e1b2c3d4f5a6"
down_revision: str | None = "d6a4f2c9b8e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "UPDATE screen_states SET mode = 'idle' "
        "WHERE mode IN ('show_qr', 'voting_open', 'show_results', 'show_final_winners')"
    )


def downgrade() -> None:
    pass
