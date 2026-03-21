"""Tests for coach service."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio

from app.services.coach_service import CoachService
from app.models.conversation import Conversation, Message, MessageRole


class TestCoachConversations:
    """Tests for conversation management."""

    def test_create_new_conversation(self, db_session):
        """New chat should create a conversation."""
        service = CoachService(db_session)

        mock_ai_client = MagicMock()
        mock_ai_client.complete = AsyncMock(return_value="I can help you with that!")

        with patch(
            "app.services.coach_service.get_ai_client_with_db",
            return_value=mock_ai_client,
        ):
            result = asyncio.get_event_loop().run_until_complete(
                service.chat("How much did I spend?")
            )

        assert "conversation_id" in result
        assert "response" in result

        conv = (
            db_session.query(Conversation)
            .filter(Conversation.id == result["conversation_id"])
            .first()
        )
        assert conv is not None

    def test_continue_existing_conversation(self, db_session):
        """Chat with conversation_id should continue existing conversation."""
        conv = Conversation()
        db_session.add(conv)
        db_session.flush()

        service = CoachService(db_session)

        mock_ai_client = MagicMock()
        mock_ai_client.complete = AsyncMock(
            return_value="Here's your spending breakdown..."
        )

        with patch(
            "app.services.coach_service.get_ai_client_with_db",
            return_value=mock_ai_client,
        ):
            result = asyncio.get_event_loop().run_until_complete(
                service.chat("Show me more details", conversation_id=conv.id)
            )

        assert result["conversation_id"] == conv.id

        messages = (
            db_session.query(Message).filter(Message.conversation_id == conv.id).all()
        )
        assert len(messages) == 2

    def test_invalid_conversation_raises_error(self, db_session):
        """Chat with invalid conversation_id should raise error."""
        service = CoachService(db_session)

        with pytest.raises(ValueError, match="not found"):
            asyncio.get_event_loop().run_until_complete(
                service.chat("Hello", conversation_id="invalid-id")
            )

    def test_list_conversations(self, db_session):
        """Should list conversations in order."""
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

        msg = Message(conversation_id=conv.id, role=MessageRole.user, content="Hello")
        db_session.add(msg)
        db_session.commit()

        service = CoachService(db_session)
        success = service.delete_conversation(conv.id)

        assert success is True

        assert (
            db_session.query(Conversation).filter(Conversation.id == conv.id).first()
            is None
        )
        assert (
            db_session.query(Message).filter(Message.conversation_id == conv.id).count()
            == 0
        )


class TestCoachContext:
    """Tests for context assembly."""

    def test_get_category_spending(self, db_session, sample_transaction):
        """Should calculate spending by category."""
        service = CoachService(db_session)
        spending = service._get_category_spending()

        assert isinstance(spending, dict)

    def test_get_recurring_summary(self, db_session, sample_recurring_group):
        """Should return recurring charges summary."""
        service = CoachService(db_session)
        recurring = service._get_recurring_summary()

        assert isinstance(recurring, list)
        for item in recurring:
            assert "name" in item
            assert "amount" in item
            assert "frequency" in item

    def test_get_spending_trends(self, db_session, sample_transaction):
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


class TestCoachAPI:
    """Tests for coach API endpoints."""

    def test_get_quick_questions_endpoint(self, client):
        """Quick questions endpoint should return list."""
        response = client.get("/api/v1/coach/quick-questions")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_list_conversations_empty(self, client):
        """Should return empty list when no conversations."""
        response = client.get("/api/v1/coach/conversations")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_get_conversation_not_found(self, client):
        """Should return 404 for non-existent conversation."""
        response = client.get("/api/v1/coach/conversations/nonexistent-id")
        assert response.status_code == 404
