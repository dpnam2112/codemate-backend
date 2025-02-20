from uuid import uuid4
from core.db import Base
from sqlalchemy.orm import relationship
from core.db.mixins import TimestampMixin
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, String, UUID, DateTime, Boolean, Date

class Professor(Base, TimestampMixin):
    __tablename__ = "professors"

    id = Column(UUID, primary_key=True, default=uuid4)  # Unique ID for each professor
    name = Column(String(255), nullable=False)  # Username of the professor
    email = Column(String(255), unique=True, nullable=False)    # Email of the professor
    password = Column(String(255), nullable=True)   # Password of the professor
    avatar_url = Column(String, nullable=True)  # Avatar URL of the professor
    mscb = Column(String(10), nullable=True)    # Employee ID
    date_of_birth = Column(Date, nullable=True) # Date of birth of the professor
    fullname = Column(String(255), nullable=True)   # Full name of the professor
        
    is_email_verified = Column(Boolean, default=False, nullable=False)  # Email verification status
    verification_code = Column(String(6), nullable=True)    # Verification code
    verification_code_expires_at = Column(DateTime, nullable=True)  # Verification code expiration time

    password_reset_code = Column(String(6), nullable=True)  # Password reset code
    password_reset_code_expires_at = Column(DateTime, nullable=True)    # Password reset code expiration time

    is_active = Column(Boolean, default=False, nullable=False)  # Active status of the professor
    
    courses = relationship("Courses", back_populates="professor")
    feedbacks = relationship("Feedback", back_populates="professor", lazy='dynamic')