"""Add columns for user, courses and studentcourses tables

Revision ID: 2d124cb9eaee
Revises: 21f3364b195b
Create Date: 2024-11-19 15:41:00.021868
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

revision: str = '2d124cb9eaee'
down_revision: Union[str, None] = '21f3364b195b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # First create the enum type
    userrole = postgresql.ENUM('student', 'professor', 'admin', name='userrole')
    userrole.create(op.get_bind())

    # Handle the users table
    # Add new UUID column
    op.execute('ALTER TABLE users ADD COLUMN new_id UUID DEFAULT gen_random_uuid()')
    # Drop primary key and other constraints
    op.execute('ALTER TABLE users DROP CONSTRAINT users_pkey CASCADE')
    # Drop old id column
    op.drop_column('users', 'id')
    # Rename new_id to id
    op.execute('ALTER TABLE users RENAME COLUMN new_id TO id')
    # Create new primary key
    op.execute('ALTER TABLE users ADD PRIMARY KEY (id)')
    
    # Update user table with new columns
    op.alter_column('users', 'created_at', 
                    existing_type=postgresql.TIMESTAMP(timezone=True), 
                    type_=sa.DateTime(), 
                    nullable=True)
    op.add_column('users', sa.Column('email', sa.String(length=255), nullable=False))
    op.add_column('users', sa.Column('avatar_url', sa.String(), nullable=True))
    op.add_column('users', sa.Column('role', userrole, nullable=False))
    op.create_unique_constraint(None, 'users', ['email'])

    # Rest of the upgrade function remains the same...
    # Handle the courses table
    op.execute('ALTER TABLE courses ADD COLUMN new_id UUID DEFAULT gen_random_uuid()')
    op.execute('ALTER TABLE courses DROP CONSTRAINT courses_pkey CASCADE')
    op.drop_column('courses', 'id')
    op.execute('ALTER TABLE courses RENAME COLUMN new_id TO id')
    op.execute('ALTER TABLE courses ADD PRIMARY KEY (id)')
    
    op.add_column('courses', sa.Column('professor_id', sa.UUID(), nullable=False))
    op.add_column('courses', sa.Column('learning_outcomes', postgresql.ARRAY(sa.Text()), nullable=True))
    op.add_column('courses', sa.Column('start_date', sa.Date(), nullable=True))
    op.add_column('courses', sa.Column('end_date', sa.Date(), nullable=True))
    op.add_column('courses', sa.Column('status', sa.String(length=50), nullable=False))
    op.add_column('courses', sa.Column('image_url', sa.String(), nullable=True))

    # Handle the student_courses table
    op.execute('ALTER TABLE student_courses DROP CONSTRAINT IF EXISTS student_courses_course_id_fkey')
    op.execute('ALTER TABLE student_courses DROP CONSTRAINT IF EXISTS student_courses_student_id_fkey')
    
    op.execute('ALTER TABLE student_courses ADD COLUMN temp_student_id UUID DEFAULT gen_random_uuid()')
    op.execute('ALTER TABLE student_courses ADD COLUMN temp_course_id UUID DEFAULT gen_random_uuid()')
    
    op.drop_column('student_courses', 'student_id')
    op.drop_column('student_courses', 'course_id')
    op.drop_column('student_courses', 'id')
    
    op.execute('ALTER TABLE student_courses RENAME COLUMN temp_student_id TO student_id')
    op.execute('ALTER TABLE student_courses RENAME COLUMN temp_course_id TO course_id')
    
    op.create_foreign_key(None, 'student_courses', 'users', ['student_id'], ['id'])
    op.create_foreign_key(None, 'student_courses', 'courses', ['course_id'], ['id'])
    op.create_foreign_key(None, 'courses', 'users', ['professor_id'], ['id'])

def downgrade() -> None:
    # Drop all foreign key constraints first
    op.drop_constraint(None, 'student_courses', type_='foreignkey')
    op.drop_constraint(None, 'courses', type_='foreignkey')
    op.drop_constraint(None, 'student_courses', type_='foreignkey')

    # Revert users table changes
    op.drop_constraint('users_pkey', 'users', type_='primary')
    op.execute('ALTER TABLE users ADD COLUMN temp_id SERIAL PRIMARY KEY')
    op.drop_column('users', 'id')
    op.execute('ALTER TABLE users RENAME COLUMN temp_id TO id')
    op.alter_column('users', 'created_at', 
                    existing_type=sa.DateTime(), 
                    type_=postgresql.TIMESTAMP(timezone=True), 
                    nullable=False)
    op.drop_column('users', 'role')
    op.drop_column('users', 'avatar_url')
    op.drop_column('users', 'email')

    # Drop the enum type last
    op.execute('DROP TYPE userrole')

    # Rest of the downgrade function remains the same...
    op.execute('ALTER TABLE student_courses ADD COLUMN id SERIAL PRIMARY KEY')
    op.execute('ALTER TABLE student_courses ADD COLUMN temp_student_id INTEGER')
    op.execute('ALTER TABLE student_courses ADD COLUMN temp_course_id INTEGER')
    op.drop_column('student_courses', 'student_id')
    op.drop_column('student_courses', 'course_id')
    op.execute('ALTER TABLE student_courses RENAME COLUMN temp_student_id TO student_id')
    op.execute('ALTER TABLE student_courses RENAME COLUMN temp_course_id TO course_id')

    op.execute('ALTER TABLE courses ADD COLUMN temp_id SERIAL PRIMARY KEY')
    op.drop_column('courses', 'id')
    op.execute('ALTER TABLE courses RENAME COLUMN temp_id TO id')
    op.drop_column('courses', 'image_url')
    op.drop_column('courses', 'status')
    op.drop_column('courses', 'end_date')
    op.drop_column('courses', 'start_date')
    op.drop_column('courses', 'learning_outcomes')
    op.drop_column('courses', 'professor_id')

    op.create_foreign_key('student_courses_course_id_fkey', 
                         'student_courses', 'courses', 
                         ['course_id'], ['id'])