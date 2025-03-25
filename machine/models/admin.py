from uuid import uuid4
from core.db import Base
from sqlalchemy.orm import relationship
from core.db.mixins import TimestampMixin
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, String, UUID, DateTime, Boolean, Date

class Admin(Base, TimestampMixin):
    __tablename__ = "admins"

    id = Column(UUID, primary_key=True, default=uuid4) # Unique ID for each admin
    name = Column(String(255), nullable=False)  # Username of the admin
    email = Column(String(255), unique=True, nullable=False)    # Email of the admin
    password = Column(String(255), nullable=True)   # Password of the admin
    avatar_url = Column(String, default="documents/326750ef-127e-4d24-b7f1-a9aaa87f40d6-User-avatar.svg.png")  # Avatar URL of the admin
    mscb = Column(String(255), nullable=True)   # Employee ID
    date_of_birth = Column(Date, nullable=True) # Date of birth of the admin
    fullname = Column(String(255), nullable=True)   # Full name of the admin
    
    is_email_verified = Column(Boolean, default=False, nullable=False)  # Email verification status
    verification_code = Column(String(6), nullable=True)    # Verification code
    verification_code_expires_at = Column(DateTime, nullable=True)  # Verification code expiration time

    password_reset_code = Column(String(6), nullable=True)  # Password reset code
    password_reset_code_expires_at = Column(DateTime, nullable=True)    # Password reset code expiration time

    is_active = Column(Boolean, default=False, nullable=False)  # Active status of the admin
