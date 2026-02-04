from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class BookReviewEmbedding(Base):
    """Aggregated review embedding per book from UCSD Goodreads reviews."""

    __tablename__ = "book_review_embeddings"

    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), unique=True, index=True)

    embedding = Column(Vector(384), nullable=False)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    total_review_words: Mapped[int] = mapped_column(Integer, default=0)
    avg_review_rating: Mapped[float | None] = mapped_column(Float)
    source_dataset: Mapped[str] = mapped_column(String(50), default="ucsd_goodreads")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    book: Mapped["Book"] = relationship(back_populates="review_embedding")


class TropeSeedEmbedding(Base):
    """Seed phrase embeddings for trope classification."""

    __tablename__ = "trope_seed_embeddings"

    id: Mapped[int] = mapped_column(primary_key=True)
    trope_slug: Mapped[str] = mapped_column(String(100), index=True)
    seed_phrase: Mapped[str] = mapped_column(Text, nullable=False)
    embedding = Column(Vector(384), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BookTropeScore(Base):
    """Precomputed cosine similarity between book embeddings and trope centroids."""

    __tablename__ = "book_trope_scores"
    __table_args__ = (UniqueConstraint("book_id", "trope_slug", name="uq_book_trope_score"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), index=True)
    trope_slug: Mapped[str] = mapped_column(String(100), index=True)
    similarity_score: Mapped[float] = mapped_column(Float, index=True)
    auto_tagged: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# Forward reference
from app.models.book import Book  # noqa: E402, F401
