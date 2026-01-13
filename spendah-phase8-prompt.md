# Spendah - Phase 8: Coach Foundation

## Overview

This phase builds the foundation for the AI Coach - a conversational interface that understands your financial data and can answer questions, provide insights, and eventually set goals. Phase 8 focuses on the core infrastructure; Phase 9 will add proactive observations and goal tracking.

**Key Concepts:**
- Conversations are stored tokenized (privacy-safe)
- Context assembly pulls relevant financial data for each query
- The coach sees tokenized data but responses are de-tokenized for display
- Embedded widget provides quick access from any page

## Progress Tracker

Update this as you complete each step:

- [ ] Step 1: Create Coach Models
- [ ] Step 2: Create Coach Schemas
- [ ] Step 3: Create Coach Prompts
- [ ] Step 4: Create Coach Service
- [ ] Step 5: Create Coach API Endpoints
- [ ] Step 6: Add Frontend Types and API Functions
- [ ] Step 7: Create Coach Widget Component
- [ ] Step 8: Create Coach Drawer Component
- [ ] Step 9: Integrate Coach into Layout
- [ ] Step 10: Add Tests
- [ ] Step 11: Final Testing & Verification

## Files to Create/Modify

**CREATE:**
- `backend/app/models/conversation.py`
- `backend/app/schemas/coach.py`
- `backend/app/ai/prompts/coach.py`
- `backend/app/services/coach_service.py`
- `backend/app/api/coach.py`
- `backend/tests/test_coach_service.py`
- `frontend/src/components/coach/CoachWidget.tsx`
- `frontend/src/components/coach/CoachDrawer.tsx`
- `frontend/src/components/coach/ChatMessage.tsx`
- `frontend/src/pages/Coach.tsx`

**MODIFY:**
- `backend/app/models/__init__.py` - Export new models
- `backend/app/api/router.py` - Add coach router
- `frontend/src/lib/api.ts` - Add coach API functions
- `frontend/src/types/index.ts` - Add coach types
- `frontend/src/components/layout/Layout.tsx` - Add coach widget
- `frontend/src/App.tsx` - Add coach route

---

## IMPORTANT: Read First

Before writing ANY code, read these files:
1. `handoff-slim.md` - Current project state
2. `spendah-spec.md` - Full architecture with Coach section

## Known Gotchas (from previous phases)

1. **Account model uses `account_type`** not `type`
2. **Alert routes**: Put `/settings` before `/{alert_id}` in router order
3. **OpenRouter uses `OPENROUTER_API_KEY`** not `OPENAI_API_KEY`
4. **Tests**: Use StaticPool for SQLite connection isolation
5. **Frontend API**: Use `window.location.hostname`, not hardcoded localhost
6. **Always restart after changes:**
   ```bash
   docker compose down
   docker compose up -d --build
   ```

---

## Step 1: Create Coach Models

Create `backend/app/models/conversation.py`:

```python
"""Models for coach conversations."""

from sqlalchemy import Column, String, DateTime, Text, Boolean, Enum as SQLEnum, ForeignKey
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
    """A conversation thread with the coach."""
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
from app.models.conversation import Conversation, Message, MessageRole
```

Create Alembic migration:
```bash
docker compose exec api alembic revision --autogenerate -m "add coach conversation tables"
docker compose exec api alembic upgrade head
```

**Verify:**
```bash
docker compose exec api python -c "from app.models.conversation import Conversation, Message; print('Models loaded')"
```

---

## Step 2: Create Coach Schemas

Create `backend/app/schemas/coach.py`:

```python
"""Schemas for coach conversations."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    user = "user"
    assistant = "assistant"


class ChatRequest(BaseModel):
    """Request to send a message to the coach."""
    message: str = Field(..., min_length=1, max_length=4000)
    conversation_id: Optional[str] = None  # None = start new conversation


class ChatResponse(BaseModel):
    """Response from the coach."""
    response: str
    conversation_id: str
    message_id: str
    
    class Config:
        from_attributes = True


class MessageOut(BaseModel):
    """A message in a conversation."""
    id: str
    role: MessageRole
    content: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class ConversationSummary(BaseModel):
    """Summary of a conversation for listing."""
    id: str
    title: Optional[str]
    summary: Optional[str]
    last_message_at: datetime
    message_count: int
    is_archived: bool
    
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
    messages: List[MessageOut]
    
    class Config:
        from_attributes = True


class ConversationList(BaseModel):
    """Paginated list of conversations."""
    items: List[ConversationSummary]
    total: int
    
    class Config:
        from_attributes = True


class ContextData(BaseModel):
    """Financial context assembled for coach."""
    recent_spending: dict  # Summary by category
    recurring_charges: List[dict]
    alerts_summary: dict
    account_balances: List[dict]
    month_comparison: dict  # vs last month


class QuickQuestion(BaseModel):
    """Pre-defined quick questions for UI."""
    id: str
    text: str
    category: str  # "spending", "subscriptions", "general"
```

---

## Step 3: Create Coach Prompts

Create `backend/app/ai/prompts/coach.py`:

