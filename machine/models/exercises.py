from sqlalchemy import Column, String, ForeignKey, Enum, Integer, DateTime, Boolean, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from core.db import Base
from uuid import uuid4
from core.repository.enum import DifficultyLevel, ExerciseType, GradingMethodType
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableList

class Exercises(Base):
    __tablename__ = "exercises"

    id = Column(UUID, primary_key=True, default=uuid4) # Unique identifier for each exercise
    course_id = Column(UUID, ForeignKey("courses.id"), nullable=False) # Foreign key linking the exercise to a specific course in the "courses" table
    name = Column(String, nullable=False) # The name of the exercise
    description = Column(String, nullable=True)  # A brief description of the exercise
    topic = Column(String, nullable=True) # The topic or subject area of the exercise
    questions = Column(MutableList.as_mutable(JSONB), nullable=False) 
    # For quizzes: stores the structure defined in ExerciseQuizResponse.
    # For coding exercises: stores the structure defined in ExerciseCodeResponse.
    max_score = Column(Integer, nullable=True) # The maximum score that can be achieved for this exercise 
    type = Column(Enum(ExerciseType), nullable=False) # The type of exercise, represented as an enumerated value (e.g., Quiz, Code)
    
    # Timing
    time_open = Column(DateTime, nullable=True)  # When the exercise opens
    time_close = Column(DateTime, nullable=True)  # When the exercise closes
    time_limit = Column(Integer, nullable=True)  # Time limit in minutes
    
    # Attempt settings
    attempts_allowed = Column(Integer, default=1)  # Number of attempts allowed
    grading_method = Column(Enum(GradingMethodType), nullable=False, default=GradingMethodType.highest)  # How the final grade is calculated
    shuffle_questions = Column(Boolean, default=False)  # Whether to shuffle questions
    shuffle_answers = Column(Boolean, default=False)  # Whether to shuffle answers
    
    # Feedback settings
    review_after_completion = Column(Boolean, default=True)  # Allow review after completion
    show_correct_answers = Column(Boolean, default=True)  # Whether to show correct answers after submission
    
    # Penalties & scoring
    penalty_per_attempt = Column(Float, default=0.0)  # Penalty for each incorrect attempt
    pass_mark = Column(Float, nullable=True)  # Minimum score to pass
    course = relationship("Courses", back_populates="exercises")
    student_exercises = relationship("StudentExercises", back_populates="exercise")

