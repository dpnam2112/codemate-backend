from sqlalchemy import Column, String, UUID, Enum, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from core.db import Base
from core.db.mixins import TimestampMixin
from datetime import datetime
from enum import Enum as PyEnum 


class UserRole(PyEnum):
    student = "student"
    professor = "professor"
    admin = "admin"

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(UUID, primary_key=True, default=func.gen_random_uuid()) 
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False) 
    avatar_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now()) 
    role = Column(Enum(UserRole), nullable=False, default=UserRole.student) 

    courses = relationship("Courses", back_populates="professor")
