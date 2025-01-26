from typing import List,Optional, Union
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime
from core.repository.enum import DifficultyLevel, QuestionType, ExerciseType
class QuestionModel(BaseModel):
    question: str
    answer: List[str]
    options: List[str]
    type: QuestionType
    score: int
class TestCaseModel(BaseModel):
    input: Union[str, int, float, dict, list, bool]
    output: Union[str, int, float, dict, list, bool]
class CodeModel(BaseModel):
    question: str
    testcases: list[TestCaseModel]
class ExerciseQuizResponse(BaseModel):
    exercise_id: UUID
    name: str
    description: Optional[str]
    deadline: Optional[datetime]
    time : Optional[int]
    topic: Optional[str]
    difficulty: DifficultyLevel
    questions: List[QuestionModel]
    max_score: Optional[int]
    type: ExerciseType
    course_id: UUID
class PutExerciseQuizResponse(BaseModel):
    exercise_id: UUID
    name: str
    description: Optional[str]
    deadline: Optional[datetime]
    time : Optional[int]
    topic: Optional[str]
    difficulty: DifficultyLevel
    questions: List[QuestionModel]
    max_score: Optional[int]
    type: ExerciseType
class ExerciseCodeResponse(BaseModel):
    exercise_id: UUID
    name: str
    description: Optional[str]
    deadline: Optional[datetime]
    time : Optional[int]
    topic: Optional[str]
    difficulty: DifficultyLevel
    questions: list[CodeModel]
    max_score: Optional[int]
    type: ExerciseType
    course_id: UUID
class PutExerciseCodeResponse(BaseModel):
    exercise_id: UUID
    name: str
    description: Optional[str]
    deadline: Optional[datetime]
    time : Optional[int]
    topic: Optional[str]
    difficulty: DifficultyLevel
    questions: list[CodeModel]
    max_score: Optional[int]
    type: ExerciseType