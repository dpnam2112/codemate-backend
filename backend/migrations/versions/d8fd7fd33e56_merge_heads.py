"""Merge heads

Revision ID: d8fd7fd33e56
Revises: 0f9dc49fbca7, 3338a54d4cd8
Create Date: 2025-01-22 20:15:51.188125

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8fd7fd33e56'
down_revision: Union[str, None] = ('0f9dc49fbca7', '3338a54d4cd8')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
