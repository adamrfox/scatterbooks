"""initial schema

Revision ID: 1edac03aadb0
Revises: 
Create Date: 2026-06-18 18:11:56.114652

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1edac03aadb0'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=64), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "sessions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_sessions_user", "sessions", ["user_id"])

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "name", sa.String(length=100, collation="NOCASE"), nullable=False, unique=True
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "editions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "name", sa.String(length=100, collation="NOCASE"), nullable=False, unique=True
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "books",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=False),
        sa.Column(
            "category_id",
            sa.Integer(),
            sa.ForeignKey("categories.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "edition_id", sa.Integer(), sa.ForeignKey("editions.id", ondelete="SET NULL")
        ),
        sa.Column("notes", sa.Text()),
        sa.Column(
            "created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_books_category", "books", ["category_id"])
    op.create_index("idx_books_edition", "books", ["edition_id"])

    op.create_table(
        "book_images",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "book_id", sa.Integer(), sa.ForeignKey("books.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=64), nullable=False),
        sa.Column("content_type", sa.String(length=32), nullable=False),
        sa.Column("width", sa.Integer()),
        sa.Column("height", sa.Integer()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("book_id", "position"),
    )
    op.create_index("idx_book_images_book", "book_images", ["book_id"])

    # Defense-in-depth backstop for the 5-images-per-book cap; the API also
    # checks the count up front to return a friendly 409 instead of this error.
    op.execute(
        """
        CREATE TRIGGER trg_book_images_max5
        BEFORE INSERT ON book_images
        WHEN (SELECT COUNT(*) FROM book_images WHERE book_id = NEW.book_id) >= 5
        BEGIN
            SELECT RAISE(ABORT, 'Maximum 5 images per book');
        END;
        """
    )

    # FTS5 index over books, kept in sync via triggers. Deliberately NOT an
    # "external content" table (content='books'): FTS5 maps external-content
    # columns to the content table's columns by POSITION, and books_fts's 5
    # columns (incl. denormalized category_name/edition_name, which aren't
    # even real columns on `books`) don't line up with books' 9 columns. That
    # mismatch only breaks on direct SELECT/UPDATE against books_fts (not on
    # explicit-value INSERT or MATCH queries), which is exactly the trap this
    # avoids: a plain self-contained FTS5 table supports normal INSERT/UPDATE/
    # DELETE by rowid with no positional-mapping surprises.
    op.execute(
        """
        CREATE VIRTUAL TABLE books_fts USING fts5(
            title, author, notes, category_name, edition_name
        );
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_books_ai AFTER INSERT ON books BEGIN
          INSERT INTO books_fts(rowid, title, author, notes, category_name, edition_name)
          SELECT NEW.id, NEW.title, NEW.author, NEW.notes,
                 (SELECT name FROM categories WHERE id = NEW.category_id),
                 (SELECT name FROM editions WHERE id = NEW.edition_id);
        END;
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_books_ad AFTER DELETE ON books BEGIN
          DELETE FROM books_fts WHERE rowid = OLD.id;
        END;
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_books_au AFTER UPDATE ON books BEGIN
          DELETE FROM books_fts WHERE rowid = OLD.id;
          INSERT INTO books_fts(rowid, title, author, notes, category_name, edition_name)
          SELECT NEW.id, NEW.title, NEW.author, NEW.notes,
                 (SELECT name FROM categories WHERE id = NEW.category_id),
                 (SELECT name FROM editions WHERE id = NEW.edition_id);
        END;
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_books_au")
    op.execute("DROP TRIGGER IF EXISTS trg_books_ad")
    op.execute("DROP TRIGGER IF EXISTS trg_books_ai")
    op.execute("DROP TABLE IF EXISTS books_fts")
    op.execute("DROP TRIGGER IF EXISTS trg_book_images_max5")
    op.drop_index("idx_book_images_book", table_name="book_images")
    op.drop_table("book_images")
    op.drop_index("idx_books_edition", table_name="books")
    op.drop_index("idx_books_category", table_name="books")
    op.drop_table("books")
    op.drop_table("editions")
    op.drop_table("categories")
    op.drop_index("idx_sessions_user", table_name="sessions")
    op.drop_table("sessions")
    op.drop_table("users")