```python
"""Prompts for the AI coach."""

COACH_SYSTEM_PROMPT = """You are a friendly, knowledgeable personal finance coach. You have access to the user's financial data and can answer questions about their spending, subscriptions, and financial patterns.

## Your Personality
- Warm and encouraging, never judgmental
- Direct and concise - respect the user's time
- Proactive with insights when relevant
- Honest about limitations

## What You Know
You have access to:
- Transaction history (tokenized as MERCHANT_XXX with category hints)
- Recurring charges and subscriptions
- Spending trends and comparisons
- Recent alerts and anomalies

## What You Can Do
- Answer questions about spending ("How much did I spend on dining?")
- Explain trends ("Why is my spending up this month?")
- Review subscriptions ("What subscriptions do I have?")
- Provide context ("Is this normal for my spending?")
- Offer suggestions (without being pushy)

## What You Cannot Do
- Access real merchant names (you see tokens like MERCHANT_042)
- Make purchases or changes on behalf of the user
- Provide investment advice or recommendations
- Access data outside what's provided in context

## Response Guidelines
- Keep responses concise (2-4 sentences for simple questions)
- Use specific numbers when available
- Acknowledge uncertainty when data is incomplete
- Ask clarifying questions if the request is ambiguous

## Privacy Note
The user's data is tokenized for privacy. When you see "MERCHANT_042 [Groceries]", the system will replace this with the actual merchant name before showing the user. Speak naturally as if you know the merchant names.

Current date context: {current_date}
"""

CONTEXT_ASSEMBLY_PROMPT = """Based on the user's question, determine what financial context would be helpful.

User question: {question}

Available context types:
1. recent_transactions - Last 30 days of transactions
2. category_spending - Spending by category for current/previous months
3. recurring_charges - All detected recurring charges
4. alerts - Recent alerts and anomalies
5. trends - Month-over-month comparisons

Return a JSON array of context types needed (max 3 for efficiency):
["category_spending", "recurring_charges"]

Only include what's actually relevant to answer the question."""

TITLE_GENERATION_PROMPT = """Generate a short title (max 6 words) for this conversation based on the first message.

First message: {message}

Return only the title, no quotes or explanation."""

SUMMARY_GENERATION_PROMPT = """Summarize this conversation in 1-2 sentences for future context.

Messages:
{messages}

Focus on: key topics discussed, any decisions made, follow-up items.
Return only the summary."""


def build_coach_prompt(
    user_message: str,
    context: dict,
    conversation_history: list = None
) -> str:
    """Build the full prompt for the coach with context."""
    
    prompt_parts = []
    
    # Add conversation history if exists
    if conversation_history:
        prompt_parts.append("## Previous Messages in This Conversation")
        for msg in conversation_history[-10:]:  # Last 10 messages for context
            role = "User" if msg["role"] == "user" else "Coach"
            prompt_parts.append(f"{role}: {msg['content']}")
        prompt_parts.append("")
    
    # Add financial context
    prompt_parts.append("## Your Financial Context")
    
    if "category_spending" in context:
        prompt_parts.append("\n### Spending by Category (This Month)")
        for cat, amount in context["category_spending"].items():
            prompt_parts.append(f"- {cat}: ${amount:,.2f}")
    
    if "recent_transactions" in context:
        prompt_parts.append("\n### Recent Transactions")
        for txn in context["recent_transactions"][:10]:
            prompt_parts.append(
                f"- {txn['date']}: {txn['merchant']} ${abs(txn['amount']):,.2f}"
            )
    
    if "recurring_charges" in context:
        prompt_parts.append("\n### Recurring Charges")
        for rec in context["recurring_charges"]:
            prompt_parts.append(
                f"- {rec['name']}: ${rec['amount']:,.2f}/{rec['frequency']}"
            )
    
    if "alerts" in context:
        prompt_parts.append("\n### Recent Alerts")
        for alert in context["alerts"][:5]:
            prompt_parts.append(f"- {alert['title']}")
    
    if "trends" in context:
        prompt_parts.append("\n### Spending Trends")
        trends = context["trends"]
        prompt_parts.append(f"- This month: ${trends.get('current_total', 0):,.2f}")
        prompt_parts.append(f"- Last month: ${trends.get('previous_total', 0):,.2f}")
        if trends.get('change_pct'):
            direction = "up" if trends['change_pct'] > 0 else "down"
            prompt_parts.append(f"- Change: {abs(trends['change_pct']):.1f}% {direction}")
    
    prompt_parts.append(f"\n## User's Question\n{user_message}")
    
    return "\n".join(prompt_parts)
```

---

## Step 4: Create Coach Service

Create `backend/app/services/coach_service.py`:

