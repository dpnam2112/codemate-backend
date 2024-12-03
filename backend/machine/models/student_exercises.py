from sqlalchemy import Column, ForeignKey, Integer, Text, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from core.db import Base
from uuid import uuid4
from core.repository.enum import StatusType

class StudentExercises(Base):
    __tablename__ = "student_exercises"

    id = Column(UUID, primary_key=True, default=uuid4)
    student_id = Column(UUID, ForeignKey('users.id'), nullable=False, index=True)  
    exercise_id = Column(UUID, ForeignKey('exercises.id'), nullable=False, index=True) 
    status = Column(Enum(StatusType), default="new", nullable=False) 
    score = Column(Integer, nullable=True) 
    submission = Column(Text, nullable=True) 
    time_spent = Column(Integer, default=0)
    completion_date = Column(DateTime, nullable=True)

    exercise = relationship("Exercises", back_populates="student_exercises")
    student = relationship("User", back_populates="student_exercises")