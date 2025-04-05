# File: machine/api/v1/conversations.py
from __future__ import annotations
from uuid import UUID
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.response.api_response import Ok  # Generic response wrapper
from machine.providers.internal import InternalProvider
from machine import controllers as ctrl

# ------------------------------------------------------------------------------
# Pydantic Schemas (using pydantic v2)
# ------------------------------------------------------------------------------

class MessageCreateSchema(BaseModel):
    role: str  # Expect 'user' or 'assistant'
    content: str

class MessageResponseSchema(BaseModel):
    id: int
    role: str
    content: str

    model_config = {"from_attributes": True}  # Enable orm_mode

class ConversationResponseSchema(BaseModel):
    id: UUID

    model_config = {"from_attributes": True}

class ConversationCreateRequest(BaseModel):
    # Optionally, an initial message may be provided when creating a conversation.
    initial_message: Optional[MessageCreateSchema] = None

# ------------------------------------------------------------------------------
# FastAPI Router
# ------------------------------------------------------------------------------

router = APIRouter(prefix="/conversations")

@router.post(
    "",
    response_model=Ok[ConversationResponseSchema],
    summary="Create a new conversation"
)
async def create_conversation(
    conversation_controller: ctrl.ConversationController = Depends(InternalProvider().get_conversation_controller)
) -> Ok[ConversationResponseSchema]:
    # Create a new conversation (no additional attributes required)
    conversation = await conversation_controller.create({})
    # If an initial message is provided, add it to the conversation.
    return Ok(data=ConversationResponseSchema.model_validate(conversation))


@router.get(
    "/{conversation_id}/messages",
    response_model=Ok[List[MessageResponseSchema]],
    summary="Retrieve all messages for a conversation"
)
async def get_conversation_messages(
    conversation_id: UUID,
    conversation_controller: ctrl.ConversationController = Depends(InternalProvider().get_conversation_controller)
) -> Ok[List[MessageResponseSchema]]:
    conversation = await conversation_controller.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = conversation.messages or []
    response = [MessageResponseSchema.model_validate(msg) for msg in messages]
    return Ok(data=response)
