"""Coach API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import List

from app.dependencies import get_db
from app.rate_limit import limiter
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
@limiter.limit("20/minute")
async def chat(
    request: Request, chat_request: ChatRequest, db: Session = Depends(get_db)
):
    """Send a message to the coach and get a response."""
    service = CoachService(db)

    try:
        result = await service.chat(
            message=chat_request.message, conversation_id=chat_request.conversation_id
        )
        return ChatResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Coach error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="An error occurred processing your message"
        )


@router.get("/conversations", response_model=ConversationList)
def list_conversations(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    include_archived: bool = Query(False),
    db: Session = Depends(get_db),
):
    """Get list of conversations."""
    service = CoachService(db)
    result = service.get_conversations(limit, offset, include_archived)
    return ConversationList(**result)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: str, db: Session = Depends(get_db)):
    """Get a specific conversation with all messages."""
    service = CoachService(db)
    result = service.get_conversation(conversation_id)

    if not result:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return ConversationDetail(**result)


@router.post("/conversations/{conversation_id}/archive")
def archive_conversation(conversation_id: str, db: Session = Depends(get_db)):
    """Archive a conversation."""
    service = CoachService(db)
    success = service.archive_conversation(conversation_id)

    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {"status": "archived"}


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str, db: Session = Depends(get_db)):
    """Delete a conversation."""
    service = CoachService(db)
    success = service.delete_conversation(conversation_id)

    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {"status": "deleted"}


@router.get("/quick-questions", response_model=List[QuickQuestion])
def get_quick_questions(db: Session = Depends(get_db)):
    """Get suggested quick questions."""
    service = CoachService(db)
    questions = service.get_quick_questions()
    return [QuickQuestion(**q) for q in questions]