```python
"""Service for coach conversations and context assembly."""

from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
import json

from app.models.conversation import Conversation, Message, MessageRole
from app.models.transaction import Transaction
from app.models.recurring import RecurringGroup
from app.models.alert import Alert
from app.models.category import Category
from app.ai.client import AIClient
from app.ai.prompts.coach import (
    COACH_SYSTEM_PROMPT,
    CONTEXT_ASSEMBLY_PROMPT,
    TITLE_GENERATION_PROMPT,
    build_coach_prompt,
)
from app.services.tokenization_service import TokenizationService


class CoachService:
    """Handles coach conversations and AI interactions."""
    
    def __init__(self, db: Session):
        self.db = db
        self.ai_client = AIClient(db)
        self.tokenizer = TokenizationService(db)
    
    async def chat(
        self,
        message: str,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a chat message and return the coach's response.
        
        Args:
            message: User's message
            conversation_id: Existing conversation ID, or None for new
            
        Returns:
            {response, conversation_id, message_id}
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
        tokenized_message = self._tokenize_message(message)
        
        # Store user message
        user_msg = Message(
            conversation_id=conversation.id,
            role=MessageRole.user,
            content=tokenized_message
        )
        self.db.add(user_msg)
        
        # Get conversation history
        history = self._get_conversation_history(conversation.id)
        
        # Determine what context is needed
        context = await self._assemble_context(message)
        
        # Build prompt and get response
        full_prompt = build_coach_prompt(message, context, history)
        system_prompt = COACH_SYSTEM_PROMPT.format(
            current_date=date.today().isoformat()
        )
        
        response = await self.ai_client.complete(
            prompt=full_prompt,
            system=system_prompt
        )
        
        # De-tokenize response for storage (it may contain tokens from context)
        # Actually, we store tokenized and de-tokenize on read
        assistant_msg = Message(
            conversation_id=conversation.id,
            role=MessageRole.assistant,
            content=response
        )
        self.db.add(assistant_msg)
        
        # Generate title for new conversations
        if not conversation.title and len(history) == 0:
            conversation.title = await self._generate_title(message)
        
        # Update conversation timestamp
        conversation.last_message_at = datetime.utcnow()
        
        self.db.commit()
        
        # De-tokenize response for user
        display_response = self.tokenizer.detokenize(response)
        
        return {
            "response": display_response,
            "conversation_id": conversation.id,
            "message_id": assistant_msg.id
        }
    
    def _tokenize_message(self, message: str) -> str:
        """Tokenize any PII in the user's message."""
        # For now, just return as-is
        # Users typically don't include merchant names in their questions
        # But we could add detection for things like "I spent at Whole Foods"
        return message
    
    def _get_conversation_history(self, conversation_id: str) -> List[Dict]:
        """Get recent messages from conversation."""
        messages = self.db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at).all()
        
        return [
            {"role": m.role.value, "content": m.content}
            for m in messages
        ]
    
    async def _assemble_context(self, question: str) -> Dict[str, Any]:
        """
        Determine what context is needed and fetch it.
        
        Uses AI to determine relevant context types, then fetches data.
        """
        context = {}
        
        # For MVP, always include basic context
        # Later: use AI to determine what's needed
        
        # Category spending this month
        context["category_spending"] = self._get_category_spending()
        
        # Recurring charges
        context["recurring_charges"] = self._get_recurring_summary()
        
        # Trends
        context["trends"] = self._get_spending_trends()
        
        # Recent alerts (if question seems alert-related)
        if any(word in question.lower() for word in ["alert", "unusual", "warning", "notification"]):
            context["alerts"] = self._get_recent_alerts()
        
        # Recent transactions (if question seems transaction-specific)
        if any(word in question.lower() for word in ["transaction", "purchase", "bought", "spent at", "recent"]):
            context["recent_transactions"] = self._get_recent_transactions()
        
        return context
    
    def _get_category_spending(self, months_back: int = 0) -> Dict[str, float]:
        """Get spending by category for a month."""
        today = date.today()
        if months_back == 0:
            start = today.replace(day=1)
            end = today
        else:
            # Previous month
            first_of_current = today.replace(day=1)
            last_of_previous = first_of_current - timedelta(days=1)
            start = last_of_previous.replace(day=1)
            end = last_of_previous
        
        results = self.db.query(
            Category.name,
            func.sum(Transaction.amount)
        ).join(
            Transaction, Transaction.category_id == Category.id
        ).filter(
            Transaction.date >= start,
            Transaction.date <= end,
            Transaction.amount < 0  # Expenses only
        ).group_by(Category.name).all()
        
        return {name: abs(float(amount)) for name, amount in results}
    
    def _get_recurring_summary(self) -> List[Dict]:
        """Get summary of recurring charges."""
        recurring = self.db.query(RecurringGroup).filter(
            RecurringGroup.is_active == True
        ).all()
        
        result = []
        for r in recurring:
            # Tokenize merchant name
            token = self.tokenizer.tokenize_merchant(r.name)
            category = self.db.query(Category).filter(
                Category.id == r.category_id
            ).first()
            
            result.append({
                "name": f"{token} [{category.name if category else 'Unknown'}]",
                "amount": float(r.expected_amount) if r.expected_amount else 0,
                "frequency": r.frequency.value if r.frequency else "monthly"
            })
        
        return result
    
    def _get_spending_trends(self) -> Dict[str, Any]:
        """Get month-over-month spending comparison."""
        today = date.today()
        
        # This month
        current_start = today.replace(day=1)
        current_total = self.db.query(func.sum(Transaction.amount)).filter(
            Transaction.date >= current_start,
            Transaction.amount < 0
        ).scalar() or 0
        
        # Last month
        first_of_current = today.replace(day=1)
        last_of_previous = first_of_current - timedelta(days=1)
        previous_start = last_of_previous.replace(day=1)
        previous_total = self.db.query(func.sum(Transaction.amount)).filter(
            Transaction.date >= previous_start,
            Transaction.date <= last_of_previous,
            Transaction.amount < 0
        ).scalar() or 0
        
        current = abs(float(current_total))
        previous = abs(float(previous_total))
        
        change_pct = None
        if previous > 0:
            change_pct = ((current - previous) / previous) * 100
        
        return {
            "current_total": current,
            "previous_total": previous,
            "change_pct": change_pct
        }
    
    def _get_recent_alerts(self, limit: int = 5) -> List[Dict]:
        """Get recent unread alerts."""
        alerts = self.db.query(Alert).filter(
            Alert.is_dismissed == False
        ).order_by(desc(Alert.created_at)).limit(limit).all()
        
        return [{"title": a.title, "type": a.type.value} for a in alerts]
    
    def _get_recent_transactions(self, limit: int = 10) -> List[Dict]:
        """Get recent transactions (tokenized)."""
        transactions = self.db.query(Transaction).order_by(
            desc(Transaction.date)
        ).limit(limit).all()
        
        result = []
        for t in transactions:
            merchant = t.clean_merchant or t.raw_description
            token = self.tokenizer.tokenize_merchant(merchant)
            category = self.db.query(Category).filter(
                Category.id == t.category_id
            ).first()
            
            result.append({
                "date": t.date.isoformat(),
                "merchant": f"{token} [{category.name if category else 'Unknown'}]",
                "amount": float(t.amount)
            })
        
        return result
    
    async def _generate_title(self, first_message: str) -> str:
        """Generate a title for a new conversation."""
        prompt = TITLE_GENERATION_PROMPT.format(message=first_message)
        try:
            title = await self.ai_client.complete(prompt=prompt)
            return title.strip()[:200]  # Truncate if needed
        except Exception:
            return first_message[:50] + "..." if len(first_message) > 50 else first_message
    
    def get_conversations(
        self,
        limit: int = 20,
        offset: int = 0,
        include_archived: bool = False
    ) -> Dict[str, Any]:
        """Get paginated list of conversations."""
        query = self.db.query(Conversation)
        
        if not include_archived:
            query = query.filter(Conversation.is_archived == False)
        
        total = query.count()
        
        conversations = query.order_by(
            desc(Conversation.last_message_at)
        ).offset(offset).limit(limit).all()
        
        items = []
        for c in conversations:
            message_count = self.db.query(Message).filter(
                Message.conversation_id == c.id
            ).count()
            
            items.append({
                "id": c.id,
                "title": c.title,
                "summary": c.summary,
                "last_message_at": c.last_message_at,
                "message_count": message_count,
                "is_archived": c.is_archived
            })
        
        return {"items": items, "total": total}
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict]:
        """Get a conversation with all messages."""
        conversation = self.db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        
        if not conversation:
            return None
        
        messages = self.db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at).all()
        
        # De-tokenize messages for display
        detokenized_messages = []
        for m in messages:
            detokenized_messages.append({
                "id": m.id,
                "role": m.role.value,
                "content": self.tokenizer.detokenize(m.content),
                "created_at": m.created_at
            })
        
        return {
            "id": conversation.id,
            "title": conversation.title,
            "summary": conversation.summary,
            "started_at": conversation.started_at,
            "last_message_at": conversation.last_message_at,
            "is_archived": conversation.is_archived,
            "messages": detokenized_messages
        }
    
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
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and all messages."""
        conversation = self.db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        
        if not conversation:
            return False
        
        self.db.delete(conversation)
        self.db.commit()
        return True
    
    def get_quick_questions(self) -> List[Dict]:
        """Get suggested quick questions for the UI."""
        return [
            {"id": "1", "text": "How much did I spend this month?", "category": "spending"},
            {"id": "2", "text": "What are my biggest expenses?", "category": "spending"},
            {"id": "3", "text": "How does this month compare to last month?", "category": "spending"},
            {"id": "4", "text": "What subscriptions do I have?", "category": "subscriptions"},
            {"id": "5", "text": "Are there any subscriptions I should review?", "category": "subscriptions"},
            {"id": "6", "text": "What alerts should I know about?", "category": "general"},
        ]
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
    ChatRequest,
    ChatResponse,
    ConversationList,
    ConversationDetail,
    ConversationSummary,
    QuickQuestion,
)
from app.services.coach_service import CoachService

router = APIRouter(prefix="/coach", tags=["coach"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """Send a message to the coach and get a response."""
    service = CoachService(db)
    
    try:
        result = await service.chat(
            message=request.message,
            conversation_id=request.conversation_id
        )
        return ChatResponse(**result)
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
    result = service.get_conversations(limit, offset, include_archived)
    return ConversationList(**result)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific conversation with all messages."""
    service = CoachService(db)
    result = service.get_conversation(conversation_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return ConversationDetail(**result)


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
    
    return {"status": "archived"}


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
    
    return {"status": "deleted"}


@router.get("/quick-questions", response_model=list[QuickQuestion])
def get_quick_questions(db: Session = Depends(get_db)):
    """Get suggested quick questions."""
    service = CoachService(db)
    questions = service.get_quick_questions()
    return [QuickQuestion(**q) for q in questions]
```

