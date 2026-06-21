"""add year to books

Revision ID: 5393b904a0e9
Revises: 15776ffd571f
Create Date: 2026-06-21 18:04:41.736310

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5393b904a0e9'
down_revision: Union[str, None] = '15776ffd571f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("books", sa.Column("year", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("books", "year")
