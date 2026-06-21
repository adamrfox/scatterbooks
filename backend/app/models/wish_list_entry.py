from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class WishListEntry(Base):
    __tablename__ = "wish_list_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    wish_list_id: Mapped[int] = mapped_column(
        ForeignKey("wish_lists.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL")
    )
    edition_id: Mapped[int | None] = mapped_column(
        ForeignKey("editions.id", ondelete="SET NULL")
    )
    notes: Mapped[str | None] = mapped_column(Text)
    year: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    wish_list: Mapped["WishList"] = relationship(back_populates="entries")
    images: Mapped[list["WishListEntryImage"]] = relationship(
        back_populates="entry",
        cascade="all, delete-orphan",
        order_by="WishListEntryImage.position",
    )
    category: Mapped["Category | None"] = relationship()
    edition: Mapped["Edition | None"] = relationship()

    @property
    def cover_image_id(self) -> int | None:
        return self.images[0].id if self.images else None