Update `backend/app/api/router.py`:

```python
from app.api.coach import router as coach_router

# Add to router includes:
router.include_router(coach_router)
```

---

## Step 6: Add Frontend Types and API Functions

Update `frontend/src/types/index.ts`:

```typescript
// Add coach types

export interface ChatRequest {
  message: string;
  conversation_id?: string;
}

export interface ChatResponse {
  response: string;
  conversation_id: string;
  message_id: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

export interface ConversationSummary {
  id: string;
  title: string | null;
  summary: string | null;
  last_message_at: string;
  message_count: number;
  is_archived: boolean;
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

export interface QuickQuestion {
  id: string;
  text: string;
  category: string;
}
```

Update `frontend/src/lib/api.ts`:

```typescript
// Add coach API functions

export const coachApi = {
  chat: (message: string, conversationId?: string) =>
    fetch(`${API_BASE}/coach/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        message, 
        conversation_id: conversationId 
      }),
    }).then(r => r.json()),
  
  getConversations: (limit = 20, offset = 0) =>
    fetch(`${API_BASE}/coach/conversations?limit=${limit}&offset=${offset}`).then(r => r.json()),
  
  getConversation: (id: string) =>
    fetch(`${API_BASE}/coach/conversations/${id}`).then(r => r.json()),
  
  archiveConversation: (id: string) =>
    fetch(`${API_BASE}/coach/conversations/${id}/archive`, { method: 'POST' }).then(r => r.json()),
  
  deleteConversation: (id: string) =>
    fetch(`${API_BASE}/coach/conversations/${id}`, { method: 'DELETE' }).then(r => r.json()),
  
  getQuickQuestions: () =>
    fetch(`${API_BASE}/coach/quick-questions`).then(r => r.json()),
};
```

---

## Step 7: Create Coach Widget Component

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
    <div className={cn(
      "flex gap-3 p-4",
      isUser ? "justify-end" : "justify-start"
    )}>
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
          <span className="text-sm">🤖</span>
        </div>
      )}
      
      <div className={cn(
        "max-w-[80%] rounded-lg px-4 py-2",
        isUser 
          ? "bg-primary text-primary-foreground" 
          : "bg-muted"
      )}>
        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        <span className="text-xs opacity-60 mt-1 block">
          {new Date(message.created_at).toLocaleTimeString([], { 
            hour: '2-digit', 
            minute: '2-digit' 
          })}
        </span>
      </div>
      
      {isUser && (
        <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center flex-shrink-0">
          <span className="text-sm text-primary-foreground">👤</span>
        </div>
      )}
    </div>
  );
}
```

