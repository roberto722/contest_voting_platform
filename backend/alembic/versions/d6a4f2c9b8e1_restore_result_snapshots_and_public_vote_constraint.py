"""restore result snapshots and public vote constraint

Revision ID: d6a4f2c9b8e1
Revises: 5927e9f9e7d5
Create Date: 2026-06-25 17:30:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "d6a4f2c9b8e1"
down_revision: str | None = "5927e9f9e7d5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "result_snapshots",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("competition_id", sa.String(), nullable=False),
        sa.Column("snapshot_name", sa.String(length=255), nullable=False),
        sa.Column("results_json", sa.JSON(), nullable=False),
        sa.Column("created_by_admin_id", sa.String(length=36), nullable=True),
        sa.Column("is_final", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["competition_id"], ["competitions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_result_snapshots_competition_id"),
        "result_snapshots",
        ["competition_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_result_snapshots_is_final"),
        "result_snapshots",
        ["is_final"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_public_vote_voter_competition_participant_session",
        "public_votes",
        ["voter_account_id", "competition_id", "participant_id", "voting_session_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_public_vote_voter_competition_participant_session",
        "public_votes",
        type_="unique",
    )
    op.drop_index(op.f("ix_result_snapshots_is_final"), table_name="result_snapshots")
    op.drop_index(op.f("ix_result_snapshots_competition_id"), table_name="result_snapshots")
    op.drop_table("result_snapshots")
