from pydantic import BaseModel

class MessageCreateSchema(BaseModel):
    role: str  # Expect 'user' or 'assistant'
    content: str

class InvokeAssistantSchema(BaseModel):
    content: str
