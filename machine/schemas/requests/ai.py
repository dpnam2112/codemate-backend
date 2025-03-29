from pydantic import BaseModel, Field, validator
from typing import Optional
from uuid import UUID

class GenerateLearningPathRequest(BaseModel):
    course_id: UUID
    goal: str
class DifficultyDistribution(BaseModel):
    easy: Optional[int] = Field(default=10, ge=0, le=40, description="Number of easy questions")
    medium: Optional[int] = Field(default=20, ge=0, le=40, description="Number of medium questions")
    hard: Optional[int] = Field(default=10, ge=0, le=40, description="Number of hard questions")

    @validator('easy', 'medium', 'hard')
    def validate_total_questions(cls, v, values, **kwargs):
        # Ensure total questions do not exceed 40
        total_questions = (
            values.get('easy', 0) + 
            values.get('medium', 0) + 
            values.get('hard', 0)
        )
        if total_questions > 40:
            raise ValueError("Total number of questions cannot exceed 40")
        return v

class GenerateQuizRequest(BaseModel):
    module_id: UUID
    difficulty_distribution: Optional[DifficultyDistribution] = Field(
        default_factory=DifficultyDistribution,
        description="Distribution of questions by difficulty level"
    )
