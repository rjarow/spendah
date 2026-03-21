"""make_import_log_account_id_nullable

Revision ID: 8767341b220f
Revises: b2c3d4e5f6a7
Create Date: 2026-03-20 19:06:47.069145

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "8767341b220f"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("import_logs", schema=None) as batch_op:
        batch_op.alter_column("account_id", nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("import_logs", schema=None) as batch_op:
        batch_op.alter_column("account_id", nullable=False)
