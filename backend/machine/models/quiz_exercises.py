from sqlalchemy import Column, String, ForeignKey, Integer, Enum, Float, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from core.repository.enum import DifficultyLevel, StatusType
from uuid import uuid4
from core.db import Base
from sqlalchemy.ext.mutable import MutableList
class QuizExercises(Base):
    __tablename__ = "quiz_exercises"

    id = Column(UUID, primary_key=True, default=uuid4)
    module_id = Column(UUID, ForeignKey("modules.id"), nullable=False)
    name = Column(String, nullable=False)
    status = Column(Enum(StatusType), default="new", nullable=False)
    difficulty = Column(Enum(DifficultyLevel), default="easy",nullable=False)
    score = Column(Float, nullable=True)
    max_score = Column(Float, nullable=False)
    questions = Column(MutableList.as_mutable(JSONB), nullable=False)
    
    module = relationship("Modules", back_populates="quizzes")
  
