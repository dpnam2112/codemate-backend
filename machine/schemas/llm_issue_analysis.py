from pydantic import BaseModel, Field
from typing import List

class IssueAnalysis(BaseModel):
    type: str = Field(..., description="Type of the issue")
    description: str = Field(..., description="Detailed description of the issue")

class IssueAnalysisResponse(BaseModel):
    issues: List[IssueAnalysis] = Field(..., description="List of analyzed issues") 
