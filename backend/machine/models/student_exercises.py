from uuid import uuid4
from core.db import Base
from sqlalchemy.orm import relationship
from core.repository.enum import StatusType
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, ForeignKey, Integer, Text, DateTime, Enum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableList
class StudentExercises(Base):
    __tablename__ = "student_exercises"

    id = Column(UUID, primary_key=True, default=uuid4)
    student_id = Column(UUID, ForeignKey('students.id'), nullable=False, index=True)
    exercise_id = Column(UUID, ForeignKey('exercises.id'), nullable=False, index=True)
    status = Column(Enum(StatusType), default="new", nullable=False)
    score = Column(Integer, nullable=True)
    submission = Column(Text, nullable=True)
    time_spent = Column(Integer, default=0)
    completion_date = Column(DateTime, nullable=True)
    answer = Column(MutableList.as_mutable(JSONB), nullable=True)

    exercise = relationship("Exercises", back_populates="student_exercises")
    student = relationship("Student", back_populates="student_exercises")