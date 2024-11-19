from sqlalchemy import Column, String, ForeignKey, Date, Text, func
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from core.db import Base
from core.db.mixins import TimestampMixin

class Courses(Base, TimestampMixin):
    __tablename__ = "courses"

    id = Column(UUID, primary_key=True, default=func.gen_random_uuid())  # Use gen_random_uuid() for UUID
    name = Column(String(255), nullable=False)
    professor_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    learning_outcomes = Column(ARRAY(Text), nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    status = Column(String(50), default="OPEN", nullable=False)
    image_url = Column(String, nullable=True)

    professor = relationship("User", back_populates="courses")
    student_courses = relationship("StudentCourses", back_populates="course")
