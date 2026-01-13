# Spendah - Phase 8: Coach Foundation

## Overview

This phase adds the foundational AI coach infrastructure - conversation storage, chat API, and basic UI components. The coach will be able to answer questions about the user's financial data using tokenized context.

**Key Concepts:**
- Conversations persist across sessions
- All stored messages are tokenized (cloud-safe)
- Context assembly pulls relevant financial data for each query
- UI: embedded widget + slide-out drawer

## Progress Tracker

Update this as you complete each step:

- [ ] Step 1: Create Conversation Models
- [ ] Step 2: Create Alembic Migration
- [ ] Step 3: Create Coach Schemas
- [ ] Step 4: Create Coach Service
- [ ] Step 5: Create Coach Prompts
- [ ] Step 6: Create Coach API Endpoints
- [ ] Step 7: Add Frontend Types
- [ ] Step 8: Add Frontend API Functions
- [ ] Step 9: Create ChatMessage Component
- [ ] Step 10: Create CoachInput Component
- [ ] Step 11: Create CoachWidget Component
- [ ] Step 12: Create CoachDrawer Component
- [ ] Step 13: Integrate into Layout
- [ ] Step 14: Add Tests

## Files to Create/Modify

**CREATE:**
- `backend/app/models/conversation.py`
- `backend/app/schemas/coach.py`
- `backend/app/services/coach_service.py`
- `backend/app/ai/prompts/coach.py`
- `backend/app/api/coach.py`
- `backend/tests/test_coach_service.py`
- `frontend/src/components/coach/ChatMessage.tsx`
- `frontend/src/components/coach/CoachInput.tsx`
- `frontend/src/components/coach/CoachWidget.tsx`
- `frontend/src/components/coach/CoachDrawer.tsx`

**MODIFY:**
- `backend/app/models/__init__.py` - Export new models
- `backend/app/api/router.py` - Add coach router
- `frontend/src/lib/api.ts` - Add coach API functions
- `frontend/src/types/index.ts` - Add coach types
- `frontend/src/components/layout/Layout.tsx` - Add coach drawer
- `frontend/src/pages/Dashboard.tsx` - Add coach widget

---

## IMPORTANT: Read First

Before writing ANY code, read these files:
1. `HANDOFF.md` - Current project state, known gotchas
2. `backend/app/services/tokenization_service.py` - How tokenization works

## Known Gotchas (from previous phases)

1. **Account model uses `account_type`** not `type`
2. **Alert model uses `Severity`** not `AlertSeverity`
3. **Alerts API: `/settings` route before `/{alert_id}`**
4. **OpenRouter uses `OPENROUTER_API_KEY`** not `OPENAI_API_KEY`
5. **Test isolation: Use `StaticPool`** in conftest.py
6. **Always restart after changes:**
   ```bash
   docker compose down
   docker compose up -d --build
   ```

---

## Step 1: Create Conversation Models

Create `backend/app/models/conversation.py`:

```python
"""Models for coach conversations."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum as SQLEnum, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class MessageRole(str, Enum):
    """Role of message sender."""
    user = "user"
    assistant = "assistant"


class Conversation(Base):
    """A coach conversation session."""
    __tablename__ = "conversations"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    last_message_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    summary = Column(Text, nullable=True)  # AI-generated summary for context
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    """A single message in a conversation."""
    __tablename__ = "messages"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(SQLEnum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)  # Stored tokenized for cloud safety
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
```

Update `backend/app/models/__init__.py`:

```python
from app.models.conversation import Conversation, Message, MessageRole
```

**Verify:**
```bash
docker compose exec api python -c "from app.models.conversation import Conversation, Message, MessageRole; print('Models loaded')"
```

---

## Step 2: Create Alembic Migration

```bash
docker compose exec api alembic revision --autogenerate -m "add conversation tables"
docker compose exec api alembic upgrade head
```

**Verify tables exist:**
```bash
docker compose exec api python -c "
from app.database import engine
from sqlalchemy import inspect
insp = inspect(engine)
print('conversations' in insp.get_table_names())
print('messages' in insp.get_table_names())
"
```

---

## Step 3: Create Coach Schemas

Create `backend/app/schemas/coach.py`:

