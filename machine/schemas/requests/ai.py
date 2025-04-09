from pydantic import BaseModel
from uuid import UUID

class GenerateLearningPathRequest(BaseModel):
    course_id: UUID
    goal: str

class GenerateQuizRequest(BaseModel):
    module_id: UUID

class GenerateCodeExerciseRequest(BaseModel):
    module_id: UUID
