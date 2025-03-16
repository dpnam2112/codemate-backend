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