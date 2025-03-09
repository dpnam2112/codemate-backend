from pydantic import BaseModel
from core.repository.enum import FeedbackCategory, FeedbackType, FeedbackStatusType
from uuid import UUID
class CreateFeedbackRequest(BaseModel):
    type: FeedbackType
    title: str
    category: FeedbackCategory
    description: str
    rate: int
    status: FeedbackStatusType
class CreateFeedbackCourseRequest(BaseModel):
    type: FeedbackType
    title: str
    category: FeedbackCategory
    description: str
    rate: int
    status: FeedbackStatusType
    course_id: UUID
    