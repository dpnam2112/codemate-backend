from core.db import Base
from datetime import timedelta
from sqlalchemy.orm import relationship
from sqlalchemy import Column, DateTime, ForeignKey, UUID, Interval, Integer, func
from sqlalchemy.dialects.postgresql import JSONB
from pydantic import BaseModel, Field
from typing import List
from datetime import datetime

class LearningIssue(BaseModel):
    """Schema for a single learning issue identified in student's performance."""
    type: str = Field(
        ...,
        description="Type of the issue (e.g., concept_misunderstanding, quiz_failure, knowledge_gap)",
        examples=["concept_misunderstanding", "quiz_failure", "knowledge_gap"]
    )
    description: str = Field(
        ...,
        description="Detailed description of the specific difficulty faced",
        min_length=10
    )
    frequency: int = Field(
        ...,
        description="Number of times this issue has been observed",
        ge=1
    )
    related_lessons: List[str] = Field(
        default_factory=list,
        description="List of lesson IDs where this issue was observed"
    )
    last_occurrence: datetime = Field(
        ...,
        description="Timestamp of when this issue was last observed"
    )

class IssuesSummary(BaseModel):
    """Schema for the complete issues summary stored in student_courses."""
    common_issues: List[LearningIssue] = Field(
        default_factory=list,
        description="List of identified learning issues"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "common_issues": [
                    {
                        "type": "concept_misunderstanding",
                        "description": "Difficulty understanding recursion in Python",
                        "frequency": 3,
                        "related_lessons": ["lesson-1", "lesson-2"],
                        "related_modules": ["module-1"],
                        "last_occurrence": "2024-04-17T10:00:00Z"
                    }
                ]
            }
        }
        
        from_attributes = True

class StudentCourses(Base):
    __tablename__ = "student_courses"

    student_id = Column(UUID, ForeignKey('student.id',ondelete="CASCADE"), primary_key=True, nullable=False)
    course_id = Column(UUID, ForeignKey('courses.id',ondelete="CASCADE"), primary_key=True, nullable=False)
    last_accessed = Column(DateTime, default=func.now(), nullable=True)
    completed_lessons = Column(Integer, default=0, nullable=True)
    time_spent = Column(Interval, default=timedelta(0), nullable=True) 
    # Total of time spent in each quiz or code challenges of the course
    percentage_done = Column(Integer, default=0, nullable=True) 
    # Percentage done of the course
    issues_summary = Column(JSONB, nullable=True)
    achievements = Column(JSONB, nullable=True)
    # Summary of issues found in the course

    course = relationship("Courses", back_populates="student_courses")
    student = relationship("Student", back_populates="student_courses")
