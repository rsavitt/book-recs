from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserSimilarity(Base):
    """Precomputed similarity scores between users."""

    __tablename__ = "user_similarities"
    __table_args__ = (
        UniqueConstraint("user_id", "neighbor_id", name="unique_user_neighbor_pair"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    neighbor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    # Similarity metrics
    similarity_score: Mapped[float] = mapped_column(Float, index=True)  # -1 to 1 (Pearson) or 0 to 1 (cosine)
    overlap_count: Mapped[int] = mapped_column(Integer)  # Number of books both users rated
    adjusted_similarity: Mapped[float] = mapped_column(Float, index=True)  # After significance weighting

    # Computation metadata
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
