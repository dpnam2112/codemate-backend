from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from datetime import datetime

class LearningIssue(BaseModel):
    type: str
    description: str
    frequency: int
    related_lessons: List[str] = []
    related_modules: List[str] = []
    last_occurrence: datetime
    
class QuizQuestionResult(BaseModel):
    question_id: UUID
    is_correct: bool

class QuizScoreResponse(BaseModel):
    quiz_id: UUID
    total_questions: int
    correct_answers: int
    score: float 
    results: List[QuizQuestionResult]  
    identified_issues: Optional[List[LearningIssue]] = None
  