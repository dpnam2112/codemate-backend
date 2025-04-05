from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from core.db.mixins.timestamp import TimestampMixin
from core.db import Base

class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

class Message(Base, TimestampMixin):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    role: Mapped[str] = mapped_column(String(20))  # 'user' or 'assistant'
    content: Mapped[str] = mapped_column(Text)
    conversation_id: Mapped[UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"))

class CodingConversation(Base, TimestampMixin):
    __tablename__ = "coding_conversations"
    __table_args__ = (
        UniqueConstraint("user_id", "conversation_id", name="uq_user_conversation"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )

    # For now, no need for foreign key constraint on this column. Coding conversation can be
    # initiated by any type of users: admin, student or prof. 
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True))
    conversation_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"))

    conversation: Mapped["Conversation"] = relationship()
