"""
Chat router: AI-powered financial assistant conversations.
"""

import logging
import uuid
from typing import Optional

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app.models.chat_history import ChatHistory
from app.models.user import User
from app.schemas.chat import (
    ChatHistoryResponse,
    ChatMessageResponse,
    ChatRequest,
    ChatResponse,
)
from app.services import chat_service

router = APIRouter()


@router.post("", response_model=ChatResponse)
async def send_chat_message(
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Send a message to the AI financial assistant and get a response."""
    logger.info("Chat message received: user_id=%s, message=%.100s", current_user.id, body.message)
    session_id = body.session_id or str(uuid.uuid4())

    assistant_response = await chat_service.process_chat(
        user_id=current_user.id,
        message=body.message,
        session_id=session_id,
        db=db,
    )

    return ChatResponse(
        user_message=body.message,
        assistant_message=assistant_response,
        session_id=session_id,
    )


@router.get("/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return chat history for the current user, optionally filtered by session."""
    logger.info("Chat history request: user_id=%s, session_id=%s", current_user.id, session_id)
    query = db.query(ChatHistory).filter(ChatHistory.user_id == current_user.id)

    if session_id:
        query = query.filter(ChatHistory.session_id == session_id)

    total_count = query.count()

    records = (
        query.order_by(ChatHistory.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    # Reverse to chronological order for display
    records = list(reversed(records))

    messages = [
        ChatMessageResponse(
            id=record.id,
            role=record.role,
            content=record.content,
            created_at=record.created_at,
        )
        for record in records
    ]

    return ChatHistoryResponse(messages=messages, total_count=total_count)
