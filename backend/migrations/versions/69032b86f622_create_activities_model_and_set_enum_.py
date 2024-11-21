from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "69032b86f622"
down_revision: Union[str, None] = "3b4c93bddfdc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the Enum type 'statustype'
    op.execute(
        """
        UPDATE courses
        SET status = 'New' 
        WHERE status = 'OPEN';
    """
    )
    op.execute(
        """
    CREATE TYPE statustype AS ENUM ('New', 'In Progress', 'Completed');
    """
    )

    # Alter the 'status' column in 'courses' table to use the 'statustype' enum
    op.alter_column(
        "courses",
        "status",
        existing_type=sa.VARCHAR(length=50),
        type_=sa.Enum("New", "In Progress", "Completed", name="statustype"),
        existing_nullable=False,
        postgresql_using="status::statustype",
        server_default="New",
    )

    # Add columns with default values to avoid NotNullViolationError
    op.add_column("student_courses", sa.Column("completed_lessons", sa.Integer(), nullable=False, server_default="0"))
    op.add_column(
        "student_courses",
        sa.Column("time_spent", sa.Interval(), nullable=False, server_default=sa.text("'0 second'::interval")),
    )
    op.add_column("student_courses", sa.Column("assignments_done", sa.Integer(), nullable=False, server_default="0"))
    op.add_column(
        "student_courses",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.add_column(
        "student_courses",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Make student_id and course_id non-nullable in student_courses
    op.alter_column(
        "student_courses",
        "student_id",
        existing_type=sa.UUID(),
        nullable=False,
        existing_server_default=sa.text("gen_random_uuid()"),
    )
    op.alter_column(
        "student_courses",
        "course_id",
        existing_type=sa.UUID(),
        nullable=False,
        existing_server_default=sa.text("gen_random_uuid()"),
    )


def downgrade() -> None:
    # Drop the 'statustype' enum type if rolling back
    op.execute("DROP TYPE statustype")

    # Revert the 'status' column in 'courses' table to use a VARCHAR
    op.alter_column(
        "courses",
        "status",
        existing_type=sa.Enum("New", "In Progress", "Completed", name="statustype"),
        type_=sa.VARCHAR(length=50),
        existing_nullable=False,
    )

    # Rollback the changes to student_courses table
    op.drop_column("student_courses", "updated_at")
    op.drop_column("student_courses", "created_at")
    op.drop_column("student_courses", "assignments_done")
    op.drop_column("student_courses", "time_spent")
    op.drop_column("student_courses", "completed_lessons")

    # Revert the nullable changes for student_id and course_id in student_courses
    op.alter_column(
        "student_courses",
        "student_id",
        existing_type=sa.UUID(),
        nullable=True,
        existing_server_default=sa.text("gen_random_uuid()"),
    )
    op.alter_column(
        "student_courses",
        "course_id",
        existing_type=sa.UUID(),
        nullable=True,
        existing_server_default=sa.text("gen_random_uuid()"),
    )
