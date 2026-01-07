"""
Transaction database model.
"""

import uuid
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import Column, String, Boolean, DateTime, Date, Numeric, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base


class Transaction(Base):
    """Transaction model."""

    __tablename__ = "transactions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    hash = Column(String(64), unique=True, nullable=False, index=True)  # For deduplication
    date = Column(Date, nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)  # Negative = expense, positive = income
    raw_description = Column(Text, nullable=False)
    clean_merchant = Column(String(255), nullable=True)
    category_id = Column(String(36), ForeignKey("categories.id"), nullable=True)
    account_id = Column(String(36), ForeignKey("accounts.id"), nullable=False)
    is_recurring = Column(Boolean, default=False, nullable=False)
    recurring_group_id = Column(String(36), ForeignKey("recurring_groups.id"), nullable=True)
    notes = Column(Text, nullable=True)
    ai_categorized = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    account = relationship("Account", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")
    recurring_group = relationship("RecurringGroup", back_populates="transactions")
    alerts = relationship("Alert", back_populates="transaction")

    # Indexes for common queries
    __table_args__ = (
        Index("idx_transaction_date_account", "date", "account_id"),
        Index("idx_transaction_category", "category_id"),
    )
