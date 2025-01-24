from uuid import UUID
from typing import Optional
from pydantic import BaseModel
from core.repository.enum import ActivityType

class AddActivityRequest(BaseModel):
    student_id: UUID
    type: ActivityType
    description: str
