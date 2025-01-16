"""Refactor User into Student, Professor, Admin

Revision ID: 731ef32afdc4
Revises: 3338a54d4cd8
Create Date: 2025-01-05 14:16:13.388819

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '731ef32afdc4'
down_revision: Union[str, None] = '3338a54d4cd8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop foreign key constraints referencing 'users'
    op.drop_constraint('courses_professor_id_fkey', 'courses', type_='foreignkey')
    op.drop_constraint('learning_paths_student_id_fkey', 'learning_paths', type_='foreignkey')
    op.drop_constraint('student_courses_student_id_fkey', 'student_courses', type_='foreignkey')
    op.drop_constraint('student_lessons_student_id_fkey', 'student_lessons', type_='foreignkey')
    op.drop_constraint('student_exercises_student_id_fkey', 'student_exercises', type_='foreignkey')
    
    # Drop the 'users' table if it exists
    op.execute("DROP TABLE IF EXISTS users CASCADE")

    # Ensure the new tables (students, professors, admins) do not already exist
    op.execute("DROP TABLE IF EXISTS admins")
    op.execute("DROP TABLE IF EXISTS professors")
    op.execute("DROP TABLE IF EXISTS students")

    # Create new tables
    op.create_table('admins',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('avatar_url', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('mscb', sa.String(length=255), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )

    op.create_table('professors',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('avatar_url', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )

    op.create_table('students',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('avatar_url', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )

    # Create the necessary foreign key constraints
    op.create_foreign_key(None, 'activities', 'students', ['student_id'], ['id'])
    op.create_foreign_key(None, 'courses', 'professors', ['professor_id'], ['id'])
    op.create_foreign_key(None, 'learning_paths', 'students', ['student_id'], ['id'])
    op.create_foreign_key(None, 'student_courses', 'students', ['student_id'], ['id'])
    op.create_foreign_key(None, 'student_exercises', 'students', ['student_id'], ['id'])
    op.create_foreign_key(None, 'student_lessons', 'students', ['student_id'], ['id'])


def downgrade() -> None:
    # Drop foreign key constraints for the new schema
    op.drop_constraint(None, 'student_lessons', type_='foreignkey')
    op.create_foreign_key('student_lessons_student_id_fkey', 'student_lessons', 'users', ['student_id'], ['id'])
    op.drop_constraint(None, 'student_exercises', type_='foreignkey')
    op.create_foreign_key('student_exercises_student_id_fkey', 'student_exercises', 'users', ['student_id'], ['id'])
    op.drop_constraint(None, 'student_courses', type_='foreignkey')
    op.create_foreign_key('student_courses_student_id_fkey', 'student_courses', 'users', ['student_id'], ['id'])
    op.drop_constraint(None, 'learning_paths', type_='foreignkey')
    op.create_foreign_key('learning_paths_student_id_fkey', 'learning_paths', 'users', ['student_id'], ['id'])
    op.drop_constraint(None, 'courses', type_='foreignkey')
    op.create_foreign_key('courses_professor_id_fkey', 'courses', 'users', ['professor_id'], ['id'])
    op.drop_constraint(None, 'activities', type_='foreignkey')
    op.create_foreign_key('activities_student_id_fkey', 'activities', 'users', ['student_id'], ['id'])

    # Check if the ENUM type exists and only create it if it doesn't exist already
    conn = op.get_bind()
    result = conn.execute("SELECT 1 FROM pg_type WHERE typname = 'userrole' LIMIT 1;")
    if not result.fetchone():
        # Only create the ENUM type if it doesn't exist
        op.execute("""
            CREATE TYPE userrole AS ENUM ('student', 'professor', 'admin');
        """)

    # Recreate the 'users' table
    op.create_table('users',
        sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
        sa.Column('name', sa.VARCHAR(length=255), autoincrement=False, nullable=False),
        sa.Column('email', sa.VARCHAR(length=255), autoincrement=False, nullable=False),
        sa.Column('avatar_url', sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
        sa.Column('role', postgresql.ENUM('student', 'professor', 'admin', name='userrole', create_type=False),
                  autoincrement=False, nullable=False),
        sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
        sa.PrimaryKeyConstraint('id', name='users_pkey'),
        sa.UniqueConstraint('email', name='users_email_key')
    )

    # Drop the 'students', 'professors', and 'admins' tables
    op.drop_table('students')
    op.drop_table('professors')
    op.drop_table('admins')