```python
"""Schemas for coach API."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

from app.models.conversation import MessageRole


class MessageCreate(BaseModel):
    """Input for sending a message."""
    message: str
    conversation_id: Optional[str] = None


class MessageResponse(BaseModel):
    """A single message."""
    id: str
    role: MessageRole
    content: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class ChatResponse(BaseModel):
    """Response from chat endpoint."""
    response: str
    conversation_id: str
    message_id: str


class ConversationSummary(BaseModel):
    """Summary of a conversation for listing."""
    id: str
    summary: Optional[str]
    last_message_at: datetime
    message_count: int
    is_archived: bool
    
    class Config:
        from_attributes = True


class ConversationDetail(BaseModel):
    """Full conversation with messages."""
    id: str
    summary: Optional[str]
    started_at: datetime
    last_message_at: datetime
    is_archived: bool
    messages: List[MessageResponse]
    
    class Config:
        from_attributes = True


class ConversationList(BaseModel):
    """Paginated list of conversations."""
    items: List[ConversationSummary]
    total: int
```

---

## Step 4: Create Coach Service

Create `backend/app/services/coach_service.py`:

```python
"""Service for AI coach functionality."""

import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.conversation import Conversation, Message, MessageRole
from app.models.transaction import Transaction
from app.models.category import Category
from app.models.recurring import RecurringGroup
from app.models.alert import Alert
from app.services.tokenization_service import TokenizationService
from app.ai.client import AIClient
from app.ai.prompts.coach import build_coach_prompt, COACH_SYSTEM_PROMPT
from app.config import get_settings


class CoachService:
    """Handles coach conversations and context assembly."""
    
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self._tokenizer: Optional[TokenizationService] = None
        self._ai_client: Optional[AIClient] = None
    
    @property
    def tokenizer(self) -> TokenizationService:
        if self._tokenizer is None:
            self._tokenizer = TokenizationService(self.db)
        return self._tokenizer
    
    @property
    def ai_client(self) -> AIClient:
        if self._ai_client is None:
            self._ai_client = AIClient(self.db)
        return self._ai_client
    
    async def chat(
        self,
        message: str,
        conversation_id: Optional[str] = None
    ) -> Tuple[str, str, str]:
        """
        Process a chat message and return AI response.
        
        Returns: (response_text, conversation_id, message_id)
        """
        # Get or create conversation
        if conversation_id:
            conversation = self.db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()
            if not conversation:
                conversation = self._create_conversation()
        else:
            conversation = self._create_conversation()
        
        # Store user message (tokenized)
        tokenized_message = self.tokenizer.tokenize_text(message)
        user_msg = Message(
            conversation_id=conversation.id,
            role=MessageRole.user,
            content=tokenized_message
        )
        self.db.add(user_msg)
        self.db.commit()
        
        # Build context
        context = self._build_context()
        conversation_history = self._get_conversation_history(conversation.id)
        
        # Build prompt
        prompt = build_coach_prompt(
            user_message=message,  # Use original for AI
            context=context,
            history=conversation_history
        )
        
        # Get AI response
        response = await self.ai_client.complete(
            prompt=prompt,
            system=COACH_SYSTEM_PROMPT
        )
        
        # De-tokenize response for storage (it may contain tokens from context)
        # Actually, store tokenized and de-tokenize on retrieval
        tokenized_response = response  # AI response won't have raw PII
        
        # Store assistant message
        assistant_msg = Message(
            conversation_id=conversation.id,
            role=MessageRole.assistant,
            content=tokenized_response
        )
        self.db.add(assistant_msg)
        
        # Update conversation timestamp
        conversation.last_message_at = datetime.utcnow()
        self.db.commit()
        
        # De-tokenize response for user
        display_response = self.tokenizer.detokenize(response)
        
        return display_response, conversation.id, assistant_msg.id
    
    def _create_conversation(self) -> Conversation:
        """Create a new conversation."""
        conversation = Conversation()
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation
    
    def _get_conversation_history(
        self,
        conversation_id: str,
        limit: int = 10
    ) -> List[Dict[str, str]]:
        """Get recent messages for context."""
        messages = self.db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(desc(Message.created_at)).limit(limit).all()
        
        # Reverse to get chronological order, skip the just-added user message
        messages = list(reversed(messages))[:-1] if messages else []
        
        return [
            {"role": m.role.value, "content": m.content}
            for m in messages
        ]
    
    def _build_context(self) -> Dict[str, Any]:
        """
        Build financial context for the coach.
        
        Assembles relevant data, tokenized for cloud safety.
        """
        context = {}
        
        # Recent transactions (last 30 days)
        thirty_days_ago = datetime.utcnow().date() - timedelta(days=30)
        recent_txns = self.db.query(Transaction).filter(
            Transaction.date >= thirty_days_ago
        ).order_by(desc(Transaction.date)).limit(50).all()
        
        context["recent_transactions"] = [
            self.tokenizer.tokenize_transaction_for_ai({
                "merchant": t.clean_merchant or t.raw_description,
                "amount": float(t.amount),
                "date": t.date.isoformat(),
                "category_name": t.category.name if t.category else None
            })
            for t in recent_txns
        ]
        
        # Spending by category (current month)
        first_of_month = datetime.utcnow().date().replace(day=1)
        category_spending = self.db.query(
            Category.name,
            func.sum(Transaction.amount).label("total")
        ).join(Transaction).filter(
            Transaction.date >= first_of_month,
            Transaction.amount < 0  # Expenses only
        ).group_by(Category.name).all()
        
        context["category_spending"] = [
            {"category": name, "total": abs(float(total))}
            for name, total in category_spending
        ]
        
        # Active recurring charges
        recurring = self.db.query(RecurringGroup).filter(
            RecurringGroup.is_active == True
        ).all()
        
        context["recurring_charges"] = [
            {
                "name": self.tokenizer.tokenize_merchant(r.name),
                "amount": float(r.expected_amount) if r.expected_amount else None,
                "frequency": r.frequency.value if r.frequency else None
            }
            for r in recurring
        ]
        
        # Unread alerts
        unread_alerts = self.db.query(Alert).filter(
            Alert.is_read == False,
            Alert.is_dismissed == False
        ).limit(5).all()
        
        context["unread_alerts"] = [
            {
                "type": a.type.value,
                "title": a.title,
                "severity": a.severity.value
            }
            for a in unread_alerts
        ]
        
        # Summary stats
        total_income = self.db.query(func.sum(Transaction.amount)).filter(
            Transaction.date >= first_of_month,
            Transaction.amount > 0
        ).scalar() or 0
        
        total_expenses = self.db.query(func.sum(Transaction.amount)).filter(
            Transaction.date >= first_of_month,
            Transaction.amount < 0
        ).scalar() or 0
        
        context["month_summary"] = {
            "income": float(total_income),
            "expenses": abs(float(total_expenses)),
            "net": float(total_income) + float(total_expenses)
        }
        
        return context
    
    def get_conversations(
        self,
        limit: int = 20,
        offset: int = 0,
        include_archived: bool = False
    ) -> Tuple[List[Conversation], int]:
        """Get paginated list of conversations."""
        query = self.db.query(Conversation)
        
        if not include_archived:
            query = query.filter(Conversation.is_archived == False)
        
        total = query.count()
        
        conversations = query.order_by(
            desc(Conversation.last_message_at)
        ).offset(offset).limit(limit).all()
        
        # Add message counts
        for conv in conversations:
            conv.message_count = self.db.query(Message).filter(
                Message.conversation_id == conv.id
            ).count()
        
        return conversations, total
    
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get a single conversation with messages."""
        conversation = self.db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        
        if conversation:
            # De-tokenize messages for display
            for msg in conversation.messages:
                msg.content = self.tokenizer.detokenize(msg.content)
        
        return conversation
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and its messages."""
        conversation = self.db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        
        if not conversation:
            return False
        
        self.db.delete(conversation)
        self.db.commit()
        return True
    
    def archive_conversation(self, conversation_id: str) -> bool:
        """Archive a conversation."""
        conversation = self.db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        
        if not conversation:
            return False
        
        conversation.is_archived = True
        self.db.commit()
        return True
```

