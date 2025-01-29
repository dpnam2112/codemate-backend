from uuid import uuid4
from core.db import Base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, Enum, func
from core.repository.enum import FeedbackCategory, FeedbackType, FeedbackStatusType
from sqlalchemy.orm import relationship

class Feedback(Base):
    __tablename__ = "feedback"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    title = Column(Text, nullable=False)
    category = Column(Enum(FeedbackCategory), default="other", nullable=False)
    description = Column(Text, nullable=True)
    rate = Column(Integer, nullable=False)
    student_id = Column(UUID, ForeignKey("student.id"), nullable=False)
    feedback_type = Column(Enum(FeedbackType), default="system", nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    status = Column(Enum(FeedbackStatusType), default="pending", nullable=False)
    course_id = Column(UUID, ForeignKey("courses.id"), nullable=True)
    
    course = relationship("Courses", back_populates="feedbacks")
    student = relationship("Student", back_populates="feedbacks")
