from uuid import UUID
from pydantic import BaseModel, Field
from typing import Optional

class ProgrammingProblemCreateRequest(BaseModel):
    title: str = Field(...)
    description: Optional[str] = None

class ProgrammingLanguageConfigCreateRequest(BaseModel):
    judge0_language_id: int = Field(...)
    boilerplate_code: Optional[str] = None
    time_limit: float = Field(default=1.0)
    memory_limit: int = Field(default=128000)

class ProgrammingTestCaseCreateRequest(BaseModel):
    input: str = Field(...)
    expected_output: str = Field(...)
    is_public: bool = Field(default=False)
    score: float = Field(default=1.0)

class ProgrammingSubmissionCreateRequest(BaseModel):
    exercise_id: UUID
    judge0_language_id: int
    code: str

class ProgrammingLanguageConfigResponse(BaseModel):
    id: UUID
    judge0_language_id: int
    boilerplate_code: Optional[str]
    time_limit: float
    memory_limit: int

    class Config:
        from_attributes = True

class ProgrammingTestCaseResponse(BaseModel):
    id: UUID
    input: str
    expected_output: str
    is_public: bool
    score: float

    class Config:
        from_attributes = True

class ProgrammingSubmissionResponse(BaseModel):
    id: UUID
    exercise_id: UUID
    judge0_language_id: int
    status: str
