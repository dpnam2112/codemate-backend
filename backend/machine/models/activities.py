from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, UUID, func
from sqlalchemy.orm import relationship
from core.db import Base
from uuid import uuid4
from core.repository.enum import ActivityType

class Activities(Base):
    __tablename__ = "activities"

    id = Column(UUID, primary_key=True, default=uuid4)
    type = Column(Enum(ActivityType, name="activitytype"), nullable=False)
    description = Column(String(255), nullable=False)  
    timestamp = Column(DateTime, default=func.now(), nullable=False) 
    student_id = Column(UUID, ForeignKey("users.id"), nullable=False)

    student = relationship("User", back_populates="activities")
