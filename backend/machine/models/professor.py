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
    
    # Thêm các trường xác thực email
    is_email_verified = Column(Boolean, default=False, nullable=False)  # Trạng thái xác thực email
    verification_code = Column(String(6), nullable=True)  # Mã xác thực
    verification_code_expires_at = Column(DateTime, nullable=True)  # Thời gian hết hạn mã xác thực

    # Trường mới cho tính năng đặt lại mật khẩu
    password_reset_code = Column(String(6), nullable=True)  # Mã xác thực reset mật khẩu
    password_reset_code_expires_at = Column(DateTime, nullable=True)  # Thời gian hết hạn mã reset mật khẩu

    # Trường mới cho trạng thái người dùng
    is_active = Column(Boolean, default=False, nullable=False)  # Trạng thái tài khoản người dùng
    
    courses = relationship("Courses", back_populates="professor")
