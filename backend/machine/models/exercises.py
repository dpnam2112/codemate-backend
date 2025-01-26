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

    id = Column(UUID, primary_key=True, default=uuid4) # Unique identifier for each exercise
    course_id = Column(UUID, ForeignKey("courses.id"), nullable=False) # Foreign key linking the exercise to a specific course in the "courses" table
    name = Column(String, nullable=False) # The name of the exercise
    description = Column(String, nullable=True)  # A brief description of the exercise
    deadline = Column(DateTime, nullable=True) # The deadline for completing the exercise
    time = Column(Integer, nullable=True)  # The estimated time (in minutes) allocated for completing the exercise
    topic = Column(String, nullable=True) # The topic or subject area of the exercise
    difficulty = Column(Enum(DifficultyLevel), nullable=False) # The difficulty level of the exercise
    questions = Column(MutableList.as_mutable(JSONB), nullable=False) 
    # For quizzes: stores the structure defined in ExerciseQuizResponse.
    # For coding exercises: stores the structure defined in ExerciseCodeResponse.
    max_score = Column(Integer, nullable=True) # The maximum score that can be achieved for this exercise 
    type = Column(Enum(ExerciseType), nullable=False) # The type of exercise, represented as an enumerated value (e.g., Quiz, Code)
    
    course = relationship("Courses", back_populates="exercises")
    student_exercises = relationship("StudentExercises", back_populates="exercise")

