from uuid import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy import JSON, String, DateTime, func, ForeignKey
from .base import Base
from sqlalchemy.dialects.postgresql import UUID as pgUUID

class Document(Base):
    """Model to store documents.

    Attributes:
        id (UUID): Unique identifier for the document.
        collection_id (UUID): Foreign key to the parent collection.
        s3_file_id (UUID): Foreign key to the associated S3 file.
        title (str): Title of the document.
        metadata (JSON): Optional metadata for the document.
        created_at (DateTime): Timestamp when the document was created.
        updated_at (DateTime): Timestamp when the document was last updated.
        collection (DocumentCollection): The collection this document belongs to.
        s3_file (S3File): The S3 file associated with this document.
    """
    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(pgUUID(as_uuid=True), primary_key=True, default=UUID)
    collection_id: Mapped[UUID] = mapped_column(pgUUID(as_uuid=True), ForeignKey("collections.id"), nullable=False)
    s3_file_id: Mapped[UUID] = mapped_column(pgUUID(as_uuid=True), ForeignKey("s3_files.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    cmetadata: Mapped[dict] = mapped_column(JSON, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    collection = relationship("DocumentCollection", back_populates="documents")
    s3_file = relationship("S3File")

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, title='{self.title}', collection_id={self.collection_id}, s3_file_id={self.s3_file_id})>"

