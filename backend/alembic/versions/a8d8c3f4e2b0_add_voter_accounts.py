"""add_voter_accounts

Revision ID: a8d8c3f4e2b0
Revises: 9f3cbae8330d
Create Date: 2026-06-24 21:55:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "a8d8c3f4e2b0"
down_revision: str | None = "9f3cbae8330d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create voter_accounts table
    op.create_table(
        "voter_accounts",
        sa.Column("event_id", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column("access_code_hash", sa.String(length=255), nullable=False),
        sa.Column("access_token", sa.String(length=36), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index(op.f("ix_voter_accounts_event_id"), "voter_accounts", ["event_id"], unique=False)
    op.create_index(op.f("ix_voter_accounts_access_token"), "voter_accounts", ["access_token"], unique=True)

    # 2. Add voter_account_id to participants
    op.add_column("participants", sa.Column("voter_account_id", sa.String(), nullable=True))
    op.create_foreign_key(
        "fk_participants_voter_account_id_voter_accounts",
        "participants",
        "voter_accounts",
        ["voter_account_id"],
        ["id"],
        ondelete="SET NULL"
    )
    op.create_index(op.f("ix_participants_voter_account_id"), "participants", ["voter_account_id"], unique=False)
    op.create_unique_constraint(
        "uq_voter_account_competition",
        "participants",
        ["voter_account_id", "competition_id"]
    )

    # 3. Add voter_account_id to public_votes and drop voter_session_id
    op.add_column("public_votes", sa.Column("voter_account_id", sa.String(), nullable=False))
    op.create_foreign_key(
        "fk_public_votes_voter_account_id_voter_accounts",
        "public_votes",
        "voter_accounts",
        ["voter_account_id"],
        ["id"],
        ondelete="CASCADE"
    )
    op.create_index(op.f("ix_public_votes_voter_account_id"), "public_votes", ["voter_account_id"], unique=False)
    
    op.drop_index("ix_public_votes_voter_session_id", table_name="public_votes")
    op.drop_column("public_votes", "voter_session_id")

    # 4. Drop voter_sessions
    op.drop_index("ix_voter_sessions_event_id", table_name="voter_sessions")
    op.drop_index("ix_voter_sessions_voter_token_hash", table_name="voter_sessions")
    op.drop_table("voter_sessions")


def downgrade() -> None:
    # 1. Recreate voter_sessions table
    op.create_table(
        "voter_sessions",
        sa.Column("event_id", sa.String(), nullable=False),
        sa.Column("voter_token_hash", sa.String(length=255), nullable=False),
        sa.Column("ip_hash", sa.String(length=255), nullable=True),
        sa.Column("user_agent_hash", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index(op.f("ix_voter_sessions_event_id"), "voter_sessions", ["event_id"], unique=False)
    op.create_index(op.f("ix_voter_sessions_voter_token_hash"), "voter_sessions", ["voter_token_hash"], unique=False)

    # 2. Add voter_session_id to public_votes and drop voter_account_id
    op.add_column("public_votes", sa.Column("voter_session_id", sa.String(), nullable=True))
    op.create_foreign_key(
        "fk_public_votes_voter_session_id_voter_sessions",
        "public_votes",
        "voter_sessions",
        ["voter_session_id"],
        ["id"],
        ondelete="CASCADE"
    )
    op.create_index(op.f("ix_public_votes_voter_session_id"), "public_votes", ["voter_session_id"], unique=False)
    
    op.drop_index("ix_public_votes_voter_account_id", table_name="public_votes")
    op.drop_column("public_votes", "voter_account_id")

    # 3. Drop voter_account_id and unique constraint from participants
    op.drop_constraint("uq_voter_account_competition", "participants", type_="unique")
    op.drop_index("ix_participants_voter_account_id", table_name="participants")
    op.drop_column("participants", "voter_account_id")

    # 4. Drop voter_accounts table
    op.drop_index("ix_voter_accounts_access_token", table_name="voter_accounts")
    op.drop_index("ix_voter_accounts_event_id", table_name="voter_accounts")
    op.drop_table("voter_accounts")
