# Spendah - Phase 8: Coach Foundation

## Overview

This phase adds the foundation for an AI coach that can have conversations about the user's finances. The coach has read access to all financial data (tokenized for cloud AI) and can answer questions, provide insights, and remember past conversations.

**Key Concepts:**
- Conversations stored tokenized for privacy
- Context assembly from financial data before each AI call
- Streaming responses for better UX
- Embedded widget on dashboard + drawer accessible from any page

## Progress Tracker

Update this as you complete each step:

- [ ] Step 1: Create Coach Models
- [ ] Step 2: Create Coach Schemas
- [ ] Step 3: Create Coach Service
- [ ] Step 4: Create Coach Prompts
- [ ] Step 5: Create Coach API Endpoints
- [ ] Step 6: Add Coach Types to Frontend
- [ ] Step 7: Create Coach API Functions
- [ ] Step 8: Create Chat Message Component
- [ ] Step 9: Create Coach Widget (Dashboard)
- [ ] Step 10: Create Coach Drawer (Global)
- [ ] Step 11: Integrate Coach into Layout
- [ ] Step 12: Add Tests
- [ ] Step 13: Final Testing & Verification

## Files to Create/Modify

**CREATE:**
- `backend/app/models/coach.py`
- `backend/app/schemas/coach.py`
- `backend/app/services/coach_service.py`
- `backend/app/ai/prompts/coach.py`
- `backend/app/api/coach.py`
- `backend/tests/test_coach_service.py`
- `frontend/src/components/coach/ChatMessage.tsx`
- `frontend/src/components/coach/CoachWidget.tsx`
- `frontend/src/components/coach/CoachDrawer.tsx`
- `frontend/src/components/coach/CoachInput.tsx`
- `frontend/src/hooks/useCoach.ts`

**MODIFY:**
- `backend/app/models/__init__.py` - Export new models
- `backend/app/api/router.py` - Add coach router
- `frontend/src/lib/api.ts` - Add coach API functions
- `frontend/src/types/index.ts` - Add coach types
- `frontend/src/pages/Dashboard.tsx` - Add coach widget
- `frontend/src/components/layout/Layout.tsx` - Add coach drawer trigger

---

## IMPORTANT: Read First

Before writing ANY code, read these files:
1. `HANDOFF.md` - Current project state
2. `spendah-spec.md` - Architecture with coach details (search for "Coach")

## Known Gotchas (from previous phases)

1. **Account model uses `account_type`** not `type`
2. **Alert model uses `Severity`** not `AlertSeverity`
3. **OpenRouter uses `OPENROUTER_API_KEY`** not `OPENAI_API_KEY`
4. **Dynamic API URL** - use `${window.location.hostname}` not hardcoded localhost
5. **Always restart after changes:**
   ```bash
   docker compose down
   docker compose up -d --build
   ```

---

## Step 1: Create Coach Models

Create `backend/app/models/coach.py`:

```python
"""Models for coach conversations."""

from sqlalchemy import Column, String, Text, DateTime, Boolean, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum
import uuid

from app.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class MessageRole(str, Enum):
    """Who sent the message."""
    user = "user"
    assistant = "assistant"


class Conversation(Base):
    """A coach conversation session."""
    __tablename__ = "coach_conversations"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(200), nullable=True)  # Auto-generated from first message
    summary = Column(Text, nullable=True)  # AI-generated summary for context
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    last_message_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    """A single message in a conversation."""
    __tablename__ = "coach_messages"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    conversation_id = Column(String(36), ForeignKey("coach_conversations.id"), nullable=False)
    role = Column(SQLEnum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)  # Stored tokenized for privacy
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
```

Update `backend/app/models/__init__.py`:

```python
from app.models.coach import Conversation, Message, MessageRole
```

Create Alembic migration:
```bash
docker compose exec api alembic revision --autogenerate -m "add coach conversation tables"
docker compose exec api alembic upgrade head
```

**Verify:**
```bash
docker compose exec api python -c "from app.models.coach import Conversation, Message; print('Models loaded')"
```

---

## Step 2: Create Coach Schemas

Create `backend/app/schemas/coach.py`:

