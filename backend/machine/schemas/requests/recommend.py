from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class RecommendLessonRequest(BaseModel):
    lesson_id: UUID
class RecommendModuleRequest(BaseModel):
    module_id: UUID
    