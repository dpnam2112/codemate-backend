from core.db import Base
from uuid import uuid4
from core.db import Base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, String, ForeignKey, DateTime, ARRAY, Text, func, Integer

class Modules(Base):
    __tablename__ = "modules"

    id = Column(UUID, primary_key=True, default=uuid4)
    recommend_lesson_id = Column(UUID, ForeignKey("recommend_lessons.id", ondelete="CASCADE"), nullable=False)
    title = Column(Text, nullable=True)
    objectives = Column(ARRAY(String), nullable=True)
    last_accessed = Column(DateTime, default=func.now(), nullable=False)
    progress = Column(Integer, default=0, nullable=True)
    
    quizzes = relationship("RecommendQuizzes", back_populates="module", cascade="all, delete-orphan")  
    recommendDocuments = relationship("RecommendDocuments", back_populates="module", cascade="all, delete-orphan")
    recommend_lesson = relationship("RecommendLessons", back_populates="modules")    