```python
"""Schemas for coach API."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    user = "user"
    assistant = "assistant"


class MessageCreate(BaseModel):
    """Send a message to the coach."""
    content: str = Field(..., min_length=1, max_length=4000)
    conversation_id: Optional[str] = None  # None = start new conversation


class MessageResponse(BaseModel):
    """A single message."""
    id: str
    role: MessageRole
    content: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class ConversationSummary(BaseModel):
    """Summary for conversation list."""
    id: str
    title: Optional[str]
    last_message_at: datetime
    message_count: int
    preview: str  # First ~100 chars of last message
    
    class Config:
        from_attributes = True


class ConversationDetail(BaseModel):
    """Full conversation with messages."""
    id: str
    title: Optional[str]
    summary: Optional[str]
    started_at: datetime
    last_message_at: datetime
    is_archived: bool
    messages: List[MessageResponse]
    
    class Config:
        from_attributes = True


class ChatResponse(BaseModel):
    """Response from sending a chat message."""
    conversation_id: str
    message: MessageResponse
    

class ConversationList(BaseModel):
    """Paginated list of conversations."""
    items: List[ConversationSummary]
    total: int
    has_more: bool
```

---

## Step 3: Create Coach Service

Create `backend/app/services/coach_service.py`:

```python
"""Service for coach conversations and AI interaction."""

from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.models.coach import Conversation, Message, MessageRole
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
    
    @property
    def tokenizer(self) -> TokenizationService:
        if self._tokenizer is None:
            self._tokenizer = TokenizationService(self.db)
        return self._tokenizer
    
    async def chat(
        self,
        content: str,
        conversation_id: Optional[str] = None
    ) -> tuple[Conversation, Message]:
        """
        Send a message to the coach and get a response.
        
        Returns: (conversation, assistant_message)
        """
        # Get or create conversation
        if conversation_id:
            conversation = self.db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()
            if not conversation:
                raise ValueError(f"Conversation {conversation_id} not found")
        else:
            conversation = Conversation()
            self.db.add(conversation)
            self.db.flush()
        
        # Tokenize user message before storing
        tokenized_content = self._tokenize_message(content)
        
        # Save user message
        user_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.user,
            content=tokenized_content
        )
        self.db.add(user_message)
        
        # Build context and get AI response
        context = self._build_financial_context()
        history = self._get_conversation_history(conversation.id)
        
        ai_response = await self._get_ai_response(
            user_message=content,  # Send original for better AI understanding
            context=context,
            history=history
        )
        
        # Tokenize AI response before storing (in case it mentions specific merchants)
        tokenized_response = self._tokenize_message(ai_response)
        
        # Save assistant message
        assistant_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.assistant,
            content=tokenized_response
        )
        self.db.add(assistant_message)
        
        # Update conversation title if first message
        if not conversation.title:
            conversation.title = self._generate_title(content)
        
        conversation.last_message_at = datetime.utcnow()
        self.db.commit()
        
        # Detokenize for response to user
        assistant_message.content = self.tokenizer.detokenize(assistant_message.content)
        
        return conversation, assistant_message
    
    def get_conversations(
        self,
        limit: int = 20,
        offset: int = 0,
        include_archived: bool = False
    ) -> tuple[List[Conversation], int]:
        """Get list of conversations with pagination."""
        query = self.db.query(Conversation)
        
        if not include_archived:
            query = query.filter(Conversation.is_archived == False)
        
        total = query.count()
        
        conversations = query.order_by(
            desc(Conversation.last_message_at)
        ).offset(offset).limit(limit).all()
        
        return conversations, total
    
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation with all messages."""
        conversation = self.db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        
        if conversation:
            # Detokenize all messages for display
            for msg in conversation.messages:
                msg.content = self.tokenizer.detokenize(msg.content)
        
        return conversation
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation."""
        conversation = self.db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        
        if not conversation:
            return False
        
        self.db.delete(conversation)
        self.db.commit()
        return True
    
    def archive_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Archive a conversation."""
        conversation = self.db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        
        if conversation:
            conversation.is_archived = True
            self.db.commit()
        
        return conversation
    
    def _tokenize_message(self, content: str) -> str:
        """Tokenize PII in a message."""
        if not self.settings.privacy_obfuscation_enabled:
            return content
        
        # Tokenize any merchant names that appear in the message
        # This is a simple approach - could be enhanced with NER
        return self.tokenizer.tokenize_description(content)
    
    def _build_financial_context(self) -> Dict[str, Any]:
        """Build context from user's financial data for the AI."""
        today = date.today()
        month_start = today.replace(day=1)
        last_month_start = (month_start - timedelta(days=1)).replace(day=1)
        
        # Current month spending by category
        current_spending = self._get_spending_by_category(month_start, today)
        
        # Last month spending for comparison
        last_spending = self._get_spending_by_category(last_month_start, month_start - timedelta(days=1))
        
        # Recent transactions (last 10)
        recent_txns = self.db.query(Transaction).order_by(
            desc(Transaction.date)
        ).limit(10).all()
        
        # Active recurring charges
        recurring = self.db.query(RecurringGroup).filter(
            RecurringGroup.is_active == True
        ).all()
        
        # Unread alerts
        alerts = self.db.query(Alert).filter(
            Alert.is_read == False,
            Alert.is_dismissed == False
        ).order_by(desc(Alert.created_at)).limit(5).all()
        
        # Tokenize all the data
        context = {
            "current_month": month_start.strftime("%B %Y"),
            "spending_this_month": self._tokenize_spending(current_spending),
            "spending_last_month": self._tokenize_spending(last_spending),
            "recent_transactions": [
                self.tokenizer.tokenize_transaction_for_ai({
                    "merchant": t.clean_merchant,
                    "amount": float(t.amount),
                    "date": t.date,
                    "category_name": t.category.name if t.category else None
                })
                for t in recent_txns
            ],
            "recurring_charges": [
                {
                    "name": self.tokenizer.tokenize_merchant(r.name),
                    "amount": float(r.expected_amount) if r.expected_amount else None,
                    "frequency": r.frequency.value if r.frequency else "monthly"
                }
                for r in recurring
            ],
            "pending_alerts": len(alerts),
            "total_monthly_recurring": sum(
                float(r.expected_amount or 0) for r in recurring
                if r.frequency and r.frequency.value == "monthly"
            )
        }
        
        return context
    
    def _get_spending_by_category(self, start: date, end: date) -> Dict[str, Decimal]:
        """Get spending totals by category for a date range."""
        results = self.db.query(
            Category.name,
            func.sum(Transaction.amount).label('total')
        ).join(
            Transaction, Transaction.category_id == Category.id
        ).filter(
            Transaction.date >= start,
            Transaction.date <= end,
            Transaction.amount < 0  # Expenses only
        ).group_by(Category.name).all()
        
        return {name: abs(total) for name, total in results}
    
    def _tokenize_spending(self, spending: Dict[str, Decimal]) -> Dict[str, float]:
        """Convert spending dict to serializable format."""
        return {cat: float(amount) for cat, amount in spending.items()}
    
    def _get_conversation_history(self, conversation_id: str) -> List[Dict[str, str]]:
        """Get recent message history for context."""
        messages = self.db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at).all()
        
        # Return last 10 messages for context
        return [
            {"role": m.role.value, "content": m.content}
            for m in messages[-10:]
        ]
    
    async def _get_ai_response(
        self,
        user_message: str,
        context: Dict[str, Any],
        history: List[Dict[str, str]]
    ) -> str:
        """Get response from AI."""
        ai_client = AIClient(self.db)
        
        # Build the prompt with context
        prompt = build_coach_prompt(user_message, context, history)
        
        response = await ai_client.complete(
            prompt=prompt,
            system=COACH_SYSTEM_PROMPT
        )
        
        return response
    
    def _generate_title(self, first_message: str) -> str:
        """Generate a title from the first message."""
        # Simple approach: first 50 chars
        title = first_message[:50]
        if len(first_message) > 50:
            title += "..."
        return title
```

