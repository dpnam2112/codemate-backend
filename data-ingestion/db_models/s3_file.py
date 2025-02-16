from uuid import UUID
from .base import Base
from sqlalchemy.orm import mapped_column, Mapped
from typing import Optional
from sqlalchemy import JSON, String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID as pgUUID

class S3File(Base):
    """Model to store references to S3 files.

    Content hash may be used to check for file duplication.
    """
    
    __tablename__ = "s3_files"

    id: Mapped[UUID] = mapped_column(pgUUID(as_uuid=True), primary_key=True, default=UUID)
    bucket_name: Mapped[str] = mapped_column(String, nullable=False)
    file_key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    content_hash: Mapped[str] = mapped_column(String, unique=True, nullable=False) 
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    cmetadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # JSON metadata or extra info

    def __repr__(self) -> str:
        return f"<S3File(id={self.id}, bucket='{self.bucket_name}', file_key='{self.file_key}')>"

