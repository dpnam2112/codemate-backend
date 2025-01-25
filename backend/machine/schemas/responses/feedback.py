from pydantic import BaseModel
from core.repository.enum import FeedbackCategory, FeedbackType, FeedbackStatusType
class CreateFeedbackResponse(BaseModel):
    id: str
    type: FeedbackType
    title: str
    category: FeedbackCategory
    description: str
    rate: int
    status: FeedbackStatusType
    created_at: str
    resolved_at: str