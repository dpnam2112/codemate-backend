from uuid import uuid4
from core.db import Base
from sqlalchemy.orm import relationship
from core.db.mixins import TimestampMixin
from core.repository.enum import StatusType
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy import Column, String, ForeignKey, Date, Text, Enum, Integer


class Courses(Base, TimestampMixin):
    __tablename__ = "courses"

    id = Column(UUID, primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    professor_id = Column(UUID, ForeignKey("professors.id"), nullable=False)
    learning_outcomes = Column(ARRAY(Text), nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    status = Column(Enum(StatusType, name="statustype"), default="new", nullable=False)
    image_url = Column(String, nullable=True)
    nCredit = Column(Integer, nullable=True)
    nSemester = Column(Integer, nullable=True)
    courseID = Column(String, nullable=True)
    createdByAdminID = Column(String, nullable=True)

    student_courses = relationship("StudentCourses", back_populates="course")
    professor = relationship("Professor", back_populates="courses")
    lessons = relationship("Lessons", back_populates="course")
    exercises = relationship("Exercises", back_populates="course")
    student_lessons = relationship("StudentLessons", back_populates="course")
    learning_paths = relationship("LearningPaths", back_populates="course")
