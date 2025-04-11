from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB, UUID as pgUUID
from core.db import Base
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy import ForeignKey
from sqlalchemy import Identity
class LearningPaths(Base):
    __tablename__ = "learning_paths"

    id: Mapped[UUID] = mapped_column(pgUUID(as_uuid=True), primary_key=True, default=uuid4)
    start_date: Mapped[datetime | None] = mapped_column(default=datetime.now(), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(nullable=True)
    objective: Mapped[str | None] = mapped_column(nullable=True)
    progress: Mapped[float] = mapped_column(default=0.0, nullable=False)
    version: Mapped[int] = mapped_column(Identity(), nullable=False)
    llm_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("student.id"), nullable=False)
    course_id: Mapped[UUID] = mapped_column(ForeignKey("courses.id"), nullable=False)

    student: Mapped["Student"] = relationship(back_populates="learning_paths")
    course: Mapped["Courses"] = relationship(back_populates="learning_paths", cascade="all")
    recommend_lessons: Mapped[list["RecommendLessons"]] = relationship(back_populates="learning_path", cascade="all, delete-orphan")
