from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy import JSON, String, Integer, DateTime, func, Text, ForeignKey
from .base import Base

class Document(Base):
    """Model to store documents.

    Attributes:
        id (int): Unique identifier for the document.
        collection_id (int): Foreign key to the parent collection.
        s3_file_id (int): Foreign key to the associated S3 file.
        metadata (str): Optional metadata for the document.
        created_at (DateTime): Timestamp when the document was created.
        updated_at (DateTime): Timestamp when the document was last updated.
        collection (Collection): The collection this document belongs to.
        s3_file (S3File): The S3 file associated with this document.
    """
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    collection_id: Mapped[int] = mapped_column(Integer, ForeignKey("collections.id"), nullable=False)
    s3_file_id: Mapped[int] = mapped_column(Integer, ForeignKey("s3_files.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    cmetadata: Mapped[str] = mapped_column(JSON, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    collection = relationship("Collection", back_populates="documents")
    s3_file = relationship("S3File")

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, title='{self.title}', collection_id={self.collection_id}, s3_file_id={self.s3_file_id})>"
