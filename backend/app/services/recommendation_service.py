"""
Recommendation service.

Generates personalized Romantasy recommendations using collaborative filtering:

1. Get user's top-K similar neighbors
2. For each Romantasy book the user hasn't read:
   - Calculate weighted average rating from neighbors
   - Apply filters (spice, YA, tropes)
3. Rank by predicted rating with diversity constraints
4. Generate explanations for each recommendation
"""

from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.book import Book
from app.models.rating import Rating
from app.models.similarity import UserSimilarity
from app.models.user import User
from app.schemas.recommendation import (
    RecommendationExplanation,
    RecommendationFilters,
    RecommendationResponse,
)

settings = get_settings()


@dataclass
class ScoredBook:
    """A book with its predicted rating and metadata."""

    book: Book
    predicted_rating: float
    confidence: float
    contributing_neighbors: list[tuple[int, float, float]]  # (user_id, similarity, rating)
    neighbor_count: int
    average_neighbor_rating: float


@dataclass
class RecommendationEngine:
    """
    Generates recommendations using collaborative filtering.

    Algorithm:
    1. Get user's similar neighbors
    2. Find all Romantasy books rated by neighbors that user hasn't read
    3. Score each book: weighted average of neighbor ratings
    4. Apply filters and diversity constraints
    5. Return top recommendations with explanations
    """

    db: Session
    user_id: int
    filters: RecommendationFilters = field(default_factory=RecommendationFilters)
    min_neighbors_for_rec: int = 2  # Minimum neighbors who rated a book to recommend it
    diversity_author_limit: int = 3  # Max books from same author in results

    def get_recommendations(self, limit: int = 20, offset: int = 0) -> list[RecommendationResponse]:
        """
        Generate personalized recommendations.

        Returns:
            List of RecommendationResponse objects
        """
        # Get user's similar neighbors
        neighbors = self._get_neighbors()

        if not neighbors:
            # Cold start: return popular Romantasy books
            return self._get_popular_recommendations(limit, offset)

        # Get user's already-read books
        read_book_ids = self._get_read_book_ids()

        # Score candidate books
        scored_books = self._score_candidate_books(neighbors, read_book_ids)

        if not scored_books:
            return self._get_popular_recommendations(limit, offset)

        # Apply filters
        filtered_books = self._apply_filters(scored_books)

        # Apply diversity constraints
        diverse_books = self._apply_diversity(filtered_books)

        # Paginate
        paginated = diverse_books[offset : offset + limit]

        # Convert to response objects
        return [self._to_response(scored) for scored in paginated]

    def _get_neighbors(self) -> list[tuple[int, float]]:
        """Get user's similar neighbors as (neighbor_id, similarity)."""
        neighbors = (
            self.db.query(UserSimilarity.neighbor_id, UserSimilarity.adjusted_similarity)
            .filter(
                UserSimilarity.user_id == self.user_id,
                UserSimilarity.adjusted_similarity > 0,
            )
            .order_by(UserSimilarity.adjusted_similarity.desc())
            .limit(100)  # Use top 100 neighbors for scoring
            .all()
        )
        return list(neighbors)

    def _get_read_book_ids(self) -> set[int]:
        """Get IDs of books the user has already read/rated."""
        ratings = self.db.query(Rating.book_id).filter(Rating.user_id == self.user_id).all()
        return {r.book_id for r in ratings}

    def _score_candidate_books(
        self,
        neighbors: list[tuple[int, float]],
        exclude_book_ids: set[int],
    ) -> list[ScoredBook]:
        """
        Score all candidate Romantasy books based on neighbor ratings.

        Uses weighted average: score = Σ(sim * rating) / Σ(sim)
        """
        neighbor_ids = [n_id for n_id, _ in neighbors]
        neighbor_sim = dict(neighbors)

        # Get all ratings from neighbors for Romantasy books
        neighbor_ratings = (
            self.db.query(Rating.book_id, Rating.user_id, Rating.rating)
            .join(Book, Book.id == Rating.book_id)
            .filter(
                Rating.user_id.in_(neighbor_ids),
                Rating.rating > 0,
                Book.is_romantasy,
                ~Rating.book_id.in_(exclude_book_ids) if exclude_book_ids else True,
            )
            .all()
        )

        # Group ratings by book
        book_ratings: dict[int, list[tuple[int, float, float]]] = defaultdict(list)
        for book_id, user_id, rating in neighbor_ratings:
            sim = neighbor_sim.get(user_id, 0)
            if sim > 0:
                book_ratings[book_id].append((user_id, sim, float(rating)))

        # Score each book
        scored = []
        for book_id, ratings in book_ratings.items():
            if len(ratings) < self.min_neighbors_for_rec:
                continue

            # Weighted average
            total_weight = sum(sim for _, sim, _ in ratings)
            weighted_sum = sum(sim * rating for _, sim, rating in ratings)
            predicted_rating = weighted_sum / total_weight if total_weight > 0 else 0

            # Confidence based on neighbor count and total similarity
            confidence = min(len(ratings) / 10, 1.0) * min(total_weight / 2, 1.0)

            # Get book object
            book = self.db.query(Book).filter(Book.id == book_id).first()
            if not book:
                continue

            avg_rating = sum(r for _, _, r in ratings) / len(ratings)

            scored.append(
                ScoredBook(
                    book=book,
                    predicted_rating=predicted_rating,
                    confidence=confidence,
                    contributing_neighbors=ratings,
                    neighbor_count=len(ratings),
                    average_neighbor_rating=avg_rating,
                )
            )

        # Sort by predicted rating (descending)
        scored.sort(key=lambda x: x.predicted_rating, reverse=True)
        return scored

    def _apply_filters(self, books: list[ScoredBook]) -> list[ScoredBook]:
        """Apply user filters to scored books."""
        filtered = []

        for scored in books:
            book = scored.book

            # Spice level filter
            if self.filters.spice_min is not None:
                if book.spice_level is None or book.spice_level < self.filters.spice_min:
                    continue

            if self.filters.spice_max is not None:
                if book.spice_level is None or book.spice_level > self.filters.spice_max:
                    continue

            # YA filter
            if self.filters.is_ya is not None:
                if book.is_ya != self.filters.is_ya:
                    continue

            # Why Choose filter
            if self.filters.exclude_why_choose:
                if book.is_why_choose and book.why_choose_confidence >= 0.5:
                    continue

            # Include tropes filter
            if self.filters.include_tropes:
                book_tags = {tag.slug for tag in book.tags}
                if not any(t.lower() in book_tags for t in self.filters.include_tropes):
                    continue

            # Exclude tropes filter
            if self.filters.exclude_tropes:
                book_tags = {tag.slug for tag in book.tags}
                if any(t.lower() in book_tags for t in self.filters.exclude_tropes):
                    continue

            filtered.append(scored)

        return filtered

    def _apply_diversity(self, books: list[ScoredBook]) -> list[ScoredBook]:
        """
        Apply diversity constraints to avoid recommending too many books
        from the same author.
        """
        author_counts: dict[str, int] = defaultdict(int)
        diverse = []

        for scored in books:
            author = scored.book.author.lower()

            if author_counts[author] >= self.diversity_author_limit:
                continue

            diverse.append(scored)
            author_counts[author] += 1

        return diverse

    def _to_response(self, scored: ScoredBook) -> RecommendationResponse:
        """Convert a ScoredBook to a RecommendationResponse."""
        book = scored.book

        # Get top shared books with contributing neighbors
        top_shared = self._get_shared_books_with_neighbors(
            [n_id for n_id, _, _ in scored.contributing_neighbors[:5]]
        )

        # Generate explanation text
        explanation_text = self._generate_explanation_text(scored, top_shared)

        return RecommendationResponse(
            book_id=book.id,
            title=book.title,
            author=book.author,
            cover_url=book.cover_url,
            publication_year=book.publication_year,
            series_name=book.series_name,
            series_position=book.series_position,
            spice_level=book.spice_level,
            is_ya=book.is_ya,
            tags=[tag.name for tag in book.tags],
            predicted_rating=round(scored.predicted_rating, 2),
            confidence=round(scored.confidence, 2),
            explanation=RecommendationExplanation(
                similar_user_count=scored.neighbor_count,
                average_neighbor_rating=round(scored.average_neighbor_rating, 2),
                top_shared_books=top_shared[:5],
                sample_explanation=explanation_text,
            ),
        )

    def _get_shared_books_with_neighbors(self, neighbor_ids: list[int]) -> list[str]:
        """Get titles of highly-rated books shared with neighbors."""
        if not neighbor_ids:
            return []

        # Get books the user rated highly
        user_favorites = (
            self.db.query(Rating.book_id)
            .filter(Rating.user_id == self.user_id, Rating.rating >= 4)
            .subquery()
        )

        # Get books neighbors also rated highly
        shared = (
            self.db.query(Book.title)
            .join(Rating, Rating.book_id == Book.id)
            .filter(
                Rating.user_id.in_(neighbor_ids),
                Rating.rating >= 4,
                Rating.book_id.in_(user_favorites),
            )
            .distinct()
            .limit(10)
            .all()
        )

        return [title for (title,) in shared]

    def _generate_explanation_text(self, scored: ScoredBook, shared_books: list[str]) -> str:
        """Generate a human-readable explanation for the recommendation."""
        count = scored.neighbor_count
        avg = round(scored.average_neighbor_rating, 1)

        if shared_books:
            books_text = f" who also loved {shared_books[0]}"
            if len(shared_books) > 1:
                books_text += f" and {shared_books[1]}"
        else:
            books_text = ""

        return f"{count} similar reader{'s' if count != 1 else ''}{books_text} rated this {avg}★ average"

    def _get_popular_recommendations(self, limit: int, offset: int) -> list[RecommendationResponse]:
        """
        Fallback: return popular Romantasy books for cold start users.
        """
        # Get user's read books to exclude
        read_book_ids = self._get_read_book_ids()

        # Query for popular Romantasy books
        query = self.db.query(Book).filter(
            Book.is_romantasy,
            ~Book.id.in_(read_book_ids) if read_book_ids else True,
        )

        # Apply filters
        if self.filters.spice_min is not None:
            query = query.filter(Book.spice_level >= self.filters.spice_min)
        if self.filters.spice_max is not None:
            query = query.filter(Book.spice_level <= self.filters.spice_max)
        if self.filters.is_ya is not None:
            query = query.filter(Book.is_ya == self.filters.is_ya)
        if self.filters.exclude_why_choose:
            query = query.filter(or_(not Book.is_why_choose, Book.why_choose_confidence < 0.5))

        # Order by confidence (seed list books) then publication year
        books = (
            query.order_by(Book.romantasy_confidence.desc(), Book.publication_year.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return [
            RecommendationResponse(
                book_id=book.id,
                title=book.title,
                author=book.author,
                cover_url=book.cover_url,
                publication_year=book.publication_year,
                series_name=book.series_name,
                series_position=book.series_position,
                spice_level=book.spice_level,
                is_ya=book.is_ya,
                tags=[tag.name for tag in book.tags],
                predicted_rating=0.0,
                confidence=0.0,
                explanation=RecommendationExplanation(
                    similar_user_count=0,
                    average_neighbor_rating=0.0,
                    top_shared_books=[],
                    sample_explanation="Popular Romantasy book",
                ),
            )
            for book in books
        ]


def get_recommendations(
    db: Session,
    user_id: int,
    filters: RecommendationFilters,
    limit: int = 20,
    offset: int = 0,
) -> list[RecommendationResponse]:
    """
    Get personalized Romantasy recommendations for a user.

    Args:
        db: Database session
        user_id: User to get recommendations for
        filters: Filtering options
        limit: Maximum number of recommendations
        offset: Pagination offset

    Returns:
        List of RecommendationResponse
    """
    engine = RecommendationEngine(db=db, user_id=user_id, filters=filters)
    return engine.get_recommendations(limit=limit, offset=offset)


def record_feedback(db: Session, user_id: int, book_id: int, feedback: str) -> None:
    """
    Record user feedback on a recommendation.

    Args:
        db: Database session
        user_id: User providing feedback
        book_id: Book being rated
        feedback: "interested", "not_interested", or "already_read"
    """
    # TODO: Store feedback in a dedicated table for improving recommendations
    # For now, if "already_read", we could prompt for a rating

    if feedback == "already_read":
        # Check if rating exists
        existing = (
            db.query(Rating).filter(Rating.user_id == user_id, Rating.book_id == book_id).first()
        )
        if not existing:
            # Create unrated entry so it's excluded from future recs
            rating = Rating(
                user_id=user_id,
                book_id=book_id,
                rating=0,  # Unrated
                source="feedback",
            )
            db.add(rating)
            db.commit()


def get_recommendation_explanation(db: Session, user_id: int, book_id: int) -> dict:
    """
    Get detailed explanation for why a book was recommended.

    Args:
        db: Database session
        user_id: User who received the recommendation
        book_id: Book to explain

    Returns:
        Detailed explanation dict
    """
    # Get user's neighbors who rated this book
    neighbors = (
        db.query(
            UserSimilarity.neighbor_id,
            UserSimilarity.adjusted_similarity,
            Rating.rating,
            User.username,
        )
        .join(
            Rating,
            and_(
                Rating.user_id == UserSimilarity.neighbor_id,
                Rating.book_id == book_id,
            ),
        )
        .join(User, User.id == UserSimilarity.neighbor_id)
        .filter(
            UserSimilarity.user_id == user_id,
            User.is_public,  # Only show public users
        )
        .order_by(UserSimilarity.adjusted_similarity.desc())
        .limit(10)
        .all()
    )

    # Get shared high-rated books with these neighbors
    neighbor_ids = [n.neighbor_id for n in neighbors]
    shared_books = []

    if neighbor_ids:
        user_favorites = (
            db.query(Rating.book_id)
            .filter(Rating.user_id == user_id, Rating.rating >= 4)
            .subquery()
        )

        shared = (
            db.query(Book.title, func.count(Rating.id).label("count"))
            .join(Rating, Rating.book_id == Book.id)
            .filter(
                Rating.user_id.in_(neighbor_ids),
                Rating.rating >= 4,
                Rating.book_id.in_(user_favorites),
            )
            .group_by(Book.id, Book.title)
            .order_by(func.count(Rating.id).desc())
            .limit(5)
            .all()
        )
        shared_books = [{"title": title, "shared_by": count} for title, count in shared]

    # Get the book
    book = db.query(Book).filter(Book.id == book_id).first()

    return {
        "book_id": book_id,
        "book_title": book.title if book else None,
        "similar_users": [
            {
                "username": n.username,
                "similarity": round(n.adjusted_similarity, 3),
                "rating": n.rating,
            }
            for n in neighbors
        ],
        "shared_books": shared_books,
        "total_neighbors_who_rated": len(neighbors),
        "average_rating": (
            round(sum(n.rating for n in neighbors) / len(neighbors), 2) if neighbors else 0
        ),
    }
