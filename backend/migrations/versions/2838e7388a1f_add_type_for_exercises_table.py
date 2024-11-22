from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2838e7388a1f'
down_revision: Union[str, None] = 'ac261db49061'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Create the Enum type in PostgreSQL
    exercisetype_enum = sa.Enum('original', 'recommended', name='exercisetype')
    exercisetype_enum.create(op.get_bind(), checkfirst=True)

    # Add the 'type' column to the 'exercises' table without NOT NULL constraint
    op.add_column('exercises', sa.Column('type', exercisetype_enum, nullable=True))

    # Update existing rows to set the default value for 'type'
    op.execute("UPDATE exercises SET type = 'original' WHERE type IS NULL")

    # Alter the 'type' column to set NOT NULL constraint
    op.alter_column('exercises', 'type', nullable=False)

def downgrade() -> None:
    # Drop the 'type' column from the 'exercises' table
    op.drop_column('exercises', 'type')

    # Drop the 'exercisetype' enum type from the database
    exercisetype_enum = sa.Enum('original', 'recommended', name='exercisetype')
    exercisetype_enum.drop(op.get_bind(), checkfirst=True)
