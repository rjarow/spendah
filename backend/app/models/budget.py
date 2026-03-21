"""
Budget database model.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    Enum,
    Index,
)
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class BudgetPeriod(str, enum.Enum):
    """Budget period enumeration."""

    weekly = "weekly"
    monthly = "monthly"
    yearly = "yearly"


class Budget(Base):
    """Budget model for tracking spending limits."""

    __tablename__ = "budgets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    category_id = Column(
        String(36),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    amount = Column(Numeric(10, 2), nullable=False)
    period = Column(Enum(BudgetPeriod), nullable=False)
    start_date = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, nullable=True)

    __table_args__ = (Index("ix_budgets_active_category", "is_active", "category_id"),)

    category = relationship("Category", back_populates="budgets")
