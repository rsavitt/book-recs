"""
Reddit-sourced data models for book recommendations.

These models store aggregated signals from Reddit discussions (primarily r/romantasy)
to enhance book recommendations with community-driven insights.
"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class BookRedditMetrics(Base):
    """
    Aggregated Reddit metrics for a book.

    Stores mention counts, sentiment, and trope validation data
    collected from Reddit discussions.
    """

    __tablename__ = "book_reddit_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )

    # Engagement counts
    mention_count: Mapped[int] = mapped_column(Integer, default=0)
    recommendation_count: Mapped[int] = mapped_column(Integer, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, default=0)  # DNF/negative mentions

    # Sentiment score: -1 (negative) to +1 (positive)
    sentiment_score: Mapped[float] = mapped_column(Float, default=0.0, index=True)

    # Trope validation: {"enemies-to-lovers": 15, "slow-burn": 8}
    tropes_mentioned: Mapped[dict | None] = mapped_column(JSON, default=dict)

    # Timestamps
    first_seen: Mapped[date | None] = mapped_column(Date)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationship
    book: Mapped["Book"] = relationship(back_populates="reddit_metrics")

    def __repr__(self) -> str:
        return f"<BookRedditMetrics book_id={self.book_id} mentions={self.mention_count}>"


class BookRecommendationEdge(Base):
    """
    Reddit-sourced book-to-book recommendation edges.

    Captures "if you liked X, try Y" relationships extracted from
    Reddit discussions.
    """

    __tablename__ = "book_recommendation_edges"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"),
        index=True,
    )
    target_book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"),
        index=True,
    )

    # Edge strength
    mention_count: Mapped[int] = mapped_column(Integer, default=1)
    weight: Mapped[float] = mapped_column(Float, default=0.0)  # Normalized 0-1

    # Sample context (anonymized, no usernames)
    sample_context: Mapped[str | None] = mapped_column(Text)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    source_book: Mapped["Book"] = relationship(
        foreign_keys=[source_book_id],
        back_populates="recommendation_edges_as_source",
    )
    target_book: Mapped["Book"] = relationship(
        foreign_keys=[target_book_id],
        back_populates="recommendation_edges_as_target",
    )

    __table_args__ = (
        UniqueConstraint("source_book_id", "target_book_id", name="uq_recommendation_edge"),
    )

    def __repr__(self) -> str:
        return f"<BookRecommendationEdge {self.source_book_id} -> {self.target_book_id}>"


# Forward reference for type hints
from app.models.book import Book  # noqa: E402
