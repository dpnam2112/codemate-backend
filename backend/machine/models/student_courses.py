from sqlalchemy import Column, DateTime, ForeignKey, UUID, Interval, Integer, func
from sqlalchemy.orm import relationship
from core.db import Base
from datetime import timedelta

class StudentCourses(Base):
    __tablename__ = "student_courses"

    student_id = Column(UUID, ForeignKey('users.id'), primary_key=True, nullable=False)
    course_id = Column(UUID, ForeignKey('courses.id'), primary_key=True, nullable=False)
    last_accessed = Column(DateTime, default=func.now(), nullable=False)
    completed_lessons = Column(Integer, default=0, nullable=False)
    time_spent = Column(Interval, default=timedelta(0), nullable=False)
    assignments_done = Column(Integer, default=0, nullable=False)

    course = relationship("Courses", back_populates="student_courses")
    #lessons = relationship("Lessons", secondary="student_lessons") 
