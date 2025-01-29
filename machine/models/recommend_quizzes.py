from uuid import uuid4
from core.db import Base
from sqlalchemy.orm import relationship
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.dialects.postgresql import UUID, JSONB
from core.repository.enum import DifficultyLevel, StatusType
from sqlalchemy import Column, String, ForeignKey, Enum, Float
class RecommendQuizzes(Base):
    __tablename__ = "recommend_quizzes"

    id = Column(UUID, primary_key=True, default=uuid4) # Unique identifier for each recommended quiz
    module_id = Column(UUID, ForeignKey("modules.id", ondelete="CASCADE"), nullable=False) # Foreign key linking the recommended quiz to a specific module in the "modules" table
    name = Column(String, nullable=False) # The name of the recommended quiz
    status = Column(Enum(StatusType), default="new", nullable=False) # The current status of the recommended quiz, represented as an enumerated value (e.g., "new", "in_progress", "completed")
    difficulty = Column(Enum(DifficultyLevel), default="easy",nullable=False) # The difficulty level of the recommended quiz, represented as an enumerated value (e.g., "easy", "medium", "hard")
    score = Column(Float, nullable=True) # The score achieved by the user for this quiz
    max_score = Column(Float, nullable=False) # The maximum score that can be achieved for this quiz
    questions = Column(MutableList.as_mutable(JSONB), nullable=False)
    # Stores the questions of the quiz in JSON format
    # structure defined in QuizExerciseResponse at schema/responses/recommend.py
    module = relationship("Modules", back_populates="quizzes")
  
