"""update schema

Revision ID: 8e9efd1d01ec
Revises: 3338a54d4cd8
Create Date: 2025-01-19 14:11:09.955485

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8e9efd1d01ec'
down_revision: Union[str, None] = '3338a54d4cd8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('lessons', sa.Column('learning_outcomes', sa.ARRAY(sa.Text()), nullable=True))
    op.add_column('recommend_lessons', sa.Column('lesson_id', sa.UUID(), nullable=True))
    op.drop_constraint('recommend_lessons_id_fkey', 'recommend_lessons', type_='foreignkey')
    op.create_foreign_key("recommend_lessons_lesson_id_fk", 'recommend_lessons', 'lessons', ['lesson_id'], ['id'])
    op.drop_column('recommend_lessons', 'learning_outcomes')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('recommend_lessons', sa.Column('learning_outcomes', postgresql.ARRAY(sa.TEXT()), autoincrement=False, nullable=True))
    op.drop_constraint("recommend_lessons_lesson_id_fk", 'recommend_lessons', type_='foreignkey')
    op.create_foreign_key('recommend_lessons_id_fkey', 'recommend_lessons', 'lessons', ['id'], ['id'])
    op.drop_column('recommend_lessons', 'lesson_id')
    op.drop_column('lessons', 'learning_outcomes')
    # ### end Alembic commands ###
