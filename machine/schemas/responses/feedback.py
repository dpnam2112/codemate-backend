from pydantic import BaseModel
from uuid import UUID
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

class GetFeedbackProfessorResponse(BaseModel):
    id: UUID
    type: FeedbackType
    title: str
    category: FeedbackCategory
    description: str
    rate: int
    status: FeedbackStatusType
    created_at: str
    resolved_at: str
    student_id: UUID
    student_name: str
    student_email: str
    
class GetFeedbackListResponse(BaseModel):
    id: str
    type: str
    title: str
    category: str
    description: str
    rate: int
    status: str
    created_at: str
    resolved_at: str
    student_id: str
    student_name: str
    student_email: str
