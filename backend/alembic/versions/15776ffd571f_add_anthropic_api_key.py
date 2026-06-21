"""add anthropic api key

Revision ID: 15776ffd571f
Revises: 9cbd48b2ffdf
Create Date: 2026-06-19 19:12:39.349514

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '15776ffd571f'
down_revision: Union[str, None] = '9cbd48b2ffdf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("app_settings", sa.Column("anthropic_api_key", sa.String(length=255)))


def downgrade() -> None:
    op.drop_column("app_settings", "anthropic_api_key")
