from uuid import uuid4
from core.db import Base
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column
from core.repository.enum import UserRole
from sqlalchemy import DateTime, Enum

class UserLogins(Base):
    __tablename__ = "user_logins"
    
    id = Column(UUID, primary_key=True, default=uuid4)  # Unique ID for each user login
    user_id = Column(UUID, nullable=False)  # User ID
    user_role = Column(Enum(UserRole), nullable=False)  # User role
    login_timestamp = Column(DateTime, nullable=False)  # Login timestamp
    
    