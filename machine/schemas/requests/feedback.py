from pydantic import BaseModel
from core.repository.enum import FeedbackCategory, FeedbackType, FeedbackStatusType

class CreateFeedbackRequest(BaseModel):
    type: FeedbackType
    title: str
    category: FeedbackCategory
    description: str
    rate: int
    status: FeedbackStatusType