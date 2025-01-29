from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional

class ModuleDTO(BaseModel):
    id: UUID = Field(..., description="Unique identifier for the module.")
    recommend_lesson_id: UUID = Field(..., description="ID of the associated recommended lesson.")
    title: Optional[str] = Field(None, description="Title of the module.")
    objectives: Optional[list[str]] = Field(None, description="List of objectives for the module.")
    last_accessed: datetime = Field(..., description="Last accessed timestamp of the module.")

    class Config:
        from_attributes = True


class RecommendedLessonDTO(BaseModel):
    id: UUID = Field(..., description="Unique identifier for the recommended lesson.")
    learning_path_id: UUID = Field(..., description="ID of the associated learning path.")
    lesson_id: Optional[UUID] = Field(None, description="ID of the associated lesson.")
    progress: int = Field(..., description="Progress of the lesson, represented as a percentage.")
    explain: Optional[str] = Field(None, description="Explanation for why the lesson is recommended.")
    status: str = Field(..., description="Status of the recommended lesson.")
    modules: Optional[list[ModuleDTO]] = Field(None, description="Modules associated with the recommended lesson.")

    class Config:
        from_attributes = True


class LearningPathDTO(BaseModel):
    id: UUID = Field(..., description="Unique identifier for the learning path.")
    start_date: Optional[datetime] = Field(None, description="Start date of the learning path.")
    end_date: Optional[datetime] = Field(None, description="End date of the learning path.")
    objective: Optional[str] = Field(None, description="Objective of the learning path.")
    progress: float = Field(..., description="Progress of the learning path, represented as a percentage.")

    class Config:
        from_attributes = True
