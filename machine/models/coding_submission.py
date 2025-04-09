"""
Workflow:
    - Teacher creates a ProgrammingProblem.
    - Teacher adds multiple ProgrammingLanguageConfig rows (Python, C++, etc.).
    - Student chooses a language and writes code.

Judge0 evaluates it using:
- The chosen language
- The problem's test cases
- The selected config (boilerplate + limits)

"""
from typing import Optional
from uuid import UUID, uuid4
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import String, Text, Float, Integer, Boolean, ForeignKey, UniqueConstraint
from core.db import Base
from core.db.mixins import TimestampMixin
from enum import Enum

JUDGE0_LANG = {
    "C": 50,
    "C++": 54,
    "C++17": 59,
    "C++20": 76,
    "C#": 51,
    "Java": 62,
    "JavaScript": 63,
    "Python2": 70,
    "Python3": 71,
    "Go": 60,
    "Ruby": 72,
    "Rust": 73,
    "Swift": 83,
    "Kotlin": 78,
    "TypeScript": 74,
    "PHP": 68,
    "Perl": 85,
    "Scala": 81,
    "Haskell": 61,
    "Lua": 64,
    "R": 80
}

class SubmissionStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"

class ProgrammingLanguageConfig(Base, TimestampMixin):
    __tablename__ = "programming_language_configs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    exercise_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("exercises.id", ondelete="CASCADE"))
    judge0_language_id: Mapped[int] = mapped_column(Integer, nullable=False)
    boilerplate_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    time_limit: Mapped[float] = mapped_column(Float, default=1.0)
    memory_limit: Mapped[int] = mapped_column(Integer, default=128000)

    __table_args__ = (
        UniqueConstraint("exercise_id", "judge0_language_id", name="uq_problem_language"),
    )

class ProgrammingTestCase(Base, TimestampMixin):
    __tablename__ = "programming_testcases"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    exercise_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("exercises.id", ondelete="CASCADE"))
    input: Mapped[str] = mapped_column(Text, nullable=False)
    expected_output: Mapped[str] = mapped_column(Text, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    score: Mapped[float] = mapped_column(Float, default=1.0)

class ProgrammingSubmission(Base, TimestampMixin):
    __tablename__ = "programming_submissions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("student.id"), nullable=False)
    exercise_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("exercises.id"), nullable=False)
    judge0_language_id: Mapped[int] = mapped_column(Integer, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[SubmissionStatus] = mapped_column(String, default="pending")
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    test_results: Mapped[list["ProgrammingTestResult"]] = relationship("ProgrammingTestResult", lazy="selectin")

class ProgrammingTestResult(Base, TimestampMixin):
    __tablename__ = "programming_test_results"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    submission_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("programming_submissions.id", ondelete="CASCADE"))
    testcase_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("programming_testcases.id", ondelete="CASCADE"))
    judge0_token: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    stdout: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stderr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    time: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    memory: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    testcase: Mapped["ProgrammingTestCase"] = relationship("ProgrammingTestCase", lazy="selectin")

    submission: Mapped["ProgrammingSubmission"] = relationship(back_populates="test_results")

