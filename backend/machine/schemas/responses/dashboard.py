from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from core.repository.enum import ActivityType
class WelcomeMessageResponse(BaseModel):
    course: str
    course_id: UUID
    last_accessed: datetime
    
class GetRecentActivitiesResponse(BaseModel):
    activity_id: UUID
    activity_description: str
    activity_type: ActivityType
    activity_date: datetime
    
