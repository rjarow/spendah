"""
Learned format database model.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Enum, JSON, ForeignKey
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class FileType(str, enum.Enum):
    """File type enumeration."""
    csv = "csv"
    ofx = "ofx"
    qfx = "qfx"


class AmountStyle(str, enum.Enum):
    """Amount style enumeration."""
    signed = "signed"
    separate_columns = "separate_columns"
    parentheses_negative = "parentheses_negative"


class LearnedFormat(Base):
    """Learned format model for storing file import formats."""

    __tablename__ = "learned_formats"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    fingerprint = Column(String(64), nullable=False, index=True)  # Hash of headers/structure
    file_type = Column(Enum(FileType), nullable=False)
    column_mapping = Column(JSON, nullable=False)  # {"date": 0, "amount": 3, ...}
    date_format = Column(String(50), nullable=False)  # strptime format string
    amount_style = Column(Enum(AmountStyle), nullable=False)
    debit_column = Column(Integer, nullable=True)  # If amount_style is separate_columns
    credit_column = Column(Integer, nullable=True)  # If amount_style is separate_columns
    skip_rows = Column(Integer, default=0, nullable=False)
    account_id = Column(String(36), ForeignKey("accounts.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    accounts = relationship("Account", back_populates="learned_format", foreign_keys="Account.learned_format_id")
