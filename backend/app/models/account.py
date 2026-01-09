"""
Account database model.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class AccountType(str, enum.Enum):
    """Account type enumeration."""
    credit = "credit"
    debit = "debit"
    bank = "bank"
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

    # Relationships
    transactions = relationship("Transaction", back_populates="account")
    learned_format = relationship("LearnedFormat", back_populates="accounts", foreign_keys=[learned_format_id])
