from typing import Optional
from pydantic import BaseModel, UUID4

class CodeSolutionResponse(BaseModel):
    """
    Schema for code solution response.
    """
    solution: str
    explanation: Optional[str] = None 

    class Config:
        from_attributes = True