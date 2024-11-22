from sqlalchemy import Column, String, ForeignKey, Enum, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from core.db import Base
from uuid import uuid4
from core.repository.enum import ExerciseType

class Exercises(Base):
    __tablename__ = "exercises"

    id = Column(UUID, primary_key=True, default=uuid4)
    lesson_id = Column(UUID, ForeignKey("lessons.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    type = Column(Enum(ExerciseType), nullable=False)
    duration = Column(Integer, nullable=True) 

    lesson = relationship("Lessons", back_populates="exercises")
    student_exercises = relationship("StudentExercises", back_populates="exercise")

