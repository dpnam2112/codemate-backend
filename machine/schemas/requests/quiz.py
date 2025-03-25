from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID

class QuizAnswerRequest(BaseModel):
    quizId: UUID
    answers: Optional[List[str]] = None