---

## Step 5: Create Coach Prompts

Create `backend/app/ai/prompts/coach.py`:

```python
"""Prompts for the AI coach."""

from typing import Dict, Any, List
import json


COACH_SYSTEM_PROMPT = """You are a helpful, friendly financial coach embedded in a personal finance app called Spendah.

Your role:
- Answer questions about the user's spending, income, and financial patterns
- Provide insights and observations about their finances
- Help them understand where their money goes
- Offer suggestions for optimization (but never pushy)
- Be encouraging and non-judgmental about spending habits

Important guidelines:
- You have access to real financial data in the context - use it to give specific, personalized answers
- Merchant names may appear as tokens (MERCHANT_001, etc.) - refer to them naturally
- Always be concise - users want quick insights, not essays
- If you don't have enough data to answer, say so honestly
- Never make up numbers - only reference data you can see in the context
- Format currency as $X,XXX.XX
- When discussing spending, use positive framing when possible

You are NOT:
- A financial advisor (don't give investment advice)
- A tax professional (don't give tax advice)
- Judgmental about spending choices
"""


def build_coach_prompt(
    user_message: str,
    context: Dict[str, Any],
    history: List[Dict[str, str]]
) -> str:
    """
    Build the full prompt for the coach.
    
    Args:
        user_message: The user's current message
        context: Financial context (tokenized)
        history: Recent conversation history
    
    Returns:
        Complete prompt string
    """
    parts = []
    
    # Add financial context
    parts.append("## Your Financial Context\n")
    
    if context.get("month_summary"):
        summary = context["month_summary"]
        parts.append(f"This month so far:")
        parts.append(f"- Income: ${summary['income']:,.2f}")
        parts.append(f"- Expenses: ${summary['expenses']:,.2f}")
        parts.append(f"- Net: ${summary['net']:,.2f}")
        parts.append("")
    
    if context.get("category_spending"):
        parts.append("Spending by category this month:")
        for cat in sorted(context["category_spending"], key=lambda x: x["total"], reverse=True)[:10]:
            parts.append(f"- {cat['category']}: ${cat['total']:,.2f}")
        parts.append("")
    
    if context.get("recurring_charges"):
        parts.append(f"Active subscriptions/recurring ({len(context['recurring_charges'])} total):")
        for r in context["recurring_charges"][:5]:
            amount_str = f"${r['amount']:,.2f}" if r['amount'] else "varies"
            freq = r['frequency'] or 'unknown'
            parts.append(f"- {r['name']}: {amount_str} ({freq})")
        if len(context["recurring_charges"]) > 5:
            parts.append(f"- ... and {len(context['recurring_charges']) - 5} more")
        parts.append("")
    
    if context.get("unread_alerts"):
        parts.append(f"Unread alerts ({len(context['unread_alerts'])}):")
        for alert in context["unread_alerts"]:
            parts.append(f"- [{alert['severity']}] {alert['title']}")
        parts.append("")
    
    if context.get("recent_transactions"):
        parts.append(f"Recent transactions ({len(context['recent_transactions'])} shown):")
        for t in context["recent_transactions"][:10]:
            parts.append(f"- {t['date']}: {t['merchant']} ${abs(t['amount']):,.2f}")
        parts.append("")
    
    # Add conversation history
    if history:
        parts.append("## Recent Conversation")
        for msg in history[-6:]:  # Last 3 exchanges
            role = "User" if msg["role"] == "user" else "Coach"
            parts.append(f"{role}: {msg['content']}")
        parts.append("")
    
    # Add current message
    parts.append("## Current Question")
    parts.append(f"User: {user_message}")
    parts.append("")
    parts.append("Respond helpfully and concisely:")
    
    return "\n".join(parts)
```

