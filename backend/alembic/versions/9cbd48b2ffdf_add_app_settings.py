"""add app settings

Revision ID: 9cbd48b2ffdf
Revises: 1edac03aadb0
Create Date: 2026-06-19 18:23:25.032441

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9cbd48b2ffdf'
down_revision: Union[str, None] = '1edac03aadb0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("google_books_api_key", sa.String(length=255)),
    )
    op.execute(
        "INSERT INTO app_settings (id, google_books_api_key) VALUES (1, NULL)"
    )


def downgrade() -> None:
    op.drop_table("app_settings")
