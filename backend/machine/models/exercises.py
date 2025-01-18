from sqlalchemy import Column, String, ForeignKey, Enum, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from core.db import Base
from uuid import uuid4
from core.repository.enum import DifficultyLevel, ExerciseType
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableList

class Exercises(Base):
    __tablename__ = "exercises"

    id = Column(UUID, primary_key=True, default=uuid4)
    course_id = Column(UUID, ForeignKey("courses.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    deadline = Column(DateTime, nullable=True)
    time = Column(Integer, nullable=True)
    topic = Column(String, nullable=True)
    attempts = Column(Integer, nullable=True)
    difficulty = Column(Enum(DifficultyLevel), nullable=False)
    questions = Column(MutableList.as_mutable(JSONB), nullable=False) #Quiz rule in schema lesson (ExerciseQuizResponse) & Code rule in schema lesson (ExerciseCodeResponse)
    max_score = Column(Integer, nullable=True)
    type = Column(Enum(ExerciseType), nullable=False)
    
    course = relationship("Courses", back_populates="exercises")
    student_exercises = relationship("StudentExercises", back_populates="exercise")

