"""new column for storing submission evaluation

Revision ID: bd16b6ca454d
Revises: 525f7331eec7
Create Date: 2025-04-17 10:39:45.859794

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'bd16b6ca454d'
down_revision: Union[str, None] = '525f7331eec7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('exercises', 'source',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.alter_column('lessons', 'order',
               existing_type=sa.INTEGER(),
               server_default=sa.Identity(always=False, start=1, increment=1),
               existing_nullable=False)
    op.add_column('programming_submissions', sa.Column('llm_evaluation', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('programming_submissions', 'llm_evaluation')
    op.alter_column('lessons', 'order',
               existing_type=sa.INTEGER(),
               server_default=sa.Identity(always=True, start=1, increment=1, minvalue=1, maxvalue=2147483647, cycle=False, cache=1),
               existing_nullable=False)
    op.alter_column('exercises', 'source',
               existing_type=sa.VARCHAR(),
               nullable=True)
    # ### end Alembic commands ###
