"""Submission

Revision ID: efe0f7a9370e
Revises: 8bb833c4dee0
Create Date: 2025-04-06 17:08:25.740238

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'efe0f7a9370e'
down_revision: Union[str, None] = '8bb833c4dee0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('programming_language_configs',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('exercise_id', sa.UUID(), nullable=False),
    sa.Column('judge0_language_id', sa.Integer(), nullable=False),
    sa.Column('boilerplate_code', sa.Text(), nullable=True),
    sa.Column('time_limit', sa.Float(), nullable=False),
    sa.Column('memory_limit', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['exercise_id'], ['exercises.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('exercise_id', 'judge0_language_id', name='uq_problem_language')
    )
    op.create_table('programming_submissions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('exercise_id', sa.UUID(), nullable=False),
    sa.Column('judge0_language_id', sa.Integer(), nullable=False),
    sa.Column('code', sa.Text(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('score', sa.Float(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['exercise_id'], ['exercises.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['student.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('programming_testcases',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('exercise_id', sa.UUID(), nullable=False),
    sa.Column('input', sa.Text(), nullable=False),
    sa.Column('expected_output', sa.Text(), nullable=False),
    sa.Column('is_public', sa.Boolean(), nullable=False),
    sa.Column('score', sa.Float(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['exercise_id'], ['exercises.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('programming_test_results',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('submission_id', sa.UUID(), nullable=False),
    sa.Column('testcase_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('stdout', sa.Text(), nullable=True),
    sa.Column('stderr', sa.Text(), nullable=True),
    sa.Column('time', sa.Float(), nullable=True),
    sa.Column('judge0_token', sa.Text(), nullable=False),
    sa.Column('memory', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['submission_id'], ['programming_submissions.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['testcase_id'], ['programming_testcases.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('programming_test_results')
    op.drop_table('programming_testcases')
    op.drop_table('programming_submissions')
    op.drop_table('programming_language_configs')
    # ### end Alembic commands ###
