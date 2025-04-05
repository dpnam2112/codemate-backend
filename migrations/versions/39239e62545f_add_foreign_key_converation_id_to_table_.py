"""add foreign key 'conversation_id' to table 'exercises'

Revision ID: 39239e62545f
Revises: 8d8078a54610
Create Date: 2025-04-01 08:46:24.689091

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '39239e62545f'
down_revision: Union[str, None] = '8d8078a54610'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'exercises',
        sa.Column(
            'conversation_id',
            sa.UUID(),
            nullable=True,
            comment='Conversation between user and coding assistant'
        )
    )
    op.create_foreign_key(
        constraint_name='fk_exercises_conversation_id',
        source_table='exercises',
        referent_table='conversations',
        local_cols=['conversation_id'],
        remote_cols=['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_exercises_conversation_id', 'exercises', type_='foreignkey')
    op.drop_column('exercises', 'conversation_id')

