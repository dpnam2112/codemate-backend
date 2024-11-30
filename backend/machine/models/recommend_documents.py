from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from core.db import Base
from uuid import uuid4
from sqlalchemy.ext.mutable import MutableDict
class RecommendDocuments(Base):
    __tablename__ = "recommendDocuments"


    id = Column(UUID, primary_key=True, default=uuid4)
    module_id = Column(UUID, ForeignKey("modules.id"), nullable=False)
    content = Column(MutableDict.as_mutable(JSONB), nullable=False)
    
    module = relationship("Modules", back_populates="recommendDocuments")
    