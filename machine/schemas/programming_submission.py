from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class ProgrammingTestCaseSchema(BaseModel):
    id: UUID
    exercise_id: UUID
    input: str
    expected_output: str
    is_public: bool
    score: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ProgrammingTestResultSchema(BaseModel):
    id: UUID
    submission_id: UUID
    testcase_id: UUID
    judge0_token: str
    status: str
    stdout: Optional[str]
    stderr: Optional[str]
    time: Optional[float]
    memory: Optional[int]
    testcase: ProgrammingTestCaseSchema
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ProgrammingSubmissionItemSchema(BaseModel):
    id: UUID
    user_id: UUID
    exercise_id: UUID
    judge0_language_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class ProgrammingSubmissionSchema(BaseModel):
    id: UUID
    user_id: UUID
    exercise_id: UUID
    judge0_language_id: int
    code: str
    status: str
    score: Optional[float]
    test_results: List[ProgrammingTestResultSchema]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ProgrammingSubmissionStatSchema(BaseModel):
    id: UUID
    user_id: UUID
    exercise_id: UUID
    judge0_language_id: int
    status: str
    passed_testcases: int
    total_testcases: int

class ProgrammingSubmissionCreate(BaseModel):
    user_id: UUID
    exercise_id: UUID
    judge0_language_id: int
    code: str


class ProgrammingSubmissionUpdate(BaseModel):
    status: Optional[str] = None
    score: Optional[float] = None

