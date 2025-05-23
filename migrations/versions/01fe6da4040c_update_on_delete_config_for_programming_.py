"""update on delete config for programming_submissions.exercise_id

Revision ID: 01fe6da4040c
Revises: bd16b6ca454d
Create Date: 2025-04-21 00:44:06.742958

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '01fe6da4040c'
down_revision: Union[str, None] = 'bd16b6ca454d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('lessons', 'order',
               existing_type=sa.INTEGER(),
               server_default=sa.Identity(always=False, start=1, increment=1),
               existing_nullable=False)
    op.drop_constraint('programming_submissions_exercise_id_fkey', 'programming_submissions', type_='foreignkey')
    op.create_foreign_key(None, 'programming_submissions', 'exercises', ['exercise_id'], ['id'], ondelete='CASCADE')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'programming_submissions', type_='foreignkey')
    op.create_foreign_key('programming_submissions_exercise_id_fkey', 'programming_submissions', 'exercises', ['exercise_id'], ['id'])
    op.alter_column('lessons', 'order',
               existing_type=sa.INTEGER(),
               server_default=sa.Identity(always=True, start=1, increment=1, minvalue=1, maxvalue=2147483647, cycle=False, cache=1),
               existing_nullable=False)
    # ### end Alembic commands ###
