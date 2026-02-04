"""
Vector-based trope classification service.

Uses precomputed cosine similarity scores between book review embeddings
and trope seed phrase centroids (stored in book_trope_scores table) to
classify books by romantasy tropes.
"""

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.book import Book, BookTag
from app.models.embedding import BookReviewEmbedding, BookTropeScore


@dataclass
class TropeScoreResult:
    """A single trope score for a book."""

    trope_slug: str
    similarity_score: float
    auto_tagged: bool


@dataclass
class TropeClassificationResult:
    """Full trope classification result for a book."""

    book_id: int
    trope_scores: list[TropeScoreResult] = field(default_factory=list)
    auto_tagged: list[str] = field(default_factory=list)
    review_count: int = 0
    confidence: float = 0.0  # Based on review_count: more reviews = higher confidence


class VectorTropeClassifier:
    """
    Classifies books by tropes using precomputed vector similarity scores.

    Reads from the book_trope_scores table (populated by the import pipeline)
    rather than computing embeddings at request time.
    """

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def classify(self, book_id: int) -> TropeClassificationResult:
        """
        Get trope classification for a book from precomputed scores.

        Args:
            book_id: The book to classify

        Returns:
            TropeClassificationResult with sorted scores and auto-tagged tropes
        """
        # Get precomputed scores
        scores = (
            self.db.query(BookTropeScore)
            .filter(BookTropeScore.book_id == book_id)
            .order_by(BookTropeScore.similarity_score.desc())
            .all()
        )

        if not scores:
            return TropeClassificationResult(book_id=book_id)

        # Get review count for confidence estimation
        embedding = (
            self.db.query(BookReviewEmbedding)
            .filter(BookReviewEmbedding.book_id == book_id)
            .first()
        )
        review_count = embedding.review_count if embedding else 0

        # Confidence based on review count: 3 reviews = 0.3, 10 = 0.7, 30+ = 0.95
        if review_count >= 30:
            confidence = 0.95
        elif review_count >= 10:
            confidence = 0.5 + (review_count - 10) * 0.0225  # 0.5 to 0.95
        elif review_count >= 3:
            confidence = 0.2 + (review_count - 3) * 0.0429  # 0.2 to 0.5
        else:
            confidence = 0.0

        trope_scores = []
        auto_tagged = []

        for score in scores:
            trope_scores.append(
                TropeScoreResult(
                    trope_slug=score.trope_slug,
                    similarity_score=score.similarity_score,
                    auto_tagged=score.auto_tagged,
                )
            )
            if score.auto_tagged:
                auto_tagged.append(score.trope_slug)

        return TropeClassificationResult(
            book_id=book_id,
            trope_scores=trope_scores,
            auto_tagged=auto_tagged,
            review_count=review_count,
            confidence=round(confidence, 3),
        )

    def apply_auto_tags(self, book_id: int, dry_run: bool = False) -> list[str]:
        """
        Add auto-tagged tropes to a book's tag associations via BookTag.

        Only adds tags that don't already exist on the book.

        Args:
            book_id: The book to tag
            dry_run: If True, don't actually modify the database

        Returns:
            List of newly added tag slugs
        """
        result = self.classify(book_id)
        if not result.auto_tagged:
            return []

        book = self.db.query(Book).filter(Book.id == book_id).first()
        if not book:
            return []

        existing_slugs = {tag.slug for tag in book.tags}
        added = []

        for trope_slug in result.auto_tagged:
            if trope_slug in existing_slugs:
                continue

            tag = self.db.query(BookTag).filter(BookTag.slug == trope_slug).first()
            if tag and not dry_run:
                book.tags.append(tag)
                added.append(trope_slug)
            elif tag:
                added.append(trope_slug)

        if not dry_run:
            self.db.commit()

        return added

    def get_top_tropes(self, book_id: int, limit: int = 10) -> list[TropeScoreResult]:
        """Get the top N trope scores for a book."""
        result = self.classify(book_id)
        return result.trope_scores[:limit]


def apply_vector_tags_to_all_books(db: Session, dry_run: bool = False) -> dict:
    """
    Bulk apply auto-tagged tropes across all books with embeddings.

    Args:
        db: Database session
        dry_run: If True, don't modify the database

    Returns:
        Statistics dict
    """
    classifier = VectorTropeClassifier(db)

    # Get all book_ids that have embeddings
    book_ids = db.query(BookReviewEmbedding.book_id).all()

    stats = {
        "books_processed": 0,
        "books_with_new_tags": 0,
        "total_tags_added": 0,
    }

    for (book_id,) in book_ids:
        added = classifier.apply_auto_tags(book_id, dry_run=dry_run)
        stats["books_processed"] += 1
        if added:
            stats["books_with_new_tags"] += 1
            stats["total_tags_added"] += len(added)

        if stats["books_processed"] % 100 == 0:
            print(
                f"  Processed {stats['books_processed']}/{len(book_ids)} books, "
                f"added {stats['total_tags_added']} tags..."
            )

    if not dry_run:
        db.commit()

    return stats
