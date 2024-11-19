from sqlalchemy import Column, DateTime, ForeignKey, UUID
from sqlalchemy.orm import relationship
from core.db import Base
from core.db.mixins import TimestampMixin
from datetime import datetime

class StudentCourses(Base, TimestampMixin):
    __tablename__ = "student_courses"

    student_id = Column(UUID, ForeignKey('users.id'), primary_key=True, nullable=False)
    course_id = Column(UUID, ForeignKey('courses.id'), primary_key=True, nullable=False)
    last_accessed = Column(DateTime, default=datetime.now(), nullable=False)

    course = relationship("Courses", back_populates="student_courses")
