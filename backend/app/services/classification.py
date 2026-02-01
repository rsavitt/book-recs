"""
Romantasy classification service.

Classifies books as Romantasy using multiple signals:
1. Seed list membership (high confidence)
2. User shelf signals (aggregated across users)
3. Tag inference from shelves
4. Author heuristics (if author has Romantasy books, others might be too)
"""

from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.book import Book, BookTag, book_tag_association
from app.models.rating import Shelf
from app.data.tags import (
    TAGS,
    ROMANTASY_INDICATOR_TAGS,
    ROMANTASY_SUPPORTING_TAGS,
    normalize_shelf_to_tag,
)


@dataclass
class ClassificationResult:
    """Result of classifying a book."""

    is_romantasy: bool
    confidence: float  # 0.0 to 1.0
    reasons: list[str]
    inferred_tags: list[str]


class RomantasyClassifier:
    """
    Classifies books as Romantasy based on multiple signals.

    Confidence scoring:
    - Seed list: 1.0 (certain)
    - Strong shelf signals (>= 3 users): 0.8-0.95
    - Moderate shelf signals (1-2 users): 0.5-0.7
    - Author heuristic only: 0.3-0.5
    - No signals: 0.0
    """

    # Minimum confidence to auto-classify as Romantasy
    AUTO_CLASSIFY_THRESHOLD = 0.6

    # Weights for different signal types
    SEED_WEIGHT = 1.0
    SHELF_INDICATOR_WEIGHT = 0.3  # Per user with indicator shelf
    SHELF_SUPPORTING_WEIGHT = 0.1  # Per user with supporting shelf
    AUTHOR_WEIGHT = 0.2  # If author has other Romantasy books

    def __init__(self, db: Session):
        self.db = db
        self._romantasy_authors: set[str] | None = None

    def classify(self, book: Book) -> ClassificationResult:
        """
        Classify a book as Romantasy or not.

        Args:
            book: Book to classify

        Returns:
            ClassificationResult with confidence and reasoning
        """
        confidence = 0.0
        reasons = []
        inferred_tags = []

        # Check if already in seed list (via existing classification)
        if book.is_romantasy and book.romantasy_confidence >= 0.95:
            return ClassificationResult(
                is_romantasy=True,
                confidence=1.0,
                reasons=["In curated Romantasy seed list"],
                inferred_tags=[tag.slug for tag in book.tags],
            )

        # Analyze shelf signals
        shelf_confidence, shelf_reasons, shelf_tags = self._analyze_shelf_signals(book.id)
        confidence += shelf_confidence
        reasons.extend(shelf_reasons)
        inferred_tags.extend(shelf_tags)

        # Check author heuristic
        author_confidence, author_reason = self._check_author_heuristic(book.author)
        if author_confidence > 0 and confidence < 0.8:  # Don't over-weight if already confident
            confidence += author_confidence
            if author_reason:
                reasons.append(author_reason)

        # Cap confidence at 0.95 for non-seed books
        confidence = min(confidence, 0.95)

        # Determine classification
        is_romantasy = confidence >= self.AUTO_CLASSIFY_THRESHOLD

        return ClassificationResult(
            is_romantasy=is_romantasy,
            confidence=round(confidence, 3),
            reasons=reasons,
            inferred_tags=list(set(inferred_tags)),
        )

    def _analyze_shelf_signals(
        self, book_id: int
    ) -> tuple[float, list[str], list[str]]:
        """
        Analyze user shelves to determine Romantasy likelihood.

        Returns:
            Tuple of (confidence_score, reasons, inferred_tags)
        """
        # Get all shelves for this book across users
        shelves = (
            self.db.query(Shelf.shelf_name_normalized, func.count(Shelf.id).label("count"))
            .filter(Shelf.book_id == book_id)
            .group_by(Shelf.shelf_name_normalized)
            .all()
        )

        if not shelves:
            return 0.0, [], []

        confidence = 0.0
        reasons = []
        inferred_tags = []
        indicator_count = 0
        supporting_count = 0

        for shelf_name, count in shelves:
            # Normalize to tag
            tag_slug = normalize_shelf_to_tag(shelf_name)

            if shelf_name in ROMANTASY_INDICATOR_TAGS or tag_slug in ROMANTASY_INDICATOR_TAGS:
                indicator_count += count
                if tag_slug:
                    inferred_tags.append(tag_slug)

            elif shelf_name in ROMANTASY_SUPPORTING_TAGS or tag_slug in ROMANTASY_SUPPORTING_TAGS:
                supporting_count += count
                if tag_slug:
                    inferred_tags.append(tag_slug)

            # Also check for direct tag mapping
            if tag_slug and tag_slug not in inferred_tags:
                inferred_tags.append(tag_slug)

        # Calculate confidence from shelf signals
        if indicator_count > 0:
            # Strong signal: users explicitly shelved as romantasy/fae/etc.
            confidence += min(indicator_count * self.SHELF_INDICATOR_WEIGHT, 0.7)
            reasons.append(f"{indicator_count} user(s) shelved with Romantasy indicators")

        if supporting_count > 0:
            # Moderate signal: users shelved with fantasy/romance
            confidence += min(supporting_count * self.SHELF_SUPPORTING_WEIGHT, 0.3)
            if not reasons:  # Only add if no stronger reason
                reasons.append(f"{supporting_count} user(s) shelved with fantasy/romance tags")

        return confidence, reasons, inferred_tags

    def _check_author_heuristic(self, author: str) -> tuple[float, str | None]:
        """
        Check if the author has other confirmed Romantasy books.

        This helps catch books by known Romantasy authors that might not
        have strong shelf signals yet.
        """
        if self._romantasy_authors is None:
            self._load_romantasy_authors()

        author_normalized = author.lower().strip()

        if author_normalized in self._romantasy_authors:
            return self.AUTHOR_WEIGHT, f"Author '{author}' has other Romantasy books"

        return 0.0, None

    def _load_romantasy_authors(self):
        """Load set of authors with confirmed Romantasy books."""
        self._romantasy_authors = set()

        authors = (
            self.db.query(Book.author)
            .filter(Book.is_romantasy == True, Book.romantasy_confidence >= 0.8)
            .distinct()
            .all()
        )

        for (author,) in authors:
            self._romantasy_authors.add(author.lower().strip())


