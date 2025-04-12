from pydantic import BaseModel
from core.repository.enum import FeedbackCategory, FeedbackType, FeedbackStatusType
from uuid import UUID
from typing import Optional, List
class CreateFeedbackRequest(BaseModel):
    type: FeedbackType
    title: str
    category: FeedbackCategory
    description: str
    rate: int
    status: FeedbackStatusType
    courseId: Optional[str] = None
    professorId: Optional[str] = None
    
class UpdateFeedbackRequest(BaseModel):
    status: FeedbackStatusType