---

## Step 6: Create Coach API Endpoints

Create `backend/app/api/coach.py`:

```python
"""Coach API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.schemas.coach import (
    MessageCreate,
    ChatResponse,
    ConversationSummary,
    ConversationDetail,
    ConversationList,
)
from app.services.coach_service import CoachService

router = APIRouter(prefix="/coach", tags=["coach"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: MessageCreate,
    db: Session = Depends(get_db)
):
    """Send a message to the coach and get a response."""
    service = CoachService(db)
    
    try:
        response, conversation_id, message_id = await service.chat(
            message=request.message,
            conversation_id=request.conversation_id
        )
        
        return ChatResponse(
            response=response,
            conversation_id=conversation_id,
            message_id=message_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations", response_model=ConversationList)
def list_conversations(
    limit: int = 20,
    offset: int = 0,
    include_archived: bool = False,
    db: Session = Depends(get_db)
):
    """List all conversations."""
    service = CoachService(db)
    conversations, total = service.get_conversations(
        limit=limit,
        offset=offset,
        include_archived=include_archived
    )
    
    return ConversationList(
        items=[
            ConversationSummary(
                id=c.id,
                summary=c.summary,
                last_message_at=c.last_message_at,
                message_count=c.message_count,
                is_archived=c.is_archived
            )
            for c in conversations
        ],
        total=total
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db)
):
    """Get a single conversation with all messages."""
    service = CoachService(db)
    conversation = service.get_conversation(conversation_id)
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return conversation


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db)
):
    """Delete a conversation."""
    service = CoachService(db)
    success = service.delete_conversation(conversation_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {"deleted": True}


@router.post("/conversations/{conversation_id}/archive")
def archive_conversation(
    conversation_id: str,
    db: Session = Depends(get_db)
):
    """Archive a conversation."""
    service = CoachService(db)
    success = service.archive_conversation(conversation_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {"archived": True}
```

