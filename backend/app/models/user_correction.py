"""
User correction database model.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class UserCorrection(Base):
    """User correction model for tracking manual categorization corrections."""

    __tablename__ = "user_corrections"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    raw_description = Column(Text, nullable=False)
    clean_merchant = Column(String(255), nullable=False)
    category_id = Column(String(36), ForeignKey("categories.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    category = relationship("Category", back_populates="user_corrections")
