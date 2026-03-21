"""add ai_settings table

Revision ID: a1b2c3d4e5f6
Revises: 457488391401
Create Date: 2026-03-20

"""

from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "457488391401"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("openrouter_api_key", sa.String(length=255), nullable=True),
        sa.Column("openai_api_key", sa.String(length=255), nullable=True),
        sa.Column("anthropic_api_key", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("ai_settings")
