"""
Coach conversation database models.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class MessageRole(str, enum.Enum):
    """Who sent the message."""

    user = "user"
    assistant = "assistant"


class Conversation(Base):
    """A conversation thread with the coach."""

    __tablename__ = "coach_conversations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(200), nullable=True)
    summary = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    last_message_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    is_archived = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index(
            "ix_coach_conversations_archived_updated", "is_archived", "last_message_at"
        ),
    )

    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )


class Message(Base):
    """A single message in a conversation."""

    __tablename__ = "coach_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(
        String(36),
        ForeignKey("coach_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(SQLEnum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index(
            "ix_coach_messages_conversation_created", "conversation_id", "created_at"
        ),
    )

    conversation = relationship("Conversation", back_populates="messages")
