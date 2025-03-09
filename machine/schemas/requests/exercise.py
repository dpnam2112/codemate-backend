from pydantic import BaseModel
from typing import Optional, Union, List
from uuid import UUID
from datetime import datetime
from core.repository.enum import DifficultyLevel, QuestionType, ExerciseType, GradingMethodType
class QuizModal(BaseModel):
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
    course_id: UUID
    name: str
    description: Optional[str]
    topic: Optional[str]
    questions: List[QuizModal]
    max_score: Optional[int]
    type: ExerciseType
    time_open: Optional[datetime]
    time_close: Optional[datetime]
    time_limit: Optional[int]
    attempts_allowed: Optional[int]
    grading_method: GradingMethodType
    shuffle_questions: Optional[bool]
    shuffle_answers: Optional[bool]
    review_after_completion: Optional[bool]
    show_correct_answers: Optional[bool]
    penalty_per_attempt: Optional[float]
    pass_mark: Optional[float]
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