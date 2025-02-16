import uuid
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy import String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from .base import Base

class DocumentCollection(Base):
    """Model to store document collections.

    Attributes:
        id (UUID): Unique identifier for the collection.
        name (str): Name of the collection.
        description (str): Optional description of the collection.
        created_at (DateTime): Timestamp when the collection was created.
        updated_at (DateTime): Timestamp when the collection was last updated.
        documents (list[Document]): List of documents belonging to the collection.
    """
    __tablename__ = "collections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    documents: Mapped[list["Document"]] = relationship(
        "Document", back_populates="collection", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Collection(id={self.id}, name='{self.name}')>"

