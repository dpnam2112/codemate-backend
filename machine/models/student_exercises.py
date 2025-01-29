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
    student_id = Column(UUID, ForeignKey('student.id', ondelete="CASCADE"), nullable=False, index=True)  # Foreign key linking this record to a specific student in the "student" table
    exercise_id = Column(UUID, ForeignKey('exercises.id', ondelete="CASCADE"), nullable=False, index=True) # Foreign key linking this record to a specific exercise in the "exercises" table
    status = Column(Enum(StatusType), default="new", nullable=False) # The current status of the exercise for the student, represented as an enumerated value (e.g., "new", "in_progress", "completed")
    score = Column(Integer, nullable=True) # The score the student achieved for this exercise
    time_spent = Column(Integer, default=0)  # The total time (in minutes) the student has spent on this exercise
    completion_date = Column(DateTime, nullable=True)  # The date and time when the student completed the exercise
    answer = Column(MutableList.as_mutable(JSONB), nullable=True) 
    # Stores the student's answers in JSON format
    # For quizzes: stores the structure defined in [AnswerQuizExercise].
    exercise = relationship("Exercises", back_populates="student_exercises")
    student = relationship("Student", back_populates="student_exercises")