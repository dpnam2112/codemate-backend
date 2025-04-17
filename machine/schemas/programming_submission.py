from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from machine.models.coding_submission import SubmissionStatus

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

class CreateProgrammingSubmissionSchema(BaseModel):
    user_id: UUID
    exercise_id: UUID
    judge0_language_id: int
    code: str

    class Config:
        from_attributes = True


class EvaluationCriteria(BaseModel):
    """
    Represents a single evaluation criterion used by the LLM to assess a code submission.
    """

    name: str = Field(..., description="The name of the evaluation criterion, e.g., 'Correctness', 'Efficiency'.")
    score: float = Field(..., description="The numeric score (out of 10) for this criterion.")
    comment: str = Field(..., description="A detailed comment explaining the score given for this criterion.")

class LLMEvaluation(BaseModel):
    """
    Represents the full evaluation of a submitted solution, as provided by the LLM.
    """

    score: float = Field(..., description="Overall score given by the LLM for the solution.")
    max_score: float = Field(..., description="Maximum possible score. Defaults to 10.")
    summary: str = Field(..., description="A short summary evaluating the overall quality of the solution.")
    criteria: List[EvaluationCriteria] = Field(..., description="A list of detailed scores and comments for each evaluation criterion.")
    improvement_suggestions: List[str] = Field(..., description="Suggestions provided by the LLM to improve the code.")


class ProgrammingSubmissionSchema(BaseModel):
    id: UUID
    user_id: UUID
    exercise_id: UUID
    judge0_language_id: int
    code: str
    status: str
    score: Optional[float]
    test_results: List[ProgrammingTestResultSchema]
    llm_evaluation: Optional[LLMEvaluation] = None
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

class ProgrammingSubmissionBriefSchema(BaseModel):
    id: UUID
    judge0_language_id: int
    status: str
    passed_testcases: int
    total_testcases: int

class ProgrammingSubmissionCreateResponse(BaseModel):
    id: UUID
    status: SubmissionStatus

    class Config:
        from_attributes = True

class ProgrammingSubmissionUpdate(BaseModel):
    status: Optional[str] = None
    score: Optional[float] = None

