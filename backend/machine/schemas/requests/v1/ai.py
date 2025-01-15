from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class LearningPathPlanningRequest(BaseModel):
    course_id: UUID
    user_id: UUID
    goal: Optional[str]
