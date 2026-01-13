"""Models for PII tokenization."""

from sqlalchemy import Column, Integer, String, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.sql import func
from enum import Enum

from app.database import Base


class TokenType(str, Enum):
    """Types of tokens we create."""
    merchant = "merchant"
    account = "account"
    person = "person"


class TokenMap(Base):
    """Maps original PII values to anonymized tokens."""
    __tablename__ = "token_maps"

    id = Column(Integer, primary_key=True, index=True)
    token_type = Column(SQLEnum(TokenType), nullable=False, index=True)
    original_value = Column(String(500), nullable=False)
    normalized_value = Column(String(500), nullable=False, index=True)
    token = Column(String(50), nullable=False, unique=True, index=True)
    metadata_ = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        {"sqlite_autoincrement": True},
    )


class DateShift(Base):
    """Singleton table storing the random date shift value."""
    __tablename__ = "date_shifts"

    id = Column(Integer, primary_key=True, default=1)
    shift_days = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
