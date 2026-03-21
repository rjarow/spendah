"""add llm_prompt to categories

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-03-21 18:47:00.000001

"""

from alembic import op
import sqlalchemy as sa


revision = "d2e3f4a5b6c7"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("categories", schema=None) as batch_op:
        batch_op.add_column(sa.Column("llm_prompt", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("categories", schema=None) as batch_op:
        batch_op.drop_column("llm_prompt")
