from typing import List,Optional
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime
from core.repository.enum import DifficultyLevel, QuestionType

class DocumentResponse(BaseModel):
    name: str
    type: str 
    document_url: str
    lesson_id: UUID

    class Config:
        from_attributes = True

class CreateNewLessonResponse(BaseModel):
    id: UUID
    title: str
    description: str
    course_id: UUID
    order: int
    learning_outcomes:  Optional[list[str]] = []
    documents: List[DocumentResponse] = []

    class Config:
        from_attributes = True
class PutLessonResponse(BaseModel):
    lesson_id: UUID
    title: str
    description: Optional[str]
    order: int
    learning_outcomes: Optional[list[str]]
class DeleteLessonResponse(BaseModel):
    lesson_id: UUID
    title: str
    description: Optional[str]
    order: int
    learning_outcomes: Optional[list[str]]
class QuestionModel(BaseModel):
    question: str
    answer: List[str]
    options: List[str]
    type: QuestionType
    score: int

class ExerciseQuizResponse(BaseModel):
    exercise_id: UUID
    name: str
    description: Optional[str]
    deadline: Optional[datetime]
    time : Optional[int]
    topic: Optional[str]
    difficulty: DifficultyLevel
    questions: List[QuestionModel]
    lesson_id: UUID
