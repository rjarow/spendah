"""
Import log database model.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Enum, Text, ForeignKey
import enum
from app.database import Base


class ImportStatus(str, enum.Enum):
    """Import status enumeration."""
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class ImportLog(Base):
    """Import log model for tracking file imports."""

    __tablename__ = "import_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(255), nullable=False)
    account_id = Column(String(36), ForeignKey("accounts.id"), nullable=False)
    status = Column(Enum(ImportStatus), nullable=False, default=ImportStatus.pending)
    transactions_imported = Column(Integer, default=0, nullable=False)
    transactions_skipped = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
