from uuid import UUID
from pydantic import BaseModel


class RecommendLearningResourcesRequest(BaseModel):
    course_id: UUID
    user_id: UUID
    goal: str
