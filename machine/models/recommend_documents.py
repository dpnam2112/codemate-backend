from uuid import uuid4
from core.db import Base
from sqlalchemy.orm import relationship
from sqlalchemy import Column, ForeignKey
from sqlalchemy import Column, ForeignKey
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import JSONB
class RecommendDocuments(Base):
    __tablename__ = "recommendDocuments"


    id = Column(UUID, primary_key=True, default=uuid4)
    module_id = Column(UUID, ForeignKey("modules.id", ondelete="CASCADE"), nullable=False)
    content = Column(MutableDict.as_mutable(JSONB), nullable=False)
    # For content: stores the structure defined in DocumentResponse.
    module = relationship("Modules", back_populates="recommendDocuments")
    