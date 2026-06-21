"""add wish lists

Revision ID: cb8914a80bd2
Revises: 5393b904a0e9
Create Date: 2026-06-21 19:18:19.751472

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cb8914a80bd2'
down_revision: Union[str, None] = '5393b904a0e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "wish_lists",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "wish_list_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "wish_list_id",
            sa.Integer(),
            sa.ForeignKey("wish_lists.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=False),
        sa.Column(
            "category_id", sa.Integer(), sa.ForeignKey("categories.id", ondelete="SET NULL")
        ),
        sa.Column("edition_id", sa.Integer(), sa.ForeignKey("editions.id", ondelete="SET NULL")),
        sa.Column("notes", sa.Text()),
        sa.Column("year", sa.Integer()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "wish_list_entry_images",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "wish_list_entry_id",
            sa.Integer(),
            sa.ForeignKey("wish_list_entries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=64), nullable=False),
        sa.Column("content_type", sa.String(length=32), nullable=False),
        sa.Column("width", sa.Integer()),
        sa.Column("height", sa.Integer()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("wish_list_entry_id", "position"),
    )


def downgrade() -> None:
    op.drop_table("wish_list_entry_images")
    op.drop_table("wish_list_entries")
    op.drop_table("wish_lists")
