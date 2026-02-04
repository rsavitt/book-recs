from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Rating(Base):
    """User rating for a book."""

    __tablename__ = "ratings"
    __table_args__ = (UniqueConstraint("user_id", "book_id", name="unique_user_book_rating"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), index=True)

    # Rating data
    rating: Mapped[int] = mapped_column(Integer)  # 1-5 scale
    date_read: Mapped[date | None] = mapped_column(Date)
    date_added: Mapped[date | None] = mapped_column(Date)

    # Source tracking
    source: Mapped[str] = mapped_column(
        String(50), default="goodreads_import"
    )  # goodreads_import, manual, etc.

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="ratings")
    book: Mapped["Book"] = relationship(back_populates="ratings")


class Shelf(Base):
    """User's shelf/tag assignment for a book (from Goodreads import)."""

    __tablename__ = "shelves"
    __table_args__ = (
        UniqueConstraint("user_id", "book_id", "shelf_name", name="unique_user_book_shelf"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), index=True)

    # Shelf data
    shelf_name: Mapped[str] = mapped_column(
        String(100), index=True
    )  # e.g., "to-read", "romantasy", "fae"
    shelf_name_normalized: Mapped[str] = mapped_column(
        String(100), index=True
    )  # lowercase, no special chars

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="shelves")
    book: Mapped["Book"] = relationship()


# Forward references
from app.models.book import Book  # noqa: E402, F811
from app.models.user import User  # noqa: E402, F811
