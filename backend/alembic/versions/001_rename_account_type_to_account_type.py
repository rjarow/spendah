"""rename account type to account_type

Revision ID: 001
Revises: 
Create Date: 2026-01-09 03:50:00
"""

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    # Rename column type to account_type in accounts table
    op.alter_column('accounts', 'type', new_column_name='account_type')


def downgrade() -> None:
    # Rename back
    op.alter_column('accounts', 'account_type', new_column_name='type')
