from sqlalchemy import Column, DateTime, Integer, String, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from core.db import Base
from uuid import uuid4
from datetime import datetime
from sqlalchemy import UniqueConstraint
class LearningPaths(Base):
    __tablename__ = "learning_paths"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    start_date = Column(DateTime, default=datetime.utcnow, nullable=True)
    end_date = Column(DateTime, nullable=True)
    objective = Column(String, nullable=True)
    progress = Column(Float, default=0.0, nullable=False)
    
    student_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    course_id = Column(UUID, ForeignKey("courses.id"), nullable=False)
    
    student = relationship("User", back_populates="learning_paths")
    course = relationship("Courses", back_populates="learning_paths")
    recommend_lessons = relationship("RecommendLessons", back_populates="learning_path")
    
    __table_args__ = (
        UniqueConstraint('student_id', 'course_id', name='uq_student_course'),
    )