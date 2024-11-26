from typing import List
from uuid import UUID
from pydantic import BaseModel

class QuizAnswerRequest(BaseModel):
    quiz_id: UUID
    answers: List[int] 
