from typing import Optional
from uuid import UUID
from core.controller.base import BaseController
from machine.models.coding_assistant import Conversation


class ConversationController(BaseController[Conversation]):
    """
    Controller for Conversation operations.
    Inherits common CRUD operations from BaseController.
    """
    async def get_conversation(self, conversation_id: UUID) -> Optional[Conversation]:
        # Load conversation along with its messages relationship.
        return await self.repository.first(
            where_=[Conversation.id == conversation_id]
        )
