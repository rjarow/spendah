"""AI token usage tracking model."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Index
from app.database import Base


class AITokenUsage(Base):
    """Track AI token usage per call."""

    __tablename__ = "ai_token_usage"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task = Column(String(50), nullable=False, index=True)
    provider = Column(String(50), nullable=False)
    model = Column(String(100), nullable=False)
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (Index("ix_ai_token_usage_task_created", "task", "created_at"),)
