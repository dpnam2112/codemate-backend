"""Merge heads

Revision ID: 3bc138fa9696
Revises: 6bb743bef97e, ce9d4d94836e
Create Date: 2025-01-22 18:33:54.818106

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3bc138fa9696'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
