from uuid import UUID
from pydantic import BaseModel
from typing import List
from core.repository.enum import StatusType,DifficultyLevel
from typing import Optional
class DocumentResponse(BaseModel):
    id: UUID
    name: str


class QuizQuestionResponse(BaseModel):
    id: UUID
    question: str
    image: Optional[str] = None
    options: List[str] 
    correct_answer: str 
    explanation: str
    user_choice: Optional[int] = None

class QuizExerciseResponse(BaseModel):
    id: UUID
    name: str
    status: StatusType
    difficulty: DifficultyLevel
    score: float = None  
    questions: List[QuizQuestionResponse]
class QuizListResponse(BaseModel):
    id: UUID
    name: str
    status: StatusType
    difficulty: DifficultyLevel
    score:  Optional[float] = None  
   
    
    
class ModuleResponse(BaseModel):
    module_id: UUID
    title: str
    # description: str
    # objectives: List[str]
    
class ModuleQuizResponse(BaseModel):
    module_id: UUID
    title: str
    objectives: List[str]
    quizzes: List[QuizListResponse]
    

class RecommendLessonResponse(BaseModel):
    lesson_id: UUID
    name: str
    learning_outcomes: List[str]
    description: str
    progress: int
    status: str
    recommend_content: str
    explain: str
    modules: List[ModuleResponse]
    
