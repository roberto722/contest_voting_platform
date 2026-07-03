"""add participant voter accounts

Revision ID: b7c9d1e2f3a4
Revises: f3a2b1c0d9e8
Create Date: 2026-06-30 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "b7c9d1e2f3a4"
down_revision: str | None = "f3a2b1c0d9e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "participant_voter_accounts",
        sa.Column("participant_id", sa.String(length=36), nullable=False),
        sa.Column("voter_account_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["voter_account_id"], ["voter_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("participant_id", "voter_account_id"),
    )
    op.execute(
        """
        INSERT INTO participant_voter_accounts (participant_id, voter_account_id)
        SELECT id, voter_account_id
        FROM participants
        WHERE voter_account_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE participants
        SET voter_account_id = (
            SELECT participant_voter_accounts.voter_account_id
            FROM participant_voter_accounts
            WHERE participant_voter_accounts.participant_id = participants.id
            ORDER BY participant_voter_accounts.voter_account_id
            LIMIT 1
        )
        WHERE EXISTS (
            SELECT 1
            FROM participant_voter_accounts
            WHERE participant_voter_accounts.participant_id = participants.id
        )
        """
    )
    op.drop_table("participant_voter_accounts")
