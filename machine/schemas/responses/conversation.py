from pydantic import BaseModel
from uuid import UUID

class MessageResponseSchema(BaseModel):
    id: int
    role: str
    content: str

    model_config = {"from_attributes": True}  # Enable orm_mode

class ConversationResponseSchema(BaseModel):
    id: UUID

    model_config = {"from_attributes": True}
