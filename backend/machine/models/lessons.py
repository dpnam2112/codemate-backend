from sqlalchemy import Column, String, ForeignKey, Integer, Enum, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from core.db import Base
from uuid import uuid4
from core.repository.enum import LessonType, StatusType

class Lessons(Base):
    __tablename__ = "lessons"

    id = Column(UUID, primary_key=True, default=uuid4)
    course_id = Column(UUID, ForeignKey("courses.id"), nullable=False)  
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    lesson_type = Column(Enum(LessonType), nullable=False)
    bookmark = Column(Boolean, default=False, nullable=False)
    order = Column(Integer, nullable=False)
    status = Column(Enum(StatusType), default="New", nullable=False)

    course = relationship("Courses", back_populates="lessons")
    exercises = relationship("Exercises", back_populates="lesson")