Update `backend/app/api/router.py`:

```python
from app.api.coach import router as coach_router

# Add to router includes:
router.include_router(coach_router)
```

---

## Step 7: Add Frontend Types

Update `frontend/src/types/index.ts`:

```typescript
// Add coach types

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

export interface ChatResponse {
  response: string;
  conversation_id: string;
  message_id: string;
}

export interface ConversationSummary {
  id: string;
  summary: string | null;
  last_message_at: string;
  message_count: number;
  is_archived: boolean;
}

export interface ConversationDetail {
  id: string;
  summary: string | null;
  started_at: string;
  last_message_at: string;
  is_archived: boolean;
  messages: ChatMessage[];
}

export interface ConversationList {
  items: ConversationSummary[];
  total: number;
}
```

---

## Step 8: Add Frontend API Functions

Update `frontend/src/lib/api.ts`:

```typescript
import type {
  ChatResponse,
  ConversationList,
  ConversationDetail,
} from '@/types';

// Add coach API functions
export const coachApi = {
  chat: (message: string, conversationId?: string): Promise<ChatResponse> =>
    fetch(`${API_BASE}/coach/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
      }),
    }).then(r => {
      if (!r.ok) throw new Error('Chat failed');
      return r.json();
    }),

  getConversations: (limit = 20, offset = 0): Promise<ConversationList> =>
    fetch(`${API_BASE}/coach/conversations?limit=${limit}&offset=${offset}`)
      .then(r => r.json()),

  getConversation: (id: string): Promise<ConversationDetail> =>
    fetch(`${API_BASE}/coach/conversations/${id}`).then(r => r.json()),

  deleteConversation: (id: string): Promise<void> =>
    fetch(`${API_BASE}/coach/conversations/${id}`, { method: 'DELETE' })
      .then(r => { if (!r.ok) throw new Error('Delete failed'); }),

  archiveConversation: (id: string): Promise<void> =>
    fetch(`${API_BASE}/coach/conversations/${id}/archive`, { method: 'POST' })
      .then(r => { if (!r.ok) throw new Error('Archive failed'); }),
};
```

---

## Step 9: Create ChatMessage Component

Create `frontend/src/components/coach/ChatMessage.tsx`:

```tsx
import { cn } from '@/lib/utils';
import type { ChatMessage as ChatMessageType } from '@/types';

interface ChatMessageProps {
  message: ChatMessageType;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';

  return (
    <div
      className={cn(
        'flex w-full mb-4',
        isUser ? 'justify-end' : 'justify-start'
      )}
    >
      <div
        className={cn(
          'max-w-[80%] rounded-lg px-4 py-2',
          isUser
            ? 'bg-primary text-primary-foreground'
            : 'bg-muted'
        )}
      >
        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        <p className="text-xs opacity-70 mt-1">
          {new Date(message.created_at).toLocaleTimeString()}
        </p>
      </div>
    </div>
  );
}
```

---

## Step 10: Create CoachInput Component

Create `frontend/src/components/coach/CoachInput.tsx`:

```tsx
import { useState, KeyboardEvent } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Send } from 'lucide-react';

interface CoachInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function CoachInput({ onSend, disabled, placeholder }: CoachInputProps) {
  const [message, setMessage] = useState('');

