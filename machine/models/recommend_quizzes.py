from uuid import uuid4
from core.db import Base
from sqlalchemy.orm import relationship
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from core.repository.enum import DifficultyLevel, StatusType, QuestionType
from sqlalchemy import Column, String, ForeignKey, Enum, Float, Integer
class RecommendQuizzes(Base):
    __tablename__ = "recommend_quizzes"

    id = Column(UUID, primary_key=True, default=uuid4) # Unique identifier for each recommended quiz
    module_id = Column(UUID, ForeignKey("modules.id", ondelete="CASCADE"), nullable=False) # Foreign key linking the recommended quiz to a specific module in the "modules" table
    name = Column(String, nullable=False) # The name of the recommended quiz
    description = Column(String, nullable=True)  # A brief description of the exercise
    status = Column(Enum(StatusType), default="new", nullable=False) # The current status of the recommended quiz, represented as an enumerated value (e.g., "new", "in_progress", "completed")
    score = Column(Float, nullable=True) # The score achieved by the user for this quiz
    max_score = Column(Float, nullable=False) # The maximum score that can be achieved for this quiz
    time_limit = Column(Integer, nullable=True)  # Time limit in minutes
    duration = Column(Integer, nullable=True)
    module = relationship("Modules", back_populates="quizzes")
    questions = relationship("RecommendQuizQuestion", back_populates="quiz")
  
class RecommendQuizQuestion(Base):
    __tablename__ = "recommend_quiz_questions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    quiz_id = Column(UUID(as_uuid=True), ForeignKey("recommend_quizzes.id"), nullable=False)
    question_text = Column(String, nullable=False)
    question_type = Column(String, nullable=False, default=QuestionType.single_choice)  # multiple_choice, true_false, short_answer
    options = Column(ARRAY(String), nullable=True)  # Array of options
    correct_answer = Column(ARRAY(String), nullable=False)  # Can be string or array for multiple correct answers
    difficulty = Column(Enum(DifficultyLevel), default="easy",nullable=False) # The difficulty level of the recommended quiz, represented as an enumerated value (e.g., "easy", "medium", "hard")
    explanation = Column(String, nullable=True)
    points = Column(Float, default=10)
    user_choice = Column(ARRAY(String), nullable=True)
    
    quiz = relationship("RecommendQuizzes", back_populates="questions")