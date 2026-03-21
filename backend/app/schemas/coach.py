"""
Coach conversation schemas.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    user = "user"
    assistant = "assistant"


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    message_id: str

    class Config:
        from_attributes = True


class MessageOut(BaseModel):
    id: str
    role: MessageRole
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationSummary(BaseModel):
    id: str
    title: Optional[str]
    summary: Optional[str]
    last_message_at: datetime
    message_count: int
    is_archived: bool

    class Config:
        from_attributes = True


class ConversationDetail(BaseModel):
    id: str
    title: Optional[str]
    summary: Optional[str]
    started_at: datetime
    last_message_at: datetime
    is_archived: bool
    messages: List[MessageOut]

    class Config:
        from_attributes = True


class ConversationList(BaseModel):
    items: List[ConversationSummary]
    total: int

    class Config:
        from_attributes = True


class ContextData(BaseModel):
    recent_spending: dict
    recurring_charges: List[dict]
    alerts_summary: dict
    account_balances: List[dict]
    month_comparison: dict


class QuickQuestion(BaseModel):
    id: str
    text: str
    category: str