---

## Step 4: Create Coach Prompts

Create `backend/app/ai/prompts/coach.py`:

```python
"""Prompts for the financial coach."""

from typing import Dict, Any, List
import json


COACH_SYSTEM_PROMPT = """You are a friendly, knowledgeable financial coach. You have access to the user's spending data, recurring charges, and financial patterns.

Your role:
- Answer questions about their finances clearly and accurately
- Provide insights and observations without being preachy
- Be encouraging but honest
- Use specific numbers from their data when relevant
- Keep responses concise unless they ask for detail

Style:
- Conversational and warm, like a helpful friend who's good with money
- Never lecture or moralize
- Acknowledge their choices without judgment
- Use casual language, not corporate finance-speak

Important:
- Merchant names may appear as tokens like MERCHANT_001 - refer to them naturally
- You can see their spending patterns but not their bank balances
- Don't give specific investment advice - you're a spending coach, not a financial advisor
- If asked about something outside your data, be honest that you don't have that information
"""


def build_coach_prompt(
    user_message: str,
    context: Dict[str, Any],
    history: List[Dict[str, str]]
) -> str:
    """
    Build the full prompt with financial context.
    """
    # Format context section
    context_section = f"""## Current Financial Context

**{context['current_month']}**

Spending this month by category:
{_format_spending(context['spending_this_month'])}

Last month's spending:
{_format_spending(context['spending_last_month'])}

Recent transactions:
{_format_transactions(context['recent_transactions'])}

Active subscriptions/recurring: {len(context['recurring_charges'])} totaling ${context['total_monthly_recurring']:.2f}/month

Pending alerts: {context['pending_alerts']}
"""
    
    # Format conversation history
    history_section = ""
    if history:
        history_section = "\n## Recent Conversation\n"
        for msg in history[-6:]:  # Last 6 messages for context
            role = "User" if msg['role'] == 'user' else "Coach"
            history_section += f"\n{role}: {msg['content']}\n"
    
    # Build full prompt
    prompt = f"""{context_section}
{history_section}
## Current Question

User: {user_message}

Provide a helpful, friendly response based on their financial data."""
    
    return prompt


def _format_spending(spending: Dict[str, float]) -> str:
    """Format spending dict as readable text."""
    if not spending:
        return "No spending recorded yet"
    
    lines = []
    sorted_spending = sorted(spending.items(), key=lambda x: x[1], reverse=True)
    for category, amount in sorted_spending[:8]:  # Top 8 categories
        lines.append(f"- {category}: ${amount:.2f}")
    
    total = sum(spending.values())
    lines.append(f"\nTotal: ${total:.2f}")
    
    return "\n".join(lines)


def _format_transactions(transactions: List[Dict]) -> str:
    """Format recent transactions."""
    if not transactions:
        return "No recent transactions"
    
    lines = []
    for t in transactions[:5]:  # Show 5 most recent
        merchant = t.get('merchant', 'Unknown')
        amount = t.get('amount', 0)
        date = t.get('date', '')
        lines.append(f"- {date}: {merchant} ${abs(amount):.2f}")
    
    return "\n".join(lines)
```

