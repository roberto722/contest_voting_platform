"""remove_access_method_and_pin

Revision ID: c4c68fac5eaf
Revises: a8d8c3f4e2b0
Create Date: 2026-06-25 15:41:38.806894
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = 'c4c68fac5eaf'
down_revision: str | None = 'a8d8c3f4e2b0'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column('competitions', 'access_pin_hash')
    op.drop_column('competitions', 'access_method')


def downgrade() -> None:
    op.add_column('competitions', sa.Column('access_pin_hash', sa.String(length=255), nullable=True))
    op.add_column('competitions', sa.Column('access_method', sa.Enum('public_link', 'qr_pin', 'private_link', name='accessmethod', native_enum=False), nullable=False, server_default='public_link'))

