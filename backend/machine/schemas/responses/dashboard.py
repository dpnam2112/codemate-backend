from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class WelcomeMessageResponse(BaseModel):
    course: str
    course_id: UUID
    last_accessed: datetime