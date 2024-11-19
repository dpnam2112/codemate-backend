from sqlalchemy import Column, String, UUID, Enum, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from core.db import Base
from core.db.mixins import TimestampMixin
from datetime import datetime
from enum import Enum as PyEnum 
from sqlalchemy.orm import relationship

# Define UserRole using Python's Enum class
class UserRole(PyEnum):
    student = "student"
    professor = "professor"
    admin = "admin"

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(UUID, primary_key=True, default=func.gen_random_uuid())  # UUID field with auto-gen
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)  # Email must be unique
    avatar_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)  # Default to current UTC time
    role = Column(Enum(UserRole), nullable=False, default=UserRole.student)  # Correct Enum usage

    # Relationship with Courses (professors teach courses)
    courses = relationship("Courses", back_populates="professor")
