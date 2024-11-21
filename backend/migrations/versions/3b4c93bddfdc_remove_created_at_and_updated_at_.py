"""remove created_at and updated_at columns from student_courses

Revision ID: 3b4c93bddfdc
Revises: 2d124cb9eaee
Create Date: 2024-11-20 13:16:03.031921

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3b4c93bddfdc'
down_revision: Union[str, None] = '2d124cb9eaee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Drop the columns from the student_courses table
    op.drop_column('student_courses', 'created_at')
    op.drop_column('student_courses', 'updated_at')

def downgrade():
    # Add the columns back in case of rollback (optional)
    op.add_column('student_courses', sa.Column('created_at', sa.TIMESTAMP(), nullable=True))
    op.add_column('student_courses', sa.Column('updated_at', sa.TIMESTAMP(), nullable=True))
