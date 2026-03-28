"""Service for coach conversations and context assembly."""

import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, AsyncIterator
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.conversation import Conversation, Message, MessageRole
from app.models.transaction import Transaction
from app.models.recurring import RecurringGroup
from app.models.alert import Alert
from app.models.category import Category
from app.ai.client import get_ai_client_with_db
from app.ai.prompts.coach import (
    COACH_SYSTEM_PROMPT,
    TITLE_GENERATION_PROMPT,
    build_coach_prompt,
)
from app.services.tokenization_service import TokenizationService
from app.ai.sanitization import sanitize_for_prompt

logger = logging.getLogger(__name__)


class CoachService:
    """Handles coach conversations and AI interactions."""

    def __init__(self, db: Session):
        self.db = db
        self.tokenizer = TokenizationService(db)

    async def chat(
        self, message: str, conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a chat message and return the coach's response.

        Args:
            message: User's message
            conversation_id: Existing conversation ID, or None for new

        Returns:
            {response, conversation_id, message_id}
        """
        if conversation_id:
            conversation = (
                self.db.query(Conversation)
                .filter(Conversation.id == conversation_id)
                .first()
            )
            if not conversation:
                raise ValueError(f"Conversation {conversation_id} not found")
        else:
            conversation = Conversation()
            self.db.add(conversation)
            self.db.flush()

        tokenized_message = self._tokenize_message(message)

        user_msg = Message(
            conversation_id=conversation.id,
            role=MessageRole.user,
            content=tokenized_message,
        )
        self.db.add(user_msg)

        history = self._get_conversation_history(conversation.id)

        context = await self._assemble_context(message)

        sanitized_message = sanitize_for_prompt(message, max_length=2000)
        sanitized_history = [
            {
                "role": h["role"],
                "content": sanitize_for_prompt(h["content"], max_length=2000),
            }
            for h in history
        ]
        full_prompt = build_coach_prompt(sanitized_message, context, sanitized_history)
        system_prompt = COACH_SYSTEM_PROMPT.format(
            current_date=date.today().isoformat()
        )

        try:
            ai_client = get_ai_client_with_db(self.db, task="coach")
            response = await ai_client.complete(
                system_prompt=system_prompt, user_prompt=full_prompt
            )
        except Exception as e:
            logger.error(f"AI completion error in coach: {e}")
            self.db.rollback()
            raise

        assistant_msg = Message(
            conversation_id=conversation.id,
            role=MessageRole.assistant,
            content=response,
        )
        self.db.add(assistant_msg)

        if not conversation.title and len(history) == 0:
            conversation.title = await self._generate_title(message)

        conversation.last_message_at = datetime.utcnow()

        self.db.commit()

        display_response = self.tokenizer.detokenize(response)

        return {
            "response": display_response,
            "conversation_id": conversation.id,
            "message_id": assistant_msg.id,
        }

    async def chat_stream(
        self, message: str, conversation_id: Optional[str] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Process a chat message and stream the coach's response.

        Args:
            message: User's message
            conversation_id: Existing conversation ID, or None for new

        Yields:
            Dict with "type" field: "token" for text chunks, "done" for final metadata
        """
        if conversation_id:
            conversation = (
                self.db.query(Conversation)
                .filter(Conversation.id == conversation_id)
                .first()
            )
            if not conversation:
                raise ValueError(f"Conversation {conversation_id} not found")
        else:
            conversation = Conversation()
            self.db.add(conversation)
            self.db.flush()

        tokenized_message = self._tokenize_message(message)

        user_msg = Message(
            conversation_id=conversation.id,
            role=MessageRole.user,
            content=tokenized_message,
        )
        self.db.add(user_msg)

        history = self._get_conversation_history(conversation.id)

        context = await self._assemble_context(message)

        sanitized_message = sanitize_for_prompt(message, max_length=2000)
        sanitized_history = [
            {
                "role": h["role"],
                "content": sanitize_for_prompt(h["content"], max_length=2000),
            }
            for h in history
        ]
        full_prompt = build_coach_prompt(sanitized_message, context, sanitized_history)
        system_prompt = COACH_SYSTEM_PROMPT.format(
            current_date=date.today().isoformat()
        )

        try:
            ai_client = get_ai_client_with_db(self.db, task="coach")
            full_response = ""
            async for chunk in ai_client.complete_stream(
                system_prompt=system_prompt, user_prompt=full_prompt
            ):
                full_response += chunk
                yield {"type": "token", "content": chunk}
        except Exception as e:
            logger.error(f"AI streaming error in coach: {e}")
            self.db.rollback()
            raise

        display_response = self.tokenizer.detokenize(full_response)

        assistant_msg = Message(
            conversation_id=conversation.id,
            role=MessageRole.assistant,
            content=full_response,
        )
        self.db.add(assistant_msg)

        if not conversation.title and len(history) == 0:
            conversation.title = await self._generate_title(message)

        conversation.last_message_at = datetime.utcnow()

        self.db.commit()

        yield {
            "type": "done",
            "conversation_id": conversation.id,
            "message_id": assistant_msg.id,
        }

    def _tokenize_message(self, message: str) -> str:
        """Tokenize any PII in the user's message."""
        return message

    def _get_conversation_history(self, conversation_id: str) -> List[Dict]:
        """Get recent messages from conversation."""
        messages = (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
            .all()
        )

        return [{"role": m.role.value, "content": m.content} for m in messages]

    async def _assemble_context(self, question: str) -> Dict[str, Any]:
        """
        Assemble comprehensive financial context for the coach.
        Always includes spending context (recent + monthly + trends).
        """
        context = {}

        context["spending_context"] = self._get_spending_context()

        context["recurring_charges"] = self._get_recurring_summary()

        if any(
            word in question.lower()
            for word in ["alert", "unusual", "warning", "notification"]
        ):
            context["alerts"] = self._get_recent_alerts()

        return context

    def _get_category_spending(self, months_back: int = 0) -> Dict[str, float]:
        """Get spending by category for a month."""
        today = date.today()
        if months_back == 0:
            start = today.replace(day=1)
            end = today
        else:
            first_of_current = today.replace(day=1)
            last_of_previous = first_of_current - timedelta(days=1)
            start = last_of_previous.replace(day=1)
            end = last_of_previous

        results = (
            self.db.query(Category.name, func.sum(Transaction.amount))
            .join(Transaction, Transaction.category_id == Category.id)
            .filter(
                Transaction.date >= start,
                Transaction.date <= end,
                Transaction.amount < 0,
            )
            .group_by(Category.name)
            .all()
        )

        return {name: abs(float(amount)) for name, amount in results}

    def _get_recurring_summary(self) -> List[Dict]:
        """Get summary of recurring charges."""
        recurring = (
            self.db.query(RecurringGroup).filter(RecurringGroup.is_active == True).all()
        )

        categories = {
            c.id: c.name for c in self.db.query(Category.id, Category.name).all()
        }

        result = []
        for r in recurring:
            token = self.tokenizer.tokenize_merchant(r.name)

            result.append(
                {
                    "name": f"{token} [{categories.get(r.category_id, 'Unknown')}]",
                    "amount": float(r.expected_amount) if r.expected_amount else 0,
                    "frequency": r.frequency.value if r.frequency else "monthly",
                }
            )

        return result

    def _get_spending_trends(self) -> Dict[str, Any]:
        """Get month-over-month spending comparison."""
        today = date.today()

        current_start = today.replace(day=1)
        current_total = (
            self.db.query(func.sum(Transaction.amount))
            .filter(Transaction.date >= current_start, Transaction.amount < 0)
            .scalar()
            or 0
        )

        first_of_current = today.replace(day=1)
        last_of_previous = first_of_current - timedelta(days=1)
        previous_start = last_of_previous.replace(day=1)
        previous_total = (
            self.db.query(func.sum(Transaction.amount))
            .filter(
                Transaction.date >= previous_start,
                Transaction.date <= last_of_previous,
                Transaction.amount < 0,
            )
            .scalar()
            or 0
        )

        current = abs(float(current_total))
        previous = abs(float(previous_total))

        change_pct = None
        if previous > 0:
            change_pct = ((current - previous) / previous) * 100

        return {
            "current_total": current,
            "previous_total": previous,
            "change_pct": change_pct,
        }

    def _get_recent_alerts(self, limit: int = 5) -> List[Dict]:
        """Get recent unread alerts."""
        alerts = (
            self.db.query(Alert)
            .filter(Alert.is_dismissed == False)
            .order_by(desc(Alert.created_at))
            .limit(limit)
            .all()
        )

        return [{"title": a.title, "type": a.type.value} for a in alerts]

    def _get_recent_transactions(self, limit: int = 300) -> List[Dict]:
        """Get most recent transactions (tokenized)."""
        transactions = (
            self.db.query(Transaction)
            .order_by(desc(Transaction.date))
            .limit(limit)
            .all()
        )

        categories = {
            c.id: c.name for c in self.db.query(Category.id, Category.name).all()
        }

        result = []
        for t in transactions:
            merchant = t.clean_merchant or t.raw_description
            token = self.tokenizer.tokenize_merchant(merchant)

            result.append(
                {
                    "date": t.date.isoformat(),
                    "merchant": f"{token} [{categories.get(t.category_id, 'Unknown')}]",
                    "amount": float(t.amount),
                }
            )

        return result

    def _get_monthly_category_totals(
        self, months: int = 12
    ) -> Dict[str, Dict[str, float]]:
        """Get monthly spending totals by category for the last N months."""
        from sqlalchemy import extract

        today = date.today()
        start_date = (today.replace(day=1) - timedelta(days=30 * (months - 1))).replace(
            day=1
        )

        results = (
            self.db.query(
                func.strftime("%Y-%m", Transaction.date).label("month"),
                Category.name.label("category"),
                func.sum(Transaction.amount).label("total"),
            )
            .join(Category, Transaction.category_id == Category.id)
            .filter(
                Transaction.date >= start_date,
                Transaction.amount < 0,
            )
            .group_by("month", "category")
            .all()
        )

        monthly_data: Dict[str, Dict[str, float]] = {}
        for row in results:
            month = row.month
            if month not in monthly_data:
                monthly_data[month] = {}
            monthly_data[month][row.category] = abs(float(row.total))

        return monthly_data

    def _calculate_trends(
        self, monthly_data: Dict[str, Dict[str, float]]
    ) -> Dict[str, Any]:
        """Calculate spending trends from monthly data."""
        if not monthly_data:
            return {}

        sorted_months = sorted(monthly_data.keys())
        if len(sorted_months) < 2:
            return {"total_months": len(sorted_months)}

        current_month = sorted_months[-1]
        previous_month = sorted_months[-2] if len(sorted_months) > 1 else None

        current_total = sum(monthly_data[current_month].values())
        previous_total = (
            sum(monthly_data[previous_month].values()) if previous_month else 0
        )

        all_categories = set()
        for month_data in monthly_data.values():
            all_categories.update(month_data.keys())

        category_trends = {}
        for cat in all_categories:
            values = [monthly_data[m].get(cat, 0) for m in sorted_months[-3:]]
            if values:
                avg = sum(values) / len(values)
                current = values[-1]
                if avg > 0:
                    change_pct = ((current - avg) / avg) * 100
                    category_trends[cat] = {
                        "current": current,
                        "avg_3mo": avg,
                        "change_pct": change_pct,
                    }

        total_avg = sum(sum(m.values()) for m in monthly_data.values()) / len(
            monthly_data
        )

        return {
            "current_month_total": current_total,
            "previous_month_total": previous_total,
            "avg_monthly_total": total_avg,
            "month_change_pct": (
                (current_total - previous_total) / previous_total * 100
            )
            if previous_total > 0
            else None,
            "category_trends": category_trends,
            "months_with_data": len(sorted_months),
        }

    def _get_spending_context(self) -> Dict[str, Any]:
        """Get comprehensive spending context for the coach."""
        recent_transactions = self._get_recent_transactions(limit=300)

        monthly_totals = self._get_monthly_category_totals(months=12)

        trends = self._calculate_trends(monthly_totals)

        return {
            "recent_transactions": recent_transactions,
            "monthly_by_category": monthly_totals,
            "trends": trends,
        }

    async def _generate_title(self, first_message: str) -> str:
        """Generate a title for a new conversation."""
        sanitized = sanitize_for_prompt(first_message, max_length=200)
        prompt = TITLE_GENERATION_PROMPT.format(message=sanitized)
        try:
            ai_client = get_ai_client_with_db(self.db, task="coach")
            title = await ai_client.complete(
                system_prompt="You generate short, descriptive titles for conversations.",
                user_prompt=prompt,
            )
            return title.strip()[:200]
        except Exception:
            return (
                first_message[:50] + "..." if len(first_message) > 50 else first_message
            )

    def get_conversations(
        self, limit: int = 20, offset: int = 0, include_archived: bool = False
    ) -> Dict[str, Any]:
        """Get paginated list of conversations."""
        query = self.db.query(Conversation)

        if not include_archived:
            query = query.filter(Conversation.is_archived == False)

        total = query.count()

        conversations = (
            query.order_by(desc(Conversation.last_message_at))
            .offset(offset)
            .limit(limit)
            .all()
        )

        items = []
        for c in conversations:
            message_count = (
                self.db.query(Message).filter(Message.conversation_id == c.id).count()
            )

            items.append(
                {
                    "id": c.id,
                    "title": c.title,
                    "summary": c.summary,
                    "last_message_at": c.last_message_at,
                    "message_count": message_count,
                    "is_archived": c.is_archived,
                }
            )

        return {"items": items, "total": total}

    def get_conversation(self, conversation_id: str) -> Optional[Dict]:
        """Get a conversation with all messages."""
        conversation = (
            self.db.query(Conversation)
            .filter(Conversation.id == conversation_id)
            .first()
        )

        if not conversation:
            return None

        messages = (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
            .all()
        )

        detokenized_messages = []
        for m in messages:
            detokenized_messages.append(
                {
                    "id": m.id,
                    "role": m.role.value,
                    "content": self.tokenizer.detokenize(m.content),
                    "created_at": m.created_at,
                }
            )

        return {
            "id": conversation.id,
            "title": conversation.title,
            "summary": conversation.summary,
            "started_at": conversation.started_at,
            "last_message_at": conversation.last_message_at,
            "is_archived": conversation.is_archived,
            "messages": detokenized_messages,
        }

    def archive_conversation(self, conversation_id: str) -> bool:
        """Archive a conversation."""
        conversation = (
            self.db.query(Conversation)
            .filter(Conversation.id == conversation_id)
            .first()
        )

        if not conversation:
            return False

        conversation.is_archived = True
        self.db.commit()
        return True

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and all messages."""
        conversation = (
            self.db.query(Conversation)
            .filter(Conversation.id == conversation_id)
            .first()
        )

        if not conversation:
            return False

        self.db.delete(conversation)
        self.db.commit()
        return True

    def get_quick_questions(self) -> List[Dict]:
        """Get suggested quick questions for the UI."""
        return [
            {
                "id": "1",
                "text": "How much did I spend this month?",
                "category": "spending",
            },
            {
                "id": "2",
                "text": "What are my biggest expenses?",
                "category": "spending",
            },
            {
                "id": "3",
                "text": "How does this month compare to last month?",
                "category": "spending",
            },
            {
                "id": "4",
                "text": "What subscriptions do I have?",
                "category": "subscriptions",
            },
            {
                "id": "5",
                "text": "Are there any subscriptions I should review?",
                "category": "subscriptions",
            },
            {
                "id": "6",
                "text": "What alerts should I know about?",
                "category": "general",
            },
        ]