def classify_book(db: Session, book: Book) -> ClassificationResult:
    """
    Convenience function to classify a single book.

    Args:
        db: Database session
        book: Book to classify

    Returns:
        ClassificationResult
    """
    classifier = RomantasyClassifier(db)
    return classifier.classify(book)


def reclassify_all_books(db: Session, min_confidence: float = 0.6) -> dict:
    """
    Reclassify all books in the database.

    This should be run periodically as more users import their libraries,
    providing more shelf signal data.

    Args:
        db: Database session
        min_confidence: Minimum confidence to mark as Romantasy

    Returns:
        Dict with statistics about the reclassification
    """
    classifier = RomantasyClassifier(db)
    classifier.AUTO_CLASSIFY_THRESHOLD = min_confidence

    stats = {
        "total_books": 0,
        "newly_classified": 0,
        "confidence_updated": 0,
        "tags_added": 0,
    }

    # Get all books not in seed list (seed list books keep their classification)
    books = (
        db.query(Book)
        .filter(Book.romantasy_confidence < 0.95)  # Exclude seed list
        .all()
    )

    for book in books:
        stats["total_books"] += 1
        result = classifier.classify(book)

        # Update classification if changed
        if result.is_romantasy != book.is_romantasy:
            book.is_romantasy = result.is_romantasy
            stats["newly_classified"] += 1

        # Update confidence
        if abs(result.confidence - book.romantasy_confidence) > 0.01:
            book.romantasy_confidence = result.confidence
            stats["confidence_updated"] += 1

        # Add inferred tags
        if result.inferred_tags:
            tags_added = _add_tags_to_book(db, book, result.inferred_tags)
            stats["tags_added"] += tags_added

    db.commit()
    return stats


def _add_tags_to_book(db: Session, book: Book, tag_slugs: list[str]) -> int:
    """Add tags to a book if they don't already exist."""
    existing_slugs = {tag.slug for tag in book.tags}
    added = 0

    for slug in tag_slugs:
        if slug in existing_slugs:
            continue

        tag = db.query(BookTag).filter(BookTag.slug == slug).first()
        if tag:
            book.tags.append(tag)
            added += 1

    return added


def get_classification_stats(db: Session) -> dict:
    """
    Get statistics about Romantasy classification in the database.

    Returns:
        Dict with classification statistics
    """
    total_books = db.query(func.count(Book.id)).scalar()
    romantasy_books = db.query(func.count(Book.id)).filter(Book.is_romantasy == True).scalar()
    high_confidence = (
        db.query(func.count(Book.id))
        .filter(Book.is_romantasy == True, Book.romantasy_confidence >= 0.8)
        .scalar()
    )
    seed_list = (
        db.query(func.count(Book.id))
        .filter(Book.is_romantasy == True, Book.romantasy_confidence >= 0.95)
        .scalar()
    )

    return {
        "total_books": total_books,
        "romantasy_books": romantasy_books,
        "romantasy_percentage": round(romantasy_books / total_books * 100, 1) if total_books > 0 else 0,
        "high_confidence_count": high_confidence,
        "seed_list_count": seed_list,
    }
