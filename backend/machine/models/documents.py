from sqlalchemy import Column, String, ForeignKey
from sqlalchemy import Column, String, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from core.db import Base

class Documents(Base):
    __tablename__ = "documents"
    lesson_id = Column(UUID, ForeignKey("lessons.id"), nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  
    document_url = Column(Text, nullable=False) 

    lesson = relationship("Lessons", back_populates="documents") 
