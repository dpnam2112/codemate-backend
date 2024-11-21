"""add lessons and exercises model

Revision ID: f76b6173d137
Revises: 7e0b17cffa0d
Create Date: 2024-11-20 21:51:18.302780

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f76b6173d137"
down_revision: Union[str, None] = "7e0b17cffa0d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the lessons table
    op.create_table(
        "lessons",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("course_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("lesson_type", sa.Enum("original", "recommended", name="lessontype"), nullable=False),
        sa.Column("bookmark", sa.Boolean(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("status", postgresql.ENUM(name="statustype", create_type=False)),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create the exercises table
    op.create_table(
        "exercises",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("lesson_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("status", postgresql.ENUM(name="statustype", create_type=False)),
        sa.ForeignKeyConstraint(
            ["lesson_id"],
            ["lessons.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Alter the activities table to change enum type name
    op.alter_column(
        "activities",
        "type",
        existing_type=postgresql.ENUM(
            "VIEW_COURSE",
            "RESUME_ACTIVITY",
            "COMPLETE_LESSON",
            "COMPLETE_ASSIGNMENT",
            "ENROLL_COURSE",
            "BADGEEARNED",
            name="type",
        ),
        type=sa.Enum(
            "VIEW_COURSE",
            "RESUME_ACTIVITY",
            "COMPLETE_LESSON",
            "COMPLETE_ASSIGNMENT",
            "ENROLL_COURSE",
            "BADGE_EARNED",
            name="activitytype",
        ),
        existing_nullable=False,
    )


def downgrade() -> None:
    # Reverse the enum type change in 'activities' table
    op.alter_column(
        "activities",
        "type",
        existing_type=sa.Enum(
            "VIEW_COURSE",
            "RESUME_ACTIVITY",
            "COMPLETE_LESSON",
            "COMPLETE_ASSIGNMENT",
            "ENROLL_COURSE",
            "BADGE_EARNED",
            name="activitytype",
        ),
        type_=postgresql.ENUM(
            "VIEW_COURSE",
            "RESUME_ACTIVITY",
            "COMPLETE_LESSON",
            "COMPLETE_ASSIGNMENT",
            "ENROLL_COURSE",
            "BADGE_EARNED",
            name="type",
        ),
        existing_nullable=False,
    )

    # Drop the exercises and lessons tables
    op.drop_table("exercises")
    op.drop_table("lessons")
