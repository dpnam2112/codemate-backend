from uuid import uuid4
from core.db import Base
from sqlalchemy.orm import relationship
from core.db.mixins import TimestampMixin
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, String, UUID, DateTime, Boolean, Date


class Student(Base, TimestampMixin):
    __tablename__ = "student"

    id = Column(UUID, primary_key=True, default=uuid4)  # Unique ID for each student
    name = Column(String(255), nullable=False)  # Username of the student
    email = Column(String(255), unique=True, nullable=False)  # Email of the student
    password = Column(String(255), nullable=True)  # Password of the student
    avatar_url = Column(String, default="documents/326750ef-127e-4d24-b7f1-a9aaa87f40d6-User-avatar.svg.png")  # Avatar URL of the student
    mssv = Column(String(10), nullable=True)  # Student ID
    date_of_birth = Column(Date, nullable=True)  # Date of birth of the student
    fullname = Column(String(255), nullable=True)  # Full name of the student

    is_email_verified = Column(Boolean, default=False, nullable=False)
    """
    Email verification status. 
    Only students log in using email and password will have this field logic. 
    Students log in using Google will have this field set to True by default.
    """
    verification_code = Column(String(6), nullable=True)  # Verification code
    verification_code_expires_at = Column(DateTime, nullable=True)  # Verification code expiration time

    password_reset_code = Column(String(6), nullable=True) # Password reset code
    password_reset_code_expires_at = Column(DateTime, nullable=True) # Password reset code expiration time

    is_active = Column(Boolean, default=False, nullable=False) # Active status of the student

    feedbacks = relationship("Feedback", back_populates="student", lazy='dynamic')
    activities = relationship("Activities", back_populates="student")
    student_courses = relationship("StudentCourses", back_populates="student")
    student_exercises = relationship("StudentExercises", back_populates="student")
    learning_paths = relationship("LearningPaths", back_populates="student")
