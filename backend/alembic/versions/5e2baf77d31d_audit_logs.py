"""audit logs

Revision ID: 5e2baf77d31d
Revises: 86b7caa82272
Create Date: 2026-06-18 15:10:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "5e2baf77d31d"
down_revision: str | None = "86b7caa82272"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=True),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("actor_id", sa.String(length=36), nullable=True),
        sa.Column("actor_label", sa.String(length=255), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("entity_type", sa.String(length=128), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=True),
        sa.Column("details_json", sa.JSON(), nullable=False),
        sa.Column("ip_hash", sa.String(length=255), nullable=True),
        sa.Column("user_agent_hash", sa.String(length=255), nullable=True),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_event_id"), "audit_logs", ["event_id"], unique=False)
    op.create_index(
        op.f("ix_audit_logs_competition_id"),
        "audit_logs",
        ["competition_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_competition_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_event_id"), table_name="audit_logs")
    op.drop_table("audit_logs")
