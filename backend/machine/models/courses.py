from sqlalchemy import Column, String, ForeignKey, Date, Text, Enum
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from core.db import Base
from core.db.mixins import TimestampMixin
from core.repository.enum import StatusType
from uuid import uuid4

class Courses(Base, TimestampMixin):
    __tablename__ = "courses"

    id = Column(UUID, primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    professor_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    learning_outcomes = Column(ARRAY(Text), nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    status = Column(Enum(StatusType, name="statustype"), default="New", nullable=False)
    image_url = Column(String, nullable=True)


    student_courses = relationship("StudentCourses", back_populates="course")
    professor = relationship("User", back_populates="courses")
    lessons = relationship("Lessons", back_populates="course")


