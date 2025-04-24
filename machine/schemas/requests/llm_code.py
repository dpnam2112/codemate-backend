
from typing import Optional
from pydantic import BaseModel
class QuestionRequest(BaseModel):
    """Model dữ liệu cho câu hỏi gửi đến LLM."""
    content: str
    temperature: float = 0
    max_tokens: Optional[int] = None

class CodeAnalysisRequest(BaseModel):
    """Model dữ liệu cho yêu cầu phân tích code."""
    code: str
    language: int