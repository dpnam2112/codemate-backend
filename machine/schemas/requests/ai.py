from pydantic import BaseModel
from uuid import UUID

class GenerateLearningPathRequest(BaseModel):
    course_id: UUID
    goal: str