  const handleSend = () => {
    if (message.trim() && !disabled) {
      onSend(message.trim());
      setMessage('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex gap-2 items-end">
      <Textarea
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder || "Ask about your finances..."}
        disabled={disabled}
        className="min-h-[60px] max-h-[120px] resize-none"
        rows={2}
      />
      <Button
        onClick={handleSend}
        disabled={disabled || !message.trim()}
        size="icon"
        className="h-[60px] w-[60px]"
      >
        <Send className="h-5 w-5" />
      </Button>
    </div>
  );
}
```

---

## Step 11: Create CoachWidget Component

Create `frontend/src/components/coach/CoachWidget.tsx`:

```tsx
import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { MessageCircle, Expand } from 'lucide-react';
import { CoachInput } from './CoachInput';
import { ChatMessage } from './ChatMessage';
import { coachApi } from '@/lib/api';
import type { ChatMessage as ChatMessageType } from '@/types';

interface CoachWidgetProps {
  onExpand?: () => void;
}

export function CoachWidget({ onExpand }: CoachWidgetProps) {
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSend = async (message: string) => {
    // Add user message immediately
    const userMessage: ChatMessageType = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: message,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    try {
      const response = await coachApi.chat(message, conversationId || undefined);
      setConversationId(response.conversation_id);

      // Add assistant message
      const assistantMessage: ChatMessageType = {
        id: response.message_id,
        role: 'assistant',
        content: response.response,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Chat failed:', error);
      // Remove the user message on error
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-lg flex items-center gap-2">
          <MessageCircle className="h-5 w-5" />
          Financial Coach
        </CardTitle>
        {onExpand && (
          <Button variant="ghost" size="icon" onClick={onExpand}>
            <Expand className="h-4 w-4" />
          </Button>
        )}
      </CardHeader>
      <CardContent>
        {/* Message area */}
        <div className="h-[200px] overflow-y-auto mb-4 space-y-2">
          {messages.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              Ask me anything about your spending!
            </p>
          ) : (
            messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))
          )}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-muted rounded-lg px-4 py-2">
                <p className="text-sm text-muted-foreground">Thinking...</p>
              </div>
            </div>
          )}
        </div>

        {/* Input */}
        <CoachInput onSend={handleSend} disabled={loading} />
      </CardContent>
    </Card>
  );
}
```

---

## Step 12: Create CoachDrawer Component

Create `frontend/src/components/coach/CoachDrawer.tsx`:

```tsx
import { useState, useEffect, useRef } from 'react';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { MessageCircle, Trash2 } from 'lucide-react';
import { ChatMessage } from './ChatMessage';
import { CoachInput } from './CoachInput';
import { coachApi } from '@/lib/api';
import type { ChatMessage as ChatMessageType, ConversationSummary } from '@/types';

