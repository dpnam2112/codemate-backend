from enum import StrEnum
from typing import List
from pydantic import BaseModel, Field

class LearningResourceType(StrEnum):
    COURSE = "course"
    LESSON = "lesson"
    CODING_EXERCISE = "coding_exercise"
    PROGRAMMING_ASSIGNMENT = "programming_assignment"


class LearningResource(BaseModel):
    code: str
    title: str = Field(..., description="The title of the learning resource")
    learning_outcomes: List[str] = []
    learning_resource_type: LearningResourceType
    description: str = Field(None, description="A brief description of the learning resource")
