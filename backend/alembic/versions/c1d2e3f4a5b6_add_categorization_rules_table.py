"""add categorization_rules table

Revision ID: c1d2e3f4a5b6
Revises: 8767341b220f
Create Date: 2026-03-21 18:47:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "c1d2e3f4a5b6"
down_revision = "8767341b220f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "categorization_rules",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "match_field",
            sa.Enum("merchant", "description", "amount", name="matchfield"),
            nullable=False,
        ),
        sa.Column(
            "match_type",
            sa.Enum("contains", "exact", "starts_with", "regex", name="matchtype"),
            nullable=False,
        ),
        sa.Column("match_value", sa.String(length=255), nullable=False),
        sa.Column("category_id", sa.String(length=36), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("auto_created", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("match_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_categorization_rules_priority"),
        "categorization_rules",
        ["priority"],
        unique=False,
    )
    op.create_index(
        op.f("ix_categorization_rules_is_active"),
        "categorization_rules",
        ["is_active"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_categorization_rules_is_active"), table_name="categorization_rules"
    )
    op.drop_index(
        op.f("ix_categorization_rules_priority"), table_name="categorization_rules"
    )
    op.drop_table("categorization_rules")
    op.execute("DROP TYPE IF EXISTS matchtype")
    op.execute("DROP TYPE IF EXISTS matchfield")
