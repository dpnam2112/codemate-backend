from pydantic import BaseModel

class MessageCreateSchema(BaseModel):
    role: str  # Expect 'user' or 'assistant'
    content: str

class InvokeCodingAssistantSchema(BaseModel):
    content: str
    user_solution: str
    language_id: int
