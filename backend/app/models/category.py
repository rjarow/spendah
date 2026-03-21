"""
Category database model.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base


class Category(Base):
    """Category model with hierarchical support."""

    __tablename__ = "categories"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, index=True)
    parent_id = Column(
        String(36),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    color = Column(String(7), nullable=True)
    icon = Column(String(50), nullable=True)
    is_system = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (Index("ix_categories_name_parent", "name", "parent_id"),)

    parent = relationship("Category", remote_side=[id], backref="children")
    transactions = relationship(
        "Transaction", back_populates="category", passive_deletes=True
    )
    recurring_groups = relationship(
        "RecurringGroup", back_populates="category", passive_deletes=True
    )
    user_corrections = relationship(
        "UserCorrection", back_populates="category", passive_deletes=True
    )
    budgets = relationship("Budget", back_populates="category", passive_deletes=True)
