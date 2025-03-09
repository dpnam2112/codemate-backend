# from uuid import uuid4
# from core.db import Base
# from datetime import datetime
# from sqlalchemy.orm import relationship
# from sqlalchemy import UniqueConstraint
# from sqlalchemy.dialects.postgresql import UUID
# from sqlalchemy import Column, DateTime, String, Float, ForeignKey
# class LearningPaths(Base):
#     __tablename__ = "learning_paths"
    
#     id = Column(UUID, primary_key=True, default=uuid4)
#     start_date = Column(DateTime, default=datetime.utcnow, nullable=True)
#     end_date = Column(DateTime, nullable=True)
#     objective = Column(String, nullable=True) # What student want to achieve in this course
#     progress = Column(Float, default=0.0, nullable=False)
    
#     student_id = Column(UUID, ForeignKey("students.id"), nullable=False)
#     course_id = Column(UUID, ForeignKey("courses.id"), nullable=False)
    
#     student = relationship("Student", back_populates="learning_paths")
#     course = relationship("Courses", back_populates="learning_paths")
#     recommend_lessons = relationship("RecommendLessons", back_populates="learning_path")
    
#     __table_args__ = (
#         UniqueConstraint('student_id', 'course_id', name='uq_student_course'),
#     )
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB, UUID as pgUUID
from core.db import Base
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy import JSON, ForeignKey, UniqueConstraint

class LearningPaths(Base):
    __tablename__ = "learning_paths"

    id: Mapped[UUID] = mapped_column(pgUUID(as_uuid=True), primary_key=True, default=uuid4)
    start_date: Mapped[datetime | None] = mapped_column(default=datetime.now(), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(nullable=True)
    objective: Mapped[str | None] = mapped_column(nullable=True)
    progress: Mapped[float] = mapped_column(default=0.0, nullable=False)
    llm_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("student.id"), nullable=False)
    course_id: Mapped[UUID] = mapped_column(ForeignKey("courses.id"), nullable=False)

    student: Mapped["Student"] = relationship(back_populates="learning_paths")
    course: Mapped["Courses"] = relationship(back_populates="learning_paths")
    recommend_lessons: Mapped[list["RecommendLessons"]] = relationship(back_populates="learning_path", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('student_id', 'course_id', name='uq_student_course'),
    )

