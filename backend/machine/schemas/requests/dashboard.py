from uuid import UUID
from typing import Optional
from pydantic import BaseModel
from core.repository.enum import ActivityType

class GetRecentActivitiesRequest(BaseModel):
    student_id: UUID
    limit: int
    offset: Optional[int] = 0 

class AddActivityRequest(BaseModel):
    student_id: UUID
    type: ActivityType
    description: str
