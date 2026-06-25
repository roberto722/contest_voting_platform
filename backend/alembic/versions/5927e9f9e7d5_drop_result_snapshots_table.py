"""drop result snapshots table

Revision ID: 5927e9f9e7d5
Revises: c4c68fac5eaf
Create Date: 2026-06-25 16:28:31.279217
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = '5927e9f9e7d5'
down_revision: str | None = 'c4c68fac5eaf'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("result_snapshots")


def downgrade() -> None:
    op.create_table(
        "result_snapshots",
        sa.Column("id", sa.String(36), sa.ForeignKey("competitions.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("competition_id", sa.String(36), nullable=False),
        sa.Column("snapshot_name", sa.String(255), nullable=False),
        sa.Column("results_json", sa.JSON(), nullable=False),
        sa.Column("created_by_admin_id", sa.String(36)),
        sa.Column("is_final", sa.Boolean(), nullable=False, default=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
