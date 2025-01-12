from core.db import Base
from sqlalchemy.orm import relationship
from sqlalchemy import Column, ForeignKey, UUID, Boolean

class StudentLessons(Base):
    __tablename__ = "student_lessons"

    student_id = Column(UUID, ForeignKey('students.id'), primary_key=True, nullable=False)
    lesson_id = Column(UUID, ForeignKey('lessons.id'), primary_key=True, nullable=False)
    course_id = Column(UUID, ForeignKey('courses.id'), primary_key=True, nullable=False)
    bookmark = Column(Boolean, default=False, nullable=False)
    
    lesson = relationship("Lessons", back_populates="student_lessons")
    student = relationship("Student", back_populates="student_lessons")
    course = relationship("Courses", back_populates="student_lessons")
