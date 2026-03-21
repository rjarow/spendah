"""add coach conversation tables

Revision ID: 457488391401
Revises: 85298a57822f
Create Date: 2026-03-20 13:29:06.845955

"""

from alembic import op
import sqlalchemy as sa


revision = "457488391401"
down_revision = "85298a57822f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "coach_conversations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.Column(
            "last_message_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_coach_conversations_archived_updated",
        "coach_conversations",
        ["is_archived", "last_message_at"],
        unique=False,
    )
    op.create_index(
        "ix_coach_conversations_is_archived",
        "coach_conversations",
        ["is_archived"],
        unique=False,
    )

    op.create_table(
        "coach_messages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column(
            "role", sa.Enum("user", "assistant", name="messagerole"), nullable=False
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["coach_conversations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_coach_messages_conversation_created",
        "coach_messages",
        ["conversation_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_coach_messages_conversation_id",
        "coach_messages",
        ["conversation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_coach_messages_conversation_id", table_name="coach_messages")
    op.drop_index("ix_coach_messages_conversation_created", table_name="coach_messages")
    op.drop_table("coach_messages")
    op.drop_index(
        "ix_coach_conversations_is_archived", table_name="coach_conversations"
    )
    op.drop_index(
        "ix_coach_conversations_archived_updated", table_name="coach_conversations"
    )
    op.drop_table("coach_conversations")
