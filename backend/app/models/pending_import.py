"""
Pending import staging model.

Stores in-flight import state in SQLite so it survives restarts.
Replaces the old in-memory PENDING_IMPORTS dict.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text
from app.database import Base


class PendingImport(Base):
    """Staging table for import state between upload and confirm."""

    __tablename__ = "pending_imports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_path = Column(Text, nullable=False)
    filename = Column(String(255), nullable=False)
    parser_type = Column(String(50), nullable=False)
    data_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
