from core.db import Base
from datetime import timedelta
from sqlalchemy.orm import relationship
from sqlalchemy import Column, DateTime, ForeignKey, UUID, Interval, Integer, func
from sqlalchemy.dialects.postgresql import JSONB

class StudentCourses(Base):
    __tablename__ = "student_courses"

    student_id = Column(UUID, ForeignKey('student.id',ondelete="CASCADE"), primary_key=True, nullable=False)
    course_id = Column(UUID, ForeignKey('courses.id',ondelete="CASCADE"), primary_key=True, nullable=False)
    last_accessed = Column(DateTime, default=func.now(), nullable=True)
    completed_lessons = Column(Integer, default=0, nullable=True)
    time_spent = Column(Interval, default=timedelta(0), nullable=True) 
    # Total of time spent in each quiz or code challenges of the course
    percentage_done = Column(Integer, default=0, nullable=True) 
    # Percentage done of the course
    issues_summary = Column(JSONB, nullable=True)
    # Summary of issues found in the course

    course = relationship("Courses", back_populates="student_courses")
    student = relationship("Student", back_populates="student_courses")
