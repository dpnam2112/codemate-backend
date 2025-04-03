from uuid import uuid4
from core.db import Base
from sqlalchemy.orm import relationship
from core.repository.enum import ActivityType
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, UUID, func

class Activities(Base):
    __tablename__ = "activities"

    id = Column(UUID, primary_key=True, default=uuid4)
    type = Column(String(255), nullable=False)
    description = Column(String(255), nullable=False)
    timestamp = Column(DateTime, default=func.now(), nullable=False)
    student_id = Column(UUID, ForeignKey("student.id"), nullable=False)

    student = relationship("Student", back_populates="activities")