---

## Step 5: Create Coach API Endpoints

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
    MessageResponse,
    ConversationSummary,
    ConversationDetail,
    ConversationList,
)
from app.services.coach_service import CoachService

router = APIRouter(prefix="/coach", tags=["coach"])


@router.post("/chat", response_model=ChatResponse)
async def send_message(
    message: MessageCreate,
    db: Session = Depends(get_db)
):
    """Send a message to the coach and get a response."""
    service = CoachService(db)
    
    try:
        conversation, response_message = await service.chat(
            content=message.content,
            conversation_id=message.conversation_id
        )
        
        return ChatResponse(
            conversation_id=conversation.id,
            message=MessageResponse(
                id=response_message.id,
                role=response_message.role,
                content=response_message.content,
                created_at=response_message.created_at
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Coach error: {str(e)}")


@router.get("/conversations", response_model=ConversationList)
def list_conversations(
    limit: int = 20,
    offset: int = 0,
    include_archived: bool = False,
    db: Session = Depends(get_db)
):
    """Get list of conversations."""
    service = CoachService(db)
    conversations, total = service.get_conversations(
        limit=limit,
        offset=offset,
        include_archived=include_archived
    )
    
    items = []
    for conv in conversations:
        last_message = conv.messages[-1] if conv.messages else None
        preview = ""
        if last_message:
            preview = service.tokenizer.detokenize(last_message.content)[:100]
        
        items.append(ConversationSummary(
            id=conv.id,
            title=conv.title,
            last_message_at=conv.last_message_at,
            message_count=len(conv.messages),
            preview=preview
        ))
    
    return ConversationList(
        items=items,
        total=total,
        has_more=offset + limit < total
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db)
):
    """Get a conversation with all messages."""
    service = CoachService(db)
    conversation = service.get_conversation(conversation_id)
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        summary=conversation.summary,
        started_at=conversation.started_at,
        last_message_at=conversation.last_message_at,
        is_archived=conversation.is_archived,
        messages=[
            MessageResponse(
                id=m.id,
                role=m.role,
                content=m.content,
                created_at=m.created_at
            )
            for m in conversation.messages
        ]
    )


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db)
):
    """Delete a conversation."""
    service = CoachService(db)
    
    if not service.delete_conversation(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {"status": "deleted"}


@router.post("/conversations/{conversation_id}/archive")
def archive_conversation(
    conversation_id: str,
    db: Session = Depends(get_db)
):
    """Archive a conversation."""
    service = CoachService(db)
    conversation = service.archive_conversation(conversation_id)
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {"status": "archived"}
```

Update `backend/app/api/router.py`:

```python
from app.api.coach import router as coach_router

# Add to router includes:
router.include_router(coach_router)
```

---

## Step 6: Add Coach Types to Frontend

Update `frontend/src/types/index.ts`:

```typescript
// Coach types
export type MessageRole = 'user' | 'assistant';

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  created_at: string;
}

