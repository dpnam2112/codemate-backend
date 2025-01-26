from pydantic import BaseModel
from typing import Optional, Union, List
from uuid import UUID
from datetime import datetime
from core.repository.enum import DifficultyLevel, QuestionType, ExerciseType
class QuestionModel(BaseModel):
    question: str
    answer: list[str]
    options: list[str]
    type: QuestionType
    score: int
class TestCaseModel(BaseModel):
    input: Union[str, int, float, dict, list, bool]
    output: Union[str, int, float, dict, list, bool]
class CodeModel(BaseModel):
    question: str
    testcases: List[TestCaseModel]
class ExerciseRequest(BaseModel):
    name: str
    description: Optional[str]
    deadline: Optional[datetime]
    time : Optional[int]
    topic: Optional[str]
    difficulty: DifficultyLevel
    questions: list[QuestionModel]
    max_score: Optional[int]
    type: ExerciseType
    course_id: UUID
class ExerciseCodeRequest(BaseModel):
    name: str
    description: Optional[str]
    deadline: Optional[datetime]
    time : Optional[int]
    topic: Optional[str]
    difficulty: DifficultyLevel
    questions: list[CodeModel]
    code: str
    max_score: Optional[int]
    type: ExerciseType
    course_id: UUID