from sqlalchemy import Column, String, ForeignKey, Enum, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from core.db import Base
from uuid import uuid4
from core.repository.enum import DifficultyLevel
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableList
class Exercises(Base):
    __tablename__ = "exercises"

    id = Column(UUID, primary_key=True, default=uuid4)
    lesson_id = Column(UUID, ForeignKey("lessons.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    deadline = Column(DateTime, nullable=True)
    time = Column(Integer, nullable=True)
    topic = Column(String, nullable=True)
    attempts = Column(Integer, nullable=True)
    difficulty = Column(Enum(DifficultyLevel), nullable=False)
    questions = Column(MutableList.as_mutable(JSONB), nullable=False)

    lesson = relationship("Lessons", back_populates="exercises")
    student_exercises = relationship("StudentExercises", back_populates="exercise")

