"""
Categorization rule database model.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    Boolean,
    Enum,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class MatchField(str, enum.Enum):
    """Field to match against."""

    merchant = "merchant"
    description = "description"
    amount = "amount"


class MatchType(str, enum.Enum):
    """Type of match to perform."""

    contains = "contains"
    exact = "exact"
    starts_with = "starts_with"
    regex = "regex"


class CategorizationRule(Base):
    """Rule for auto-categorizing transactions."""

    __tablename__ = "categorization_rules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    match_field = Column(Enum(MatchField), nullable=False)
    match_type = Column(Enum(MatchType), nullable=False)
    match_value = Column(String(255), nullable=False)
    category_id = Column(String(36), ForeignKey("categories.id"), nullable=False)
    priority = Column(Integer, default=100, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    auto_created = Column(Boolean, default=False, nullable=False)
    match_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    category = relationship("Category", back_populates="rules")