Create `frontend/src/components/coach/CoachWidget.tsx`:

```tsx
import { useState } from 'react';
import { MessageCircle, Send, X, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ChatMessage } from './ChatMessage';
import { coachApi } from '@/lib/api';
import type { Message, QuickQuestion } from '@/types';

interface CoachWidgetProps {
  onExpand?: () => void;
}

export function CoachWidget({ onExpand }: CoachWidgetProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [quickQuestions, setQuickQuestions] = useState<QuickQuestion[]>([]);

  const loadQuickQuestions = async () => {
    try {
      const questions = await coachApi.getQuickQuestions();
      setQuickQuestions(questions);
    } catch (error) {
      console.error('Failed to load quick questions:', error);
    }
  };

  const handleOpen = () => {
    setIsOpen(true);
    if (quickQuestions.length === 0) {
      loadQuickQuestions();
    }
  };

  const handleSend = async (text?: string) => {
    const message = text || input.trim();
    if (!message || isLoading) return;

    const userMessage: Message = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: message,
      created_at: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await coachApi.chat(message, conversationId || undefined);
      
      if (!conversationId) {
        setConversationId(response.conversation_id);
      }

      const assistantMessage: Message = {
        id: response.message_id,
        role: 'assistant',
        content: response.response,
        created_at: new Date().toISOString(),
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Chat error:', error);
      // Show error message
      setMessages(prev => [...prev, {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        created_at: new Date().toISOString(),
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewConversation = () => {
    setMessages([]);
    setConversationId(null);
  };

  if (!isOpen) {
    return (
      <Button
        onClick={handleOpen}
        className="fixed bottom-6 right-6 h-14 w-14 rounded-full shadow-lg"
        size="icon"
      >
        <MessageCircle className="h-6 w-6" />
      </Button>
    );
  }

  return (
    <Card className="fixed bottom-6 right-6 w-96 h-[500px] shadow-xl flex flex-col">
      <CardHeader className="flex-shrink-0 flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-lg font-medium">
          💬 Financial Coach
        </CardTitle>
        <div className="flex gap-1">
          {onExpand && (
            <Button variant="ghost" size="icon" onClick={onExpand}>
              <span className="text-xs">↗️</span>
            </Button>
          )}
          <Button variant="ghost" size="icon" onClick={() => setIsOpen(false)}>
            <X className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col p-0 overflow-hidden">
        <ScrollArea className="flex-1 px-4">
          {messages.length === 0 ? (
            <div className="py-4 space-y-4">
              <p className="text-sm text-muted-foreground text-center">
                Ask me anything about your finances!
              </p>
              <div className="space-y-2">
                {quickQuestions.slice(0, 4).map((q) => (
                  <Button
                    key={q.id}
                    variant="outline"
                    className="w-full justify-start text-left h-auto py-2 text-sm"
                    onClick={() => handleSend(q.text)}
                  >
                    {q.text}
                  </Button>
                ))}
              </div>
            </div>
          ) : (
            <div className="py-2">
              {messages.map((message) => (
                <ChatMessage key={message.id} message={message} />
              ))}
              {isLoading && (
                <div className="flex gap-3 p-4">
                  <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                    <Loader2 className="h-4 w-4 animate-spin" />
                  </div>
                  <div className="bg-muted rounded-lg px-4 py-2">
                    <p className="text-sm text-muted-foreground">Thinking...</p>
                  </div>
                </div>
              )}
            </div>
          )}
        </ScrollArea>

        <div className="p-4 border-t flex-shrink-0">
          <form 
            onSubmit={(e) => { e.preventDefault(); handleSend(); }}
            className="flex gap-2"
          >
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about your finances..."
              disabled={isLoading}
              className="flex-1"
            />
            <Button type="submit" size="icon" disabled={isLoading || !input.trim()}>
              <Send className="h-4 w-4" />
            </Button>
          </form>
          {messages.length > 0 && (
            <Button 
              variant="link" 
              className="w-full text-xs mt-2"
              onClick={handleNewConversation}
            >
              Start new conversation
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
```

---

## Step 8: Create Coach Drawer Component

Create `frontend/src/components/coach/CoachDrawer.tsx`:

```tsx
import { useState, useEffect, useRef } from 'react';
import { Send, Loader2, History, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import { ChatMessage } from './ChatMessage';
import { coachApi } from '@/lib/api';
import type { Message, ConversationSummary } from '@/types';

interface CoachDrawerProps {
  trigger?: React.ReactNode;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

export function CoachDrawer({ trigger, open, onOpenChange }: CoachDrawerProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const loadConversations = async () => {
    try {
      const result = await coachApi.getConversations(10);
      setConversations(result.items);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  };

  const loadConversation = async (id: string) => {
    try {
      const conversation = await coachApi.getConversation(id);
      setMessages(conversation.messages);
      setConversationId(id);
      setShowHistory(false);
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  };

  const handleSend = async () => {
    const message = input.trim();
    if (!message || isLoading) return;

    const userMessage: Message = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: message,
      created_at: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await coachApi.chat(message, conversationId || undefined);
      
      if (!conversationId) {
        setConversationId(response.conversation_id);
      }

      const assistantMessage: Message = {
        id: response.message_id,
        role: 'assistant',
        content: response.response,
        created_at: new Date().toISOString(),
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => [...prev, {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        created_at: new Date().toISOString(),
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewConversation = () => {
    setMessages([]);
    setConversationId(null);
    setShowHistory(false);
  };

  const handleShowHistory = () => {
    loadConversations();
    setShowHistory(true);
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      {trigger && <SheetTrigger asChild>{trigger}</SheetTrigger>}
      <SheetContent className="w-[400px] sm:w-[540px] flex flex-col">
        <SheetHeader>
          <SheetTitle className="flex items-center justify-between">
            <span>💬 Financial Coach</span>
            <div className="flex gap-2">
              <Button 
                variant="ghost" 
                size="icon"
                onClick={handleShowHistory}
              >
                <History className="h-4 w-4" />
              </Button>
              <Button 
                variant="ghost" 
                size="icon"
                onClick={handleNewConversation}
              >
                <Plus className="h-4 w-4" />
              </Button>
            </div>
          </SheetTitle>
        </SheetHeader>

        <div className="flex-1 flex flex-col overflow-hidden mt-4">
          {showHistory ? (
            <ScrollArea className="flex-1">
              <div className="space-y-2 pr-4">
                {conversations.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-8">
                    No previous conversations
                  </p>
                ) : (
                  conversations.map((conv) => (
                    <button
                      key={conv.id}
                      onClick={() => loadConversation(conv.id)}
                      className="w-full text-left p-3 rounded-lg hover:bg-muted transition-colors"
                    >
                      <p className="font-medium text-sm truncate">
                        {conv.title || 'Untitled conversation'}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(conv.last_message_at).toLocaleDateString()} · {conv.message_count} messages
                      </p>
                    </button>
                  ))
                )}
              </div>
            </ScrollArea>
          ) : (
            <>
              <ScrollArea className="flex-1" ref={scrollRef}>
                <div className="pr-4">
                  {messages.length === 0 ? (
                    <div className="text-center py-12">
                      <p className="text-muted-foreground">
                        Ask me anything about your finances!
                      </p>
                    </div>
                  ) : (
                    messages.map((message) => (
                      <ChatMessage key={message.id} message={message} />
                    ))
                  )}
                  {isLoading && (
                    <div className="flex gap-3 p-4">
                      <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                        <Loader2 className="h-4 w-4 animate-spin" />
                      </div>
                      <div className="bg-muted rounded-lg px-4 py-2">
                        <p className="text-sm text-muted-foreground">Thinking...</p>
                      </div>
                    </div>
                  )}
                </div>
              </ScrollArea>

              <div className="pt-4 border-t mt-auto">
                <form 
                  onSubmit={(e) => { e.preventDefault(); handleSend(); }}
                  className="flex gap-2"
                >
                  <Input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Ask about your finances..."
                    disabled={isLoading}
                    className="flex-1"
                  />
                  <Button type="submit" size="icon" disabled={isLoading || !input.trim()}>
                    <Send className="h-4 w-4" />
                  </Button>
                </form>
              </div>
            </>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
```

---

## Step 9: Integrate Coach into Layout

Update `frontend/src/components/layout/Layout.tsx` to include the coach widget:

```tsx
// Add import
import { CoachWidget } from '@/components/coach/CoachWidget';

// Add at the end of the Layout component, before closing tag:
<CoachWidget />
```

Create `frontend/src/pages/Coach.tsx`:

```tsx
import { useState, useEffect, useRef } from 'react';
import { Send, Loader2, Plus, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ChatMessage } from '@/components/coach/ChatMessage';
import { coachApi } from '@/lib/api';
import type { Message, ConversationSummary, QuickQuestion } from '@/types';

export default function CoachPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [quickQuestions, setQuickQuestions] = useState<QuickQuestion[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadConversations();
    loadQuickQuestions();
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const loadConversations = async () => {
    try {
      const result = await coachApi.getConversations(20);
      setConversations(result.items);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  };

  const loadQuickQuestions = async () => {
    try {
      const questions = await coachApi.getQuickQuestions();
      setQuickQuestions(questions);
    } catch (error) {
      console.error('Failed to load quick questions:', error);
    }
  };

  const loadConversation = async (id: string) => {
    try {
      const conversation = await coachApi.getConversation(id);
      setMessages(conversation.messages);
      setConversationId(id);
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  };

  const handleSend = async (text?: string) => {
    const message = text || input.trim();
    if (!message || isLoading) return;

    const userMessage: Message = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: message,
      created_at: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await coachApi.chat(message, conversationId || undefined);
      
      if (!conversationId) {
        setConversationId(response.conversation_id);
        loadConversations(); // Refresh sidebar
      }

      const assistantMessage: Message = {
        id: response.message_id,
        role: 'assistant',
        content: response.response,
        created_at: new Date().toISOString(),
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => [...prev, {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        created_at: new Date().toISOString(),
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewConversation = () => {
    setMessages([]);
    setConversationId(null);
  };

  const handleDeleteConversation = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await coachApi.deleteConversation(id);
      if (conversationId === id) {
        handleNewConversation();
      }
      loadConversations();
    } catch (error) {
      console.error('Failed to delete conversation:', error);
    }
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] gap-4">
      {/* Sidebar */}
      <Card className="w-80 flex-shrink-0">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
          <CardTitle className="text-lg">Conversations</CardTitle>
          <Button variant="outline" size="icon" onClick={handleNewConversation}>
            <Plus className="h-4 w-4" />
          </Button>
        </CardHeader>
        <CardContent className="p-0">
          <ScrollArea className="h-[calc(100vh-12rem)]">
            <div className="space-y-1 px-4 pb-4">
              {conversations.map((conv) => (
                <div
                  key={conv.id}
                  onClick={() => loadConversation(conv.id)}
                  className={`group flex items-center justify-between p-3 rounded-lg cursor-pointer transition-colors ${
                    conversationId === conv.id ? 'bg-primary/10' : 'hover:bg-muted'
                  }`}
                >
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm truncate">
                      {conv.title || 'Untitled conversation'}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(conv.last_message_at).toLocaleDateString()}
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="opacity-0 group-hover:opacity-100 h-8 w-8"
                    onClick={(e) => handleDeleteConversation(conv.id, e)}
                  >
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                </div>
              ))}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>

      {/* Main chat area */}
      <Card className="flex-1 flex flex-col">
        <CardHeader className="flex-shrink-0 border-b">
          <CardTitle>💬 Financial Coach</CardTitle>
        </CardHeader>
        <CardContent className="flex-1 flex flex-col p-0 overflow-hidden">
          <ScrollArea className="flex-1 p-4" ref={scrollRef}>
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center py-12">
                <h3 className="text-xl font-semibold mb-2">
                  How can I help you today?
                </h3>
                <p className="text-muted-foreground mb-6 max-w-md">
                  I can answer questions about your spending, help review subscriptions, 
                  explain trends, and provide insights about your finances.
                </p>
                <div className="grid grid-cols-2 gap-3 max-w-lg">
                  {quickQuestions.map((q) => (
                    <Button
                      key={q.id}
                      variant="outline"
                      className="h-auto py-3 px-4 text-left justify-start"
                      onClick={() => handleSend(q.text)}
                    >
                      {q.text}
                    </Button>
                  ))}
                </div>
              </div>
            ) : (
              <div>
                {messages.map((message) => (
                  <ChatMessage key={message.id} message={message} />
                ))}
                {isLoading && (
                  <div className="flex gap-3 p-4">
                    <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                      <Loader2 className="h-4 w-4 animate-spin" />
                    </div>
                    <div className="bg-muted rounded-lg px-4 py-2">
                      <p className="text-sm text-muted-foreground">Thinking...</p>
                    </div>
                  </div>
                )}
              </div>
            )}
          </ScrollArea>

          <div className="p-4 border-t">
            <form 
              onSubmit={(e) => { e.preventDefault(); handleSend(); }}
              className="flex gap-2"
            >
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about your finances..."
                disabled={isLoading}
                className="flex-1"
              />
              <Button type="submit" disabled={isLoading || !input.trim()}>
                <Send className="h-4 w-4 mr-2" />
                Send
              </Button>
            </form>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
```

Update `frontend/src/App.tsx` to add the coach route:

```tsx
// Add import
import CoachPage from '@/pages/Coach';

// Add route in Routes:
<Route path="/coach" element={<CoachPage />} />
```

Update the sidebar to include Coach link (in `frontend/src/components/layout/Sidebar.tsx`):

```tsx
// Add to navigation items:
{ name: 'Coach', href: '/coach', icon: MessageCircle }
```

---

## Step 10: Add Tests

Create `backend/tests/test_coach_service.py`:

```python
"""Tests for coach service."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.coach_service import CoachService
from app.models.conversation import Conversation, Message, MessageRole


class TestCoachConversations:
    """Tests for conversation management."""
    
    def test_create_new_conversation(self, db_session):
        """New chat should create a conversation."""
        service = CoachService(db_session)
        
        # Mock AI client
        with patch.object(service.ai_client, 'complete', new_callable=AsyncMock) as mock_complete:
            mock_complete.return_value = "I can help you with that!"
            
            import asyncio
            result = asyncio.get_event_loop().run_until_complete(
                service.chat("How much did I spend?")
            )
        
        assert "conversation_id" in result
        assert "response" in result
        
        # Verify conversation was created
        conv = db_session.query(Conversation).filter(
            Conversation.id == result["conversation_id"]
        ).first()
        assert conv is not None
    
    def test_continue_existing_conversation(self, db_session):
        """Chat with conversation_id should continue existing conversation."""
        # Create existing conversation
        conv = Conversation()
        db_session.add(conv)
        db_session.flush()
        
        service = CoachService(db_session)
        
        with patch.object(service.ai_client, 'complete', new_callable=AsyncMock) as mock_complete:
            mock_complete.return_value = "Here's your spending breakdown..."
            
            import asyncio
            result = asyncio.get_event_loop().run_until_complete(
                service.chat("Show me more details", conversation_id=conv.id)
            )
        
        assert result["conversation_id"] == conv.id
        
        # Verify message was added
        messages = db_session.query(Message).filter(
            Message.conversation_id == conv.id
        ).all()
        assert len(messages) == 2  # User + assistant
    
    def test_invalid_conversation_raises_error(self, db_session):
        """Chat with invalid conversation_id should raise error."""
        service = CoachService(db_session)
        
        with pytest.raises(ValueError, match="not found"):
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                service.chat("Hello", conversation_id="invalid-id")
            )
    
    def test_list_conversations(self, db_session):
        """Should list conversations in order."""
        # Create conversations
        conv1 = Conversation(title="First chat")
        conv2 = Conversation(title="Second chat")
        db_session.add_all([conv1, conv2])
        db_session.commit()
        
        service = CoachService(db_session)
        result = service.get_conversations()
        
        assert result["total"] == 2
        assert len(result["items"]) == 2
    
    def test_archive_conversation(self, db_session):
        """Should archive a conversation."""
        conv = Conversation(title="Test chat")
        db_session.add(conv)
        db_session.commit()
        
        service = CoachService(db_session)
        success = service.archive_conversation(conv.id)
        
        assert success is True
        
        db_session.refresh(conv)
        assert conv.is_archived is True
    
    def test_delete_conversation(self, db_session):
        """Should delete conversation and messages."""
        conv = Conversation(title="Test chat")
        db_session.add(conv)
        db_session.flush()
        
        msg = Message(
            conversation_id=conv.id,
            role=MessageRole.user,
            content="Hello"
        )
        db_session.add(msg)
        db_session.commit()
        
        service = CoachService(db_session)
        success = service.delete_conversation(conv.id)
        
        assert success is True
        
        # Verify deleted
        assert db_session.query(Conversation).filter(
            Conversation.id == conv.id
        ).first() is None
        assert db_session.query(Message).filter(
            Message.conversation_id == conv.id
        ).count() == 0


class TestCoachContext:
    """Tests for context assembly."""
    
    def test_get_category_spending(self, db_session, sample_transactions):
        """Should calculate spending by category."""
        service = CoachService(db_session)
        spending = service._get_category_spending()
        
        # Should have spending data
        assert isinstance(spending, dict)
    
    def test_get_recurring_summary(self, db_session, sample_recurring):
        """Should return recurring charges summary."""
        service = CoachService(db_session)
        recurring = service._get_recurring_summary()
        
        assert isinstance(recurring, list)
        for item in recurring:
            assert "name" in item
            assert "amount" in item
            assert "frequency" in item
    
    def test_get_spending_trends(self, db_session, sample_transactions):
        """Should calculate month-over-month trends."""
        service = CoachService(db_session)
        trends = service._get_spending_trends()
        
        assert "current_total" in trends
        assert "previous_total" in trends


class TestQuickQuestions:
    """Tests for quick questions."""
    
    def test_get_quick_questions(self, db_session):
        """Should return quick question suggestions."""
        service = CoachService(db_session)
        questions = service.get_quick_questions()
        
        assert len(questions) > 0
        for q in questions:
            assert "id" in q
            assert "text" in q
            assert "category" in q
```

Add fixtures to `backend/tests/conftest.py`:

```python
@pytest.fixture
def sample_recurring(db_session, sample_categories):
    """Create sample recurring charges."""
    from app.models.recurring import RecurringGroup, Frequency
    
    recurring = [
        RecurringGroup(
            name="Netflix",
            expected_amount=15.99,
            frequency=Frequency.monthly,
            category_id=sample_categories["Entertainment"].id,
            is_active=True
        ),
        RecurringGroup(
            name="Spotify",
            expected_amount=9.99,
            frequency=Frequency.monthly,
            category_id=sample_categories["Entertainment"].id,
            is_active=True
        ),
    ]
    
    for r in recurring:
        db_session.add(r)
    db_session.commit()
    
    return recurring
```

---

## Step 11: Final Testing & Verification

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
curl http://localhost:8000/api/v1/coach/quick-questions
curl http://localhost:8000/api/v1/coach/conversations

# Test chat (requires AI provider to be configured)
curl -X POST http://localhost:8000/api/v1/coach/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How much did I spend this month?"}'

# Run coach tests
docker compose exec api pytest tests/test_coach_service.py -v

# Run all tests
docker compose exec api pytest -v --tb=short
```

**Test in UI:**
1. Visit the app - should see coach widget (bubble) in bottom right
2. Click widget - should open mini chat interface
3. Ask a question - should get AI response
4. Go to /coach page - should see full chat interface
5. Verify conversation history works
6. Start new conversation, verify sidebar updates

---

## Verification Checklist

- [ ] Coach models created and migrated
- [ ] `POST /api/v1/coach/chat` works
- [ ] `GET /api/v1/coach/conversations` returns list
- [ ] `GET /api/v1/coach/conversations/{id}` returns messages
- [ ] `DELETE /api/v1/coach/conversations/{id}` deletes
- [ ] Quick questions endpoint works
- [ ] Coach widget appears on all pages
- [ ] Widget opens/closes properly
- [ ] Can send messages and receive responses
- [ ] Conversation history persists
- [ ] Full coach page works
- [ ] Context assembly includes relevant financial data
- [ ] Messages are detokenized for display
- [ ] Tests pass

---

## What's Next (Phase 9)

Phase 8 gives us the foundation. Phase 9 adds:

1. **Proactive Observations**
   - Background job to detect patterns
   - Observation model and storage
   - Surface observations in widget
   
2. **Goal Tracking**
   - Goal model (budget, savings targets)
   - Goal progress calculations
   - Goal cards in UI
   
3. **Enhanced Memory**
   - Conversation summarization
   - Long-term context preservation
   - User preference learning

4. **UI Polish**
   - Better message formatting
   - Charts/graphs in responses
   - Voice input (future)
