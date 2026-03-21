"""add ai_token_usage table

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-03-21 19:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "e3f4a5b6c7d8"
down_revision = "d2e3f4a5b6c7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_token_usage",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("task", sa.String(length=50), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "completion_tokens", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ai_token_usage_task"), "ai_token_usage", ["task"], unique=False
    )
    op.create_index(
        op.f("ix_ai_token_usage_created_at"),
        "ai_token_usage",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_ai_token_usage_task_created",
        "ai_token_usage",
        ["task", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ai_token_usage_task_created", table_name="ai_token_usage")
    op.drop_index(op.f("ix_ai_token_usage_created_at"), table_name="ai_token_usage")
    op.drop_index(op.f("ix_ai_token_usage_task"), table_name="ai_token_usage")
    op.drop_table("ai_token_usage")
