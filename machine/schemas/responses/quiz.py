from typing import List
from uuid import UUID
from pydantic import BaseModel

class QuizQuestionResult(BaseModel):
    question_id: UUID
    is_correct: bool

class QuizScoreResponse(BaseModel):
    quiz_id: UUID
    total_questions: int
    correct_answers: int
    score: float 
    results: List[QuizQuestionResult]  

  