"""
Recurring group database model.
"""

import uuid
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import Column, String, Boolean, DateTime, Date, Numeric, Enum, ForeignKey
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class Frequency(str, enum.Enum):
    """Recurring frequency enumeration."""
    weekly = "weekly"
    biweekly = "biweekly"
    monthly = "monthly"
    quarterly = "quarterly"
    yearly = "yearly"


class RecurringGroup(Base):
    """Recurring group model for tracking subscription and regular payments."""

    __tablename__ = "recurring_groups"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    merchant_pattern = Column(String(255), nullable=False)
    expected_amount = Column(Numeric(12, 2), nullable=True)
    amount_variance = Column(Numeric(5, 2), nullable=True)  # Acceptable % variance
    frequency = Column(Enum(Frequency), nullable=False)
    category_id = Column(String(36), ForeignKey("categories.id"), nullable=True)
    last_seen_date = Column(Date, nullable=True)
    next_expected_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    category = relationship("Category", back_populates="recurring_groups")
    transactions = relationship("Transaction", back_populates="recurring_group")
    alerts = relationship("Alert", back_populates="recurring_group")
