from uuid import uuid4
from core.db import Base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy import Column, String, ForeignKey, Text


class Documents(Base):
    __tablename__ = "documents"
    id = Column(UUID, primary_key=True, default=uuid4)
    lesson_id = Column(UUID, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    document_url = Column(Text, nullable=False)

    lesson = relationship("Lessons", back_populates="documents")