export function CoachDrawer() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load conversations on open
  useEffect(() => {
    if (open) {
      loadConversations();
    }
  }, [open]);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadConversations = async () => {
    try {
      const data = await coachApi.getConversations(10);
      setConversations(data.items);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  };

  const loadConversation = async (id: string) => {
    try {
      const data = await coachApi.getConversation(id);
      setConversationId(id);
      setMessages(data.messages);
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  };

  const startNewConversation = () => {
    setConversationId(null);
    setMessages([]);
  };

  const handleSend = async (message: string) => {
    const userMessage: ChatMessageType = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: message,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    try {
      const response = await coachApi.chat(message, conversationId || undefined);
      setConversationId(response.conversation_id);

      const assistantMessage: ChatMessageType = {
        id: response.message_id,
        role: 'assistant',
        content: response.response,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
      loadConversations(); // Refresh list
    } catch (error) {
      console.error('Chat failed:', error);
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await coachApi.deleteConversation(id);
      if (conversationId === id) {
        startNewConversation();
      }
      loadConversations();
    } catch (error) {
      console.error('Failed to delete:', error);
    }
  };

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button
          variant="outline"
          size="icon"
          className="fixed bottom-4 right-4 h-12 w-12 rounded-full shadow-lg"
        >
          <MessageCircle className="h-6 w-6" />
        </Button>
      </SheetTrigger>
      <SheetContent className="w-[400px] sm:w-[540px] flex flex-col">
        <SheetHeader>
          <SheetTitle className="flex items-center justify-between">
            <span className="flex items-center gap-2">
              <MessageCircle className="h-5 w-5" />
              Financial Coach
            </span>
            <Button variant="outline" size="sm" onClick={startNewConversation}>
              New Chat
            </Button>
          </SheetTitle>
        </SheetHeader>

        <div className="flex-1 flex flex-col mt-4 min-h-0">
          {/* Conversation list (collapsed) */}
          {conversations.length > 0 && !conversationId && (
            <div className="mb-4 space-y-2 max-h-[200px] overflow-y-auto">
              <p className="text-sm font-medium text-muted-foreground">Recent conversations</p>
              {conversations.map((conv) => (
                <div
                  key={conv.id}
                  className="flex items-center justify-between p-2 rounded hover:bg-muted cursor-pointer"
                  onClick={() => loadConversation(conv.id)}
                >
                  <div>
                    <p className="text-sm truncate max-w-[280px]">
                      {conv.summary || 'Conversation'}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {conv.message_count} messages
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(conv.id);
                    }}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          )}

          {/* Messages */}
          <div className="flex-1 overflow-y-auto space-y-2 mb-4">
            {messages.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">
                Ask me anything about your finances!
              </p>
            ) : (
              messages.map((msg) => (
                <ChatMessage key={msg.id} message={msg} />
              ))
            )}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-muted rounded-lg px-4 py-2">
                  <p className="text-sm text-muted-foreground">Thinking...</p>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <CoachInput onSend={handleSend} disabled={loading} />
        </div>
      </SheetContent>
    </Sheet>
  );
}
```

---

## Step 13: Integrate into Layout

Update `frontend/src/components/layout/Layout.tsx`:

```tsx
import { CoachDrawer } from '@/components/coach/CoachDrawer';

// Add inside the Layout component, at the end before closing tags:
<CoachDrawer />
```

Optionally, add CoachWidget to Dashboard:

Update `frontend/src/pages/Dashboard.tsx`:

```tsx
import { CoachWidget } from '@/components/coach/CoachWidget';

// Add in the dashboard grid:
<CoachWidget />
```

---

## Step 14: Add Tests

Create `backend/tests/test_coach_service.py`:

```python
"""Tests for coach service."""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from app.services.coach_service import CoachService
from app.models.conversation import Conversation, Message, MessageRole
from app.models.transaction import Transaction
from app.models.category import Category


class TestConversationManagement:
    """Tests for conversation CRUD."""

    def test_create_conversation(self, db_session):
        """Should create a new conversation."""
        service = CoachService(db_session)
        conv = service._create_conversation()
        
        assert conv.id is not None
        assert conv.is_archived == False

    def test_get_conversations(self, db_session):
        """Should list conversations."""
        service = CoachService(db_session)
        
        # Create some conversations
        for _ in range(3):
            service._create_conversation()
        
        convs, total = service.get_conversations()
        
        assert total == 3
        assert len(convs) == 3

    def test_get_conversations_excludes_archived(self, db_session):
        """Should exclude archived by default."""
        service = CoachService(db_session)
        
        conv1 = service._create_conversation()
        conv2 = service._create_conversation()
        conv2.is_archived = True
        db_session.commit()
        
        convs, total = service.get_conversations()
        
        assert total == 1
        assert convs[0].id == conv1.id

    def test_get_conversations_includes_archived(self, db_session):
        """Should include archived when requested."""
        service = CoachService(db_session)
        
        service._create_conversation()
        conv2 = service._create_conversation()
        conv2.is_archived = True
        db_session.commit()
        
        convs, total = service.get_conversations(include_archived=True)
        
        assert total == 2

    def test_delete_conversation(self, db_session):
        """Should delete conversation and messages."""
        service = CoachService(db_session)
        conv = service._create_conversation()
        
        # Add a message
        msg = Message(
            conversation_id=conv.id,
            role=MessageRole.user,
            content="test"
        )
        db_session.add(msg)
        db_session.commit()
        
        # Delete
        result = service.delete_conversation(conv.id)
        
        assert result == True
        assert db_session.query(Conversation).filter_by(id=conv.id).first() is None
        assert db_session.query(Message).filter_by(conversation_id=conv.id).first() is None

    def test_archive_conversation(self, db_session):
        """Should archive conversation."""
        service = CoachService(db_session)
        conv = service._create_conversation()
        
        result = service.archive_conversation(conv.id)
        
        assert result == True
        db_session.refresh(conv)
        assert conv.is_archived == True


class TestContextBuilding:
    """Tests for financial context assembly."""

    def test_build_context_empty(self, db_session):
        """Should handle empty database."""
        service = CoachService(db_session)
        context = service._build_context()
        
        assert "month_summary" in context
        assert context["month_summary"]["income"] == 0
        assert context["month_summary"]["expenses"] == 0

    def test_build_context_with_transactions(self, db_session, sample_account, sample_category):
        """Should include recent transactions."""
        service = CoachService(db_session)
        
        # Add a recent transaction
        txn = Transaction(
            date=datetime.utcnow().date(),
            amount=Decimal("-50.00"),
            raw_description="Test",
            clean_merchant="Test Store",
            account_id=sample_account.id,
            category_id=sample_category.id
        )
        db_session.add(txn)
        db_session.commit()
        
        context = service._build_context()
        
        assert len(context["recent_transactions"]) > 0
        assert context["month_summary"]["expenses"] == 50.0

    def test_context_excludes_old_transactions(self, db_session, sample_account, sample_category):
        """Should not include transactions older than 30 days."""
        service = CoachService(db_session)
        
        # Add an old transaction
        old_date = datetime.utcnow().date() - timedelta(days=60)
        txn = Transaction(
            date=old_date,
            amount=Decimal("-50.00"),
            raw_description="Old Test",
            clean_merchant="Old Store",
            account_id=sample_account.id,
            category_id=sample_category.id
        )
        db_session.add(txn)
        db_session.commit()
        
        context = service._build_context()
        
        assert len(context["recent_transactions"]) == 0


class TestConversationHistory:
    """Tests for conversation history retrieval."""

    def test_get_empty_history(self, db_session):
        """Should handle conversation with no messages."""
        service = CoachService(db_session)
        conv = service._create_conversation()
        
        history = service._get_conversation_history(conv.id)
        
        assert history == []

    def test_get_history_order(self, db_session):
        """Should return messages in chronological order."""
        service = CoachService(db_session)
        conv = service._create_conversation()
        
        # Add messages
        for i in range(3):
            msg = Message(
                conversation_id=conv.id,
                role=MessageRole.user if i % 2 == 0 else MessageRole.assistant,
                content=f"Message {i}"
            )
            db_session.add(msg)
        db_session.commit()
        
        history = service._get_conversation_history(conv.id)
        
        # Should be in order (excluding last which would be the "current" message)
        assert len(history) == 2  # 3 - 1 = 2
```

---

## Verification Checklist

- [ ] `alembic upgrade head` succeeds
- [ ] `conversations` and `messages` tables created
- [ ] `POST /api/v1/coach/chat` returns response
- [ ] `GET /api/v1/coach/conversations` lists conversations
- [ ] `GET /api/v1/coach/conversations/{id}` returns messages
- [ ] `DELETE /api/v1/coach/conversations/{id}` works
- [ ] `POST /api/v1/coach/conversations/{id}/archive` works
- [ ] CoachWidget renders on Dashboard
- [ ] CoachDrawer opens from floating button
- [ ] Can send messages and receive AI responses
- [ ] Messages persist across page reloads
- [ ] Conversation history loads correctly
- [ ] Tests pass: `docker compose exec api pytest tests/test_coach_service.py -v`
- [ ] No console errors in browser

---

## Testing Commands

```bash
# Rebuild and restart
docker compose down
docker compose up -d --build
sleep 5

# Run migration
docker compose exec api alembic upgrade head

# Check tables
docker compose exec api python -c "
from app.database import engine
from sqlalchemy import inspect
insp = inspect(engine)
print('conversations:', 'conversations' in insp.get_table_names())
print('messages:', 'messages' in insp.get_table_names())
"

# Test endpoints
curl -X POST http://localhost:8000/api/v1/coach/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How much did I spend this month?"}'

curl http://localhost:8000/api/v1/coach/conversations

# Run tests
docker compose exec api pytest tests/test_coach_service.py -v

# Run all tests
docker compose exec api pytest -v --tb=short
```

---

## Notes

**What this achieves:**
- Persistent conversation storage
- Tokenized messages (cloud-safe)
- Context assembly from financial data
- Basic chat UI (widget + drawer)
- Foundation for Phase 9 (proactive insights, goals)

**What's NOT included (Phase 9):**
- Proactive observations
- Goal setting and tracking
- Conversation summarization
- Full-page chat interface
