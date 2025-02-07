from sqlalchemy import Column, String, ForeignKey, DateTime, ARRAY, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from core.db import Base
from uuid import uuid4

class Modules(Base):
    __tablename__ = "modules"

    id = Column(UUID, primary_key=True, default=uuid4)
    recommend_lesson_id = Column(UUID, ForeignKey("recommend_lessons.id", ondelete="CASCADE"), nullable=False)
    title = Column(Text, nullable=True)
    objectives = Column(ARRAY(String), nullable=True)
    last_accessed = Column(DateTime, default=func.now(), nullable=False)
    
    quizzes = relationship("QuizExercises", back_populates="module", cascade="all, delete-orphan")
    recommendDocuments = relationship("RecommendDocuments", back_populates="module", cascade="all, delete-orphan")
    recommend_lesson = relationship("RecommendLessons", back_populates="modules")    
