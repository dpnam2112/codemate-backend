from uuid import uuid4
from core.db import Base
from sqlalchemy.orm import relationship
from core.db.mixins import TimestampMixin
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, String, UUID, DateTime, Boolean, func

class Professor(Base, TimestampMixin):
    __tablename__ = "professors"

    id = Column(UUID, primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    avatar_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    mscb = Column(String(10), nullable=True)
    date_of_birth = Column(DateTime, nullable=True)
    fullname = Column(String(255), nullable=True)
        
    is_email_verified = Column(Boolean, default=False, nullable=False)
    verification_code = Column(String(6), nullable=True) 
    verification_code_expires_at = Column(DateTime, nullable=True) 

    password_reset_code = Column(String(6), nullable=True) 
    password_reset_code_expires_at = Column(DateTime, nullable=True)

    is_active = Column(Boolean, default=False, nullable=False)
    
    courses = relationship("Courses", back_populates="professor")
