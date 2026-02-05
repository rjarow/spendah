"""
Account database model.
"""

import uuid
from decimal import Decimal
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Enum, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class AccountType(str, enum.Enum):
    """Account type enumeration."""
    checking = "checking"
    savings = "savings"
    credit_card = "credit_card"
    investment = "investment"
    loan = "loan"
    mortgage = "mortgage"
    cash = "cash"
    other = "other"


class Account(Base):
    """Account model."""

    __tablename__ = "accounts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    account_type = Column(Enum(AccountType), nullable=False)
    learned_format_id = Column(String(36), ForeignKey("learned_formats.id"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    current_balance = Column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    balance_updated_at = Column(DateTime, nullable=True)

    # Relationships
    transactions = relationship("Transaction", back_populates="account")
    learned_format = relationship("LearnedFormat", back_populates="accounts", foreign_keys=[learned_format_id])
    balance_history = relationship("BalanceHistory", back_populates="account", cascade="all, delete-orphan")

    @property
    def is_asset(self) -> bool:
        """Determine if account is an asset (positive in net worth)."""
        asset_types = {
            AccountType.checking,
            AccountType.savings,
            AccountType.investment,
            AccountType.cash
        }
        return self.account_type in asset_types
