"""add library_name to app_settings

Revision ID: a3f2c1d9e845
Revises: cb8914a80bd2
Create Date: 2026-06-29 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a3f2c1d9e845"
down_revision: str | None = "cb8914a80bd2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "app_settings",
        sa.Column("library_name", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("app_settings", "library_name")
