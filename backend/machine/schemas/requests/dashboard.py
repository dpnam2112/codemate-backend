from uuid import UUID
from pydantic import BaseModel
from typing import Optional

class WelcomeMessageRequest(BaseModel):
    student_id: UUID

class GetRecentActivitiesRequest(BaseModel):
    student_id: UUID
    limit: int
    offset: Optional[int] = 0 

