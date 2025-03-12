from typing import List,Optional, Union, Any
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime
from core.repository.enum import DifficultyLevel, QuestionType, ExerciseType,GradingMethodType
class QuizModal(BaseModel):
    question: str
    answer: List[str]
    options: List[str]
    feedback: str
    type: QuestionType
    difficulty: DifficultyLevel
    score: int
class TestCaseModel(BaseModel):
    input: Any
    output: Any
    is_hidden: Optional[bool] = False
    description: Optional[str] = ""
class CodeModel(BaseModel):
    question: str
    testcases: list[TestCaseModel]
    starter_code: Optional[str] = ""
    solution_code: Optional[str] = ""
    hints: Optional[list[str]] = []
    score: Optional[int] = 10
    difficulty: Optional[DifficultyLevel] = DifficultyLevel.medium
    allowed_languages: Optional[list[str]] = []
    time_limit_seconds: Optional[int] = 5
    memory_limit_mb: Optional[int] = 256
class ExerciseQuizResponse(BaseModel):
    exercise_id: UUID
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
    
class ExerciseCodeResponse(BaseModel):
    exercise_id: UUID
    name: str
    description: Optional[str]
    topic: Optional[str]
    questions: list[CodeModel]
    max_score: Optional[int]
    type: ExerciseType
    course_id: UUID
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
class GetExercise(BaseModel):
    id: UUID
    name: str
    description: str
    type: ExerciseType
    time_open: str
    time_close: str
    time_limit: Optional[int]
    attempts_allowed: int
    grading_method: GradingMethodType