from core.db import Base
from sqlalchemy import Column, Integer, Text, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4
class ExtractedText(Base):
    __tablename__ = "extracted_texts"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    document_id = Column(UUID, ForeignKey("documents.id"), nullable=False)
    extracted_content = Column(Text, nullable=True)  # Lưu JSON text
    processing_status = Column(String, default="processing", nullable=False)  # "processing", "completed", "failed"

    document = relationship("Documents", back_populates="extracted_text")  # changed here
