from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from models import get_db, Conversation, Message
from schemas import (
    ConversationCreateRequest, ConversationCreateResponse,
    ConversationListItem, ConversationDetail,
    ConversationUpdateRequest,
)

router = APIRouter(prefix="/api/conversations", tags=["History"])


@router.get(
    "",
    response_model=list[ConversationListItem],
    summary="List Conversations",
    description="Returns all conversations ordered by most recently updated. Includes message count for each.",
)
def list_conversations(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(
            Conversation,
            func.count(Message.id).label("message_count"),
        )
        .outerjoin(Message)
        .group_by(Conversation.id)
        .order_by(Conversation.updated_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    result = []
    for convo, count in rows:
        item = ConversationListItem.model_validate(convo)
        item.message_count = count
        result.append(item)
    return result


@router.post(
    "",
    response_model=ConversationCreateResponse,
    status_code=201,
    summary="Create Conversation",
    description="Start a new conversation. Returns the conversation ID to use with subsequent API calls.",
)
def create_conversation(request: ConversationCreateRequest, db: Session = Depends(get_db)):
    convo = Conversation(
        title=request.title or "New Conversation",
        endpoint=request.endpoint,
        mode=request.mode,
        provider=request.provider,
        prompt_version=request.prompt_version,
    )
    db.add(convo)
    db.commit()
    db.refresh(convo)
    return convo


@router.get(
    "/{conversation_id}",
    response_model=ConversationDetail,
    summary="Get Conversation",
    description="Returns a conversation with all its messages in chronological order.",
)
def get_conversation(conversation_id: UUID, db: Session = Depends(get_db)):
    convo = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not convo:
        raise HTTPException(404, "Conversation not found")
    return convo


@router.patch(
    "/{conversation_id}",
    response_model=ConversationCreateResponse,
    summary="Update Conversation",
    description="Rename a conversation.",
)
def update_conversation(conversation_id: UUID, request: ConversationUpdateRequest, db: Session = Depends(get_db)):
    convo = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not convo:
        raise HTTPException(404, "Conversation not found")
    if request.title is not None:
        convo.title = request.title
    db.commit()
    db.refresh(convo)
    return convo


@router.delete(
    "/{conversation_id}",
    status_code=204,
    summary="Delete Conversation",
    description="Delete a conversation and all its messages permanently.",
)
def delete_conversation(conversation_id: UUID, db: Session = Depends(get_db)):
    convo = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not convo:
        raise HTTPException(404, "Conversation not found")
    db.delete(convo)
    db.commit()
