from .base import Base 
from sqlalchemy.orm import mapped_column, Mapped
from typing import Optional
from sqlalchemy import JSON, String, Integer, DateTime, func, Text


class S3File(Base):
    """Model to store references to S3 files.

    Content hash may be used to check for file duplication.
    """
    
    __tablename__ = "s3_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bucket_name: Mapped[str] = mapped_column(String, nullable=False)
    file_key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    content_hash: Mapped[str] = mapped_column(String, unique=True, nullable=False) 
    created_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), server_default=func.now())
    cmetadata: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)  # JSON metadata or extra info

    def __repr__(self) -> str:
        return f"<S3File(id={self.id}, bucket='{self.bucket_name}', file_key='{self.file_key}')>"
