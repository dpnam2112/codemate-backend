from pydantic import BaseModel
from typing import List
class LLMResponse(BaseModel):
    """Model dữ liệu cho kết quả từ LLM."""
    answer: str
    model_used: str

class CodeExplanation(BaseModel):
    """Model dữ liệu cho giải thích của một dòng code."""
    line: int
    code: str
    explanation: str

class CodeAnalysisResponse(BaseModel):
    """Model dữ liệu cho kết quả phân tích code."""
    explanations: List[CodeExplanation]
    
class QuizQuestion(BaseModel):
    question_text: str
    question_type: str
    options: List[str]
    correct_answer: List[str]
    difficulty: str
    explanation: str
    points: int

class Quiz(BaseModel):
    quiz_title: str
    description: str
    estimated_completion_time: str
    max_score: int
    questions: List[QuizQuestion]
