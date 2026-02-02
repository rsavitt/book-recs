from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Text, Integer, Float, ForeignKey, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# Association table for book <-> tag many-to-many
book_tag_association = Table(
    "book_tag_association",
    Base.metadata,
    Column("book_id", Integer, ForeignKey("books.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("book_tags.id"), primary_key=True),
)


class Book(Base):
    """Canonical book record - one per unique work regardless of edition."""

    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Core identifiers
    title: Mapped[str] = mapped_column(String(500), index=True)
    author: Mapped[str] = mapped_column(String(255), index=True)
    author_normalized: Mapped[str] = mapped_column(String(255), index=True)  # lowercase, no accents

    # External IDs (for deduplication)
    isbn_13: Mapped[str | None] = mapped_column(String(13), unique=True, index=True)
    isbn_10: Mapped[str | None] = mapped_column(String(10), index=True)
    open_library_id: Mapped[str | None] = mapped_column(String(50), index=True)  # e.g., OL12345W
    google_books_id: Mapped[str | None] = mapped_column(String(50), index=True)

    # Metadata
    description: Mapped[str | None] = mapped_column(Text)
    cover_url: Mapped[str | None] = mapped_column(String(500))
    page_count: Mapped[int | None] = mapped_column(Integer)
    publication_year: Mapped[int | None] = mapped_column(Integer, index=True)

    # Series info
    series_name: Mapped[str | None] = mapped_column(String(255), index=True)
    series_position: Mapped[float | None] = mapped_column(Float)  # Float for "1.5" novellas

    # Romantasy classification
    is_romantasy: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    romantasy_confidence: Mapped[float] = mapped_column(Float, default=0.0)  # 0-1 score
    spice_level: Mapped[int | None] = mapped_column(Integer)  # 0-5 scale
    is_ya: Mapped[bool | None] = mapped_column(Boolean)

    # Why Choose / Reverse Harem classification
    is_why_choose: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    why_choose_confidence: Mapped[float] = mapped_column(Float, default=0.0)  # 0-1 score

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    editions: Mapped[list["BookEdition"]] = relationship(back_populates="book", cascade="all, delete-orphan")
    tags: Mapped[list["BookTag"]] = relationship(secondary=book_tag_association, back_populates="books")
    ratings: Mapped[list["Rating"]] = relationship(back_populates="book", cascade="all, delete-orphan")


class BookEdition(Base):
    """Different editions of the same book (hardcover, paperback, different ISBNs)."""

    __tablename__ = "book_editions"

    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), index=True)

    # Edition-specific identifiers
    isbn_13: Mapped[str | None] = mapped_column(String(13), index=True)
    isbn_10: Mapped[str | None] = mapped_column(String(10), index=True)
    goodreads_book_id: Mapped[str | None] = mapped_column(String(50), index=True)

    # Edition metadata
    title_variant: Mapped[str | None] = mapped_column(String(500))  # If different from canonical
    format: Mapped[str | None] = mapped_column(String(50))  # hardcover, paperback, ebook, audiobook
    publisher: Mapped[str | None] = mapped_column(String(255))
    publication_year: Mapped[int | None] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    book: Mapped["Book"] = relationship(back_populates="editions")


class BookTag(Base):
    """Tags/tropes for books (genres, tropes, themes)."""

    __tablename__ = "book_tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)

    # Tag categorization
    category: Mapped[str] = mapped_column(String(50), index=True)  # genre, trope, theme, setting
    description: Mapped[str | None] = mapped_column(Text)

    # For filtering
    is_romantasy_indicator: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    books: Mapped[list["Book"]] = relationship(secondary=book_tag_association, back_populates="tags")


# Forward reference
from app.models.rating import Rating  # noqa: E402
