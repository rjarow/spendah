"""add task model columns

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-20

"""

from alembic import op
import sqlalchemy as sa

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ai_settings",
        sa.Column("categorize_model", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "ai_settings",
        sa.Column("merchant_clean_model", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "ai_settings",
        sa.Column("format_detect_model", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "ai_settings", sa.Column("coach_model", sa.String(length=100), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("ai_settings", "coach_model")
    op.drop_column("ai_settings", "format_detect_model")
    op.drop_column("ai_settings", "merchant_clean_model")
    op.drop_column("ai_settings", "categorize_model")