export interface ConversationSummary {
  id: string;
  title: string | null;
  last_message_at: string;
  message_count: number;
  preview: string;
}

export interface ConversationDetail {
  id: string;
  title: string | null;
  summary: string | null;
  started_at: string;
  last_message_at: string;
  is_archived: boolean;
  messages: Message[];
}

export interface ChatResponse {
  conversation_id: string;
  message: Message;
}

export interface ConversationList {
  items: ConversationSummary[];
  total: number;
  has_more: boolean;
}
```

---

## Step 7: Create Coach API Functions

Update `frontend/src/lib/api.ts`:

```typescript
// Coach API
export const coachApi = {
  chat: (content: string, conversationId?: string) =>
    fetch(`${API_BASE}/coach/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        content, 
        conversation_id: conversationId 
      }),
    }).then(r => r.json()) as Promise<ChatResponse>,

  getConversations: (limit = 20, offset = 0) =>
    fetch(`${API_BASE}/coach/conversations?limit=${limit}&offset=${offset}`)
      .then(r => r.json()) as Promise<ConversationList>,

  getConversation: (id: string) =>
    fetch(`${API_BASE}/coach/conversations/${id}`)
      .then(r => r.json()) as Promise<ConversationDetail>,

  deleteConversation: (id: string) =>
    fetch(`${API_BASE}/coach/conversations/${id}`, { method: 'DELETE' })
      .then(r => r.json()),

  archiveConversation: (id: string) =>
    fetch(`${API_BASE}/coach/conversations/${id}/archive`, { method: 'POST' })
      .then(r => r.json()),
};
```

---

## Step 8: Create Chat Message Component

Create `frontend/src/components/coach/ChatMessage.tsx`:

```tsx
import { cn } from '@/lib/utils';
import type { Message } from '@/types';

interface ChatMessageProps {
  message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';

  return (
    <div
      className={cn(
        'flex w-full',
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
        <span className="text-xs opacity-60 mt-1 block">
          {new Date(message.created_at).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit'
          })}
        </span>
      </div>
    </div>
  );
}
```

---

## Step 9: Create Coach Input Component

Create `frontend/src/components/coach/CoachInput.tsx`:

```tsx
import { useState, KeyboardEvent } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Send, Loader2 } from 'lucide-react';

interface CoachInputProps {
  onSend: (message: string) => void;
  isLoading?: boolean;
  placeholder?: string;
}

export function CoachInput({ onSend, isLoading, placeholder }: CoachInputProps) {
  const [input, setInput] = useState('');

  const handleSend = () => {
    if (input.trim() && !isLoading) {
      onSend(input.trim());
      setInput('');
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
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder || "Ask about your spending..."}
        className="min-h-[60px] max-h-[120px] resize-none"
        disabled={isLoading}
      />
      <Button
        onClick={handleSend}
        disabled={!input.trim() || isLoading}
        size="icon"
        className="h-[60px] w-[60px]"
      >
        {isLoading ? (
          <Loader2 className="h-5 w-5 animate-spin" />
        ) : (
          <Send className="h-5 w-5" />
        )}
      </Button>
    </div>
  );
}
```

---

## Step 10: Create Coach Widget (Dashboard)

Create `frontend/src/components/coach/CoachWidget.tsx`:

```tsx
import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { MessageSquare, Maximize2 } from 'lucide-react';
import { ChatMessage } from './ChatMessage';
import { CoachInput } from './CoachInput';
import { coachApi } from '@/lib/api';
import type { Message } from '@/types';

interface CoachWidgetProps {
  onExpand?: () => void;
}

export function CoachWidget({ onExpand }: CoachWidgetProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSend = async (content: string) => {
    // Optimistically add user message
    const userMessage: Message = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await coachApi.chat(content, conversationId || undefined);
      setConversationId(response.conversation_id);
      setMessages((prev) => [...prev, response.message]);
    } catch (error) {
      console.error('Coach error:', error);
      // Remove optimistic message on error
      setMessages((prev) => prev.filter((m) => m.id !== userMessage.id));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card className="h-[400px] flex flex-col">
      <CardHeader className="flex-shrink-0 pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <MessageSquare className="h-5 w-5" />
            Financial Coach
          </CardTitle>
          {onExpand && (
            <Button variant="ghost" size="icon" onClick={onExpand}>
              <Maximize2 className="h-4 w-4" />
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col overflow-hidden">
        {/* Messages area */}
        <div className="flex-1 overflow-y-auto space-y-3 mb-3">
          {messages.length === 0 ? (
            <div className="text-center text-muted-foreground py-8">
              <p className="text-sm">Ask me anything about your spending!</p>
              <p className="text-xs mt-2">Try: "How much did I spend on dining?"</p>
            </div>
          ) : (
            messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))
          )}
        </div>

        {/* Input */}
        <div className="flex-shrink-0">
          <CoachInput
            onSend={handleSend}
            isLoading={isLoading}
            placeholder="Ask about your spending..."
          />
        </div>
      </CardContent>
    </Card>
  );
}
```

---

## Step 11: Create Coach Drawer (Global)

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
import { ScrollArea } from '@/components/ui/scroll-area';
import { MessageSquare, History, Plus } from 'lucide-react';
import { ChatMessage } from './ChatMessage';
import { CoachInput } from './CoachInput';
import { coachApi } from '@/lib/api';
import type { Message, ConversationSummary } from '@/types';

export function CoachDrawer() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Load conversation history when drawer opens
  useEffect(() => {
    if (open && conversations.length === 0) {
      loadConversations();
    }
  }, [open]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
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
      setMessages(data.messages);
      setConversationId(id);
      setShowHistory(false);
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  };

  const startNewConversation = () => {
    setMessages([]);
    setConversationId(null);
    setShowHistory(false);
  };

  const handleSend = async (content: string) => {
    const userMessage: Message = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await coachApi.chat(content, conversationId || undefined);
      setConversationId(response.conversation_id);
      setMessages((prev) => [...prev, response.message]);
      // Refresh conversation list
      loadConversations();
    } catch (error) {
      console.error('Coach error:', error);
      setMessages((prev) => prev.filter((m) => m.id !== userMessage.id));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button
          variant="outline"
          size="icon"
          className="fixed bottom-4 right-4 h-14 w-14 rounded-full shadow-lg"
        >
          <MessageSquare className="h-6 w-6" />
        </Button>
      </SheetTrigger>
      <SheetContent className="w-[400px] sm:w-[540px] flex flex-col">
        <SheetHeader>
          <div className="flex items-center justify-between">
            <SheetTitle className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5" />
              Financial Coach
            </SheetTitle>
            <div className="flex gap-1">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setShowHistory(!showHistory)}
              >
                <History className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={startNewConversation}
              >
                <Plus className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </SheetHeader>

        {showHistory ? (
          <ScrollArea className="flex-1 mt-4">
            <div className="space-y-2">
              {conversations.map((conv) => (
                <button
                  key={conv.id}
                  onClick={() => loadConversation(conv.id)}
                  className="w-full text-left p-3 rounded-lg hover:bg-muted transition-colors"
                >
                  <p className="font-medium truncate">
                    {conv.title || 'Untitled conversation'}
                  </p>
                  <p className="text-sm text-muted-foreground truncate">
                    {conv.preview}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {new Date(conv.last_message_at).toLocaleDateString()}
                  </p>
                </button>
              ))}
              {conversations.length === 0 && (
                <p className="text-center text-muted-foreground py-8">
                  No conversations yet
                </p>
              )}
            </div>
          </ScrollArea>
        ) : (
          <>
            {/* Messages */}
            <ScrollArea className="flex-1 mt-4" ref={scrollRef}>
              <div className="space-y-3 pr-4">
                {messages.length === 0 ? (
                  <div className="text-center text-muted-foreground py-8">
                    <p>Ask me anything about your finances!</p>
                    <div className="mt-4 space-y-2">
                      <p className="text-sm">Try asking:</p>
                      <button
                        onClick={() => handleSend('How much did I spend this month?')}
                        className="block w-full text-sm p-2 rounded bg-muted hover:bg-muted/80"
                      >
                        "How much did I spend this month?"
                      </button>
                      <button
                        onClick={() => handleSend('What are my biggest expenses?')}
                        className="block w-full text-sm p-2 rounded bg-muted hover:bg-muted/80"
                      >
                        "What are my biggest expenses?"
                      </button>
                      <button
                        onClick={() => handleSend('Any subscriptions I should review?')}
                        className="block w-full text-sm p-2 rounded bg-muted hover:bg-muted/80"
                      >
                        "Any subscriptions I should review?"
                      </button>
                    </div>
                  </div>
                ) : (
                  messages.map((msg) => (
                    <ChatMessage key={msg.id} message={msg} />
                  ))
                )}
              </div>
            </ScrollArea>

            {/* Input */}
            <div className="mt-4">
              <CoachInput onSend={handleSend} isLoading={isLoading} />
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}
```

---

## Step 12: Integrate Coach into Layout

Update `frontend/src/components/layout/Layout.tsx` to include the coach drawer:

```tsx
import { CoachDrawer } from '@/components/coach/CoachDrawer';

// Add at the end of the Layout component, just before the closing fragment:
<CoachDrawer />
```

Update `frontend/src/pages/Dashboard.tsx` to include the coach widget:

```tsx
import { CoachWidget } from '@/components/coach/CoachWidget';

// Add in the dashboard grid, perhaps in the right column:
<CoachWidget />
```

---

## Step 13: Add Tests

Create `backend/tests/test_coach_service.py`:

```python
"""Tests for coach service."""

import pytest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.coach_service import CoachService
from app.models.coach import Conversation, Message, MessageRole
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.account import Account, AccountType


class TestCoachService:
    """Tests for CoachService."""
    
    def test_create_conversation(self, db_session):
        """Should create a new conversation."""
        service = CoachService(db_session)
        
        # Create conversation directly
        conv = Conversation(title="Test")
        db_session.add(conv)
        db_session.commit()
        
        assert conv.id is not None
        assert conv.title == "Test"
    
    def test_get_conversations_empty(self, db_session):
        """Should return empty list when no conversations."""
        service = CoachService(db_session)
        
        convs, total = service.get_conversations()
        
        assert convs == []
        assert total == 0
    
    def test_get_conversations_returns_recent_first(self, db_session):
        """Should return conversations in reverse chronological order."""
        service = CoachService(db_session)
        
        # Create conversations
        conv1 = Conversation(title="First")
        conv2 = Conversation(title="Second")
        db_session.add_all([conv1, conv2])
        db_session.commit()
        
        convs, total = service.get_conversations()
        
        assert total == 2
        assert convs[0].title == "Second"  # Most recent first
    
    def test_get_conversation_not_found(self, db_session):
        """Should return None for non-existent conversation."""
        service = CoachService(db_session)
        
        result = service.get_conversation("nonexistent")
        
        assert result is None
    
    def test_delete_conversation(self, db_session):
        """Should delete conversation and messages."""
        service = CoachService(db_session)
        
        # Create conversation with message
        conv = Conversation(title="To Delete")
        db_session.add(conv)
        db_session.flush()
        
        msg = Message(
            conversation_id=conv.id,
            role=MessageRole.user,
            content="Hello"
        )
        db_session.add(msg)
        db_session.commit()
        
        conv_id = conv.id
        
        # Delete
        result = service.delete_conversation(conv_id)
        
        assert result == True
        assert db_session.query(Conversation).filter_by(id=conv_id).first() is None
    
    def test_delete_conversation_not_found(self, db_session):
        """Should return False for non-existent conversation."""
        service = CoachService(db_session)
        
        result = service.delete_conversation("nonexistent")
        
        assert result == False
    
    def test_archive_conversation(self, db_session):
        """Should archive conversation."""
        service = CoachService(db_session)
        
        conv = Conversation(title="To Archive")
        db_session.add(conv)
        db_session.commit()
        
        result = service.archive_conversation(conv.id)
        
        assert result is not None
        assert result.is_archived == True
    
    def test_generate_title(self, db_session):
        """Should generate title from first message."""
        service = CoachService(db_session)
        
        short_title = service._generate_title("Hello")
        assert short_title == "Hello"
        
        long_message = "This is a very long message that should be truncated to fifty characters"
        long_title = service._generate_title(long_message)
        assert len(long_title) == 53  # 50 + "..."
        assert long_title.endswith("...")
    
    def test_get_spending_by_category(self, db_session):
        """Should calculate spending totals by category."""
        service = CoachService(db_session)
        
        # Create test data
        account = Account(name="Test", account_type=AccountType.checking)
        db_session.add(account)
        db_session.flush()
        
        category = Category(name="Food", color="#000", icon="utensils")
        db_session.add(category)
        db_session.flush()
        
        txn = Transaction(
            date=date.today(),
            amount=Decimal("-50.00"),
            raw_description="Test",
            clean_merchant="Test",
            account_id=account.id,
            category_id=category.id
        )
        db_session.add(txn)
        db_session.commit()
        
        result = service._get_spending_by_category(date.today(), date.today())
        
        assert "Food" in result
        assert result["Food"] == Decimal("50.00")
    
    def test_excludes_archived_by_default(self, db_session):
        """Should exclude archived conversations by default."""
        service = CoachService(db_session)
        
        conv1 = Conversation(title="Active")
        conv2 = Conversation(title="Archived", is_archived=True)
        db_session.add_all([conv1, conv2])
        db_session.commit()
        
        convs, total = service.get_conversations(include_archived=False)
        
        assert total == 1
        assert convs[0].title == "Active"
    
    def test_includes_archived_when_requested(self, db_session):
        """Should include archived conversations when requested."""
        service = CoachService(db_session)
        
        conv1 = Conversation(title="Active")
        conv2 = Conversation(title="Archived", is_archived=True)
        db_session.add_all([conv1, conv2])
        db_session.commit()
        
        convs, total = service.get_conversations(include_archived=True)
        
        assert total == 2
```

---

## Step 14: Final Testing & Verification

```bash
# Full rebuild
cd ~/projects/spendah
docker compose down
docker compose up -d --build
sleep 5

# Check for errors
docker compose logs api --tail 50

# Run migrations
docker compose exec api alembic upgrade head

# Test new endpoints
curl http://localhost:8000/api/v1/coach/conversations
curl -X POST http://localhost:8000/api/v1/coach/chat \
  -H "Content-Type: application/json" \
  -d '{"content": "How much did I spend this month?"}'

# Run coach tests
docker compose exec api pytest tests/test_coach_service.py -v

# Run all tests
docker compose exec api pytest -v --tb=short
```

**Test in UI:**
1. Go to Dashboard - should see Coach widget
2. Click floating chat button (bottom right) - should open drawer
3. Send a message - should get AI response
4. Click history icon - should see conversation list
5. Start new conversation - should clear messages
6. Close and reopen - should persist conversation

---

## Verification Checklist

- [ ] `GET /api/v1/coach/conversations` returns list
- [ ] `POST /api/v1/coach/chat` creates conversation and returns response
- [ ] `GET /api/v1/coach/conversations/{id}` returns full conversation
- [ ] `DELETE /api/v1/coach/conversations/{id}` deletes conversation
- [ ] `POST /api/v1/coach/conversations/{id}/archive` archives conversation
- [ ] Coach widget appears on Dashboard
- [ ] Coach drawer opens from floating button
- [ ] Messages display correctly (user right, assistant left)
- [ ] Conversation history shows in drawer
- [ ] New conversation button works
- [ ] Quick suggestion buttons work
- [ ] AI responses include actual financial data
- [ ] Messages are tokenized in database
- [ ] Coach tests pass
- [ ] No console errors

---

## Notes

**What this achieves:**
- Foundation for conversational AI coach
- Privacy-preserving message storage (tokenized)
- Context-aware responses using actual financial data
- Persistent conversation history
- Accessible from any page via drawer

**Phase 9 will add:**
- Proactive observations (coach notices things)
- Goal setting and tracking
- Memory across conversations
- Full chat page for extended conversations
