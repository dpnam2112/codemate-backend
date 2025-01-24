
from sqlalchemy import Column, Integer, Text, ARRAY, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4
from sqlalchemy.orm import relationship
from core.db import Base
from core.repository.enum import StatusType

class RecommendLessons(Base):
    __tablename__ = "recommend_lessons"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    learning_path_id = Column(UUID, ForeignKey("learning_paths.id"), nullable=False)
    lesson_id = Column(UUID, ForeignKey("lessons.id"), nullable=True)
    progress = Column(Integer, default=0, nullable=False)
    recommended_content = Column(Text, nullable=True)
    explain = Column(Text, nullable=True)
    status = Column(Enum(StatusType), default="new", nullable=False)
    
    lesson = relationship("Lessons", back_populates="recommend_lesson")
    learning_path = relationship("LearningPaths", back_populates="recommend_lessons")
    modules = relationship("Modules", back_populates="recommend_lesson", cascade="all, delete-orphan")
