"""expand account types

Revision ID: 85298a57822f
Revises: 3c565fee2ac5
Create Date: 2026-02-05 16:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '85298a57822f'
down_revision = '3c565fee2ac5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Since SQLite doesn't support ALTER TYPE, we need to:
    # 1. Add new column with all account types
    # 2. Copy data to new column
    # 3. Drop old column
    # 4. Rename new column to old column's name

    # Add new column with all account types
    op.add_column('accounts', sa.Column('account_type_new', sa.Text(), nullable=True))

    # Migrate data from old to new column
    op.execute("""
        UPDATE accounts
        SET account_type_new = CASE
            WHEN account_type = 'bank' THEN 'checking'
            WHEN account_type = 'credit' THEN 'credit_card'
            WHEN account_type = 'debit' THEN 'savings'
            ELSE account_type
        END
        WHERE account_type IN ('bank', 'credit', 'debit')
    """)

    # Drop old column
    op.drop_column('accounts', 'account_type')

    # Rename new column to old column's name
    op.alter_column('accounts', 'account_type_new', new_column_name='account_type')


def downgrade() -> None:
    # Revert changes
    # Add new column with all account types
    op.add_column('accounts', sa.Column('account_type_new', sa.Text(), nullable=True))

    # Migrate data from old to new column
    op.execute("""
        UPDATE accounts
        SET account_type_new = CASE
            WHEN account_type = 'checking' THEN 'bank'
            WHEN account_type = 'savings' THEN 'debit'
            WHEN account_type = 'credit_card' THEN 'credit'
            ELSE account_type
        END
        WHERE account_type IN ('checking', 'savings', 'credit_card')
    """)

    # Drop old column
    op.drop_column('accounts', 'account_type')

    # Rename new column to old column's name
    op.alter_column('accounts', 'account_type_new', new_column_name='account_type')
