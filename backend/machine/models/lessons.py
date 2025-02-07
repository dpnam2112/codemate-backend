from sqlalchemy import Column, String, ForeignKey, Integer, Enum, Text, ARRAY
from sqlalchemy import Column, String, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from core.db import Base
from uuid import uuid4
from core.repository.enum import LessonType

class Lessons(Base):
    __tablename__ = "lessons"

    id = Column(UUID, primary_key=True, default=uuid4)
    course_id = Column(UUID, ForeignKey("courses.id"), nullable=False)  
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    order = Column(Integer, nullable=False) 
    learning_outcomes = Column(ARRAY(Text), nullable=True)

    course = relationship("Courses", back_populates="lessons")
    exercises = relationship("Exercises", back_populates="lesson")
    student_lessons = relationship("StudentLessons", back_populates="lesson")
    documents = relationship("Documents", back_populates="lesson") 
    recommend_lesson = relationship("RecommendLessons", back_populates="lesson")
