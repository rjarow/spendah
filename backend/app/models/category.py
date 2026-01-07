"""
Category database model.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Category(Base):
    """Category model with hierarchical support."""

    __tablename__ = "categories"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    parent_id = Column(String(36), ForeignKey("categories.id"), nullable=True)
    color = Column(String(7), nullable=True)  # Hex color
    icon = Column(String(50), nullable=True)
    is_system = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    parent = relationship("Category", remote_side=[id], backref="children")
    transactions = relationship("Transaction", back_populates="category")
    recurring_groups = relationship("RecurringGroup", back_populates="category")
    user_corrections = relationship("UserCorrection", back_populates="category")
