from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class WishListEntryImage(Base):
    __tablename__ = "wish_list_entry_images"
    __table_args__ = (UniqueConstraint("wish_list_entry_id", "position"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    wish_list_entry_id: Mapped[int] = mapped_column(
        ForeignKey("wish_list_entries.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    filename: Mapped[str] = mapped_column(String(64), nullable=False)
    content_type: Mapped[str] = mapped_column(String(32), nullable=False)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    entry: Mapped["WishListEntry"] = relationship(back_populates="images")
