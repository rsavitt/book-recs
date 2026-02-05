"""
Onboarding service.

Handles new user onboarding:
- Preference questionnaire (spice level, YA preference, tropes)
- Manual book selection for cold start
- Onboarding progress tracking
"""

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.book import Book, BookTag
from app.models.rating import Rating
from app.models.user import User
from app.services.similarity import compute_user_similarity


def get_onboarding_status(db: Session, user_id: int) -> dict:
    """
    Get the user's onboarding completion status.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        Dict with onboarding status
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"error": "User not found"}

    # Check ratings count
    rating_count = (
        db.query(func.count(Rating.id))
        .filter(Rating.user_id == user_id, Rating.rating > 0)
        .scalar()
    )

    # Determine completion status
    has_preferences = user.spice_preference is not None or user.prefers_ya is not None
    has_enough_ratings = rating_count >= 5  # Minimum for similarity computation
    has_import = user.last_import_at is not None

    return {
        "user_id": user_id,
        "steps": {
            "preferences_set": has_preferences,
            "has_ratings": has_enough_ratings,
            "has_import": has_import,
        },
        "rating_count": rating_count,
        "is_complete": has_enough_ratings,
        "next_step": _get_next_step(has_preferences, has_enough_ratings, has_import),
    }


def _get_next_step(has_preferences: bool, has_ratings: bool, has_import: bool) -> str | None:
    """Determine the next onboarding step."""
    if not has_ratings and not has_import:
        return "import_or_rate"
    if not has_preferences:
        return "set_preferences"
    return None


def save_preferences(
    db: Session,
    user_id: int,
    spice_preference: int | None = None,
    prefers_ya: bool | None = None,
    favorite_tropes: list[str] | None = None,
    avoid_tropes: list[str] | None = None,
) -> bool:
    """
    Save user preferences from onboarding questionnaire.

    Args:
        db: Database session
        user_id: User ID
        spice_preference: Preferred spice level (0-5)
        prefers_ya: Prefer YA books
        favorite_tropes: List of preferred trope slugs
        avoid_tropes: List of trope slugs to avoid

    Returns:
        True if successful
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False

    if spice_preference is not None:
        user.spice_preference = max(0, min(5, spice_preference))

    if prefers_ya is not None:
        user.prefers_ya = prefers_ya

    # TODO: Store favorite/avoid tropes in a user_trope_preferences table
    # For MVP, we'll use these in the recommendation filters

    db.commit()
    return True


def get_starter_books(db: Session, limit: int = 20) -> list[dict]:
    """
    Get popular Romantasy books for manual rating during onboarding.

    Returns a diverse set of well-known books across different
    spice levels and subgenres.

    Args:
        db: Database session
        limit: Number of books to return

    Returns:
        List of book dicts for the UI
    """
    # Get books from the seed list (high confidence)
    books = (
        db.query(Book)
        .filter(
            Book.is_romantasy,
            Book.romantasy_confidence >= 0.95,  # Seed list books
        )
        .order_by(Book.publication_year.desc())
        .limit(limit * 2)  # Get more to filter for diversity
        .all()
    )

    # Ensure diversity by spice level
    diverse_books = _diversify_by_spice(books, limit)

    return [
        {
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "cover_url": book.cover_url,
            "series_name": book.series_name,
            "spice_level": book.spice_level,
            "is_ya": book.is_ya,
            "tags": [tag.name for tag in book.tags[:5]],
        }
        for book in diverse_books
    ]


def _diversify_by_spice(books: list[Book], limit: int) -> list[Book]:
    """Select books with diverse spice levels."""
    by_spice: dict[int, list[Book]] = {i: [] for i in range(6)}

    for book in books:
        level = book.spice_level if book.spice_level is not None else 3
        by_spice[level].append(book)

    # Round-robin selection from each spice level
    result = []
    level_idx = 0
    while len(result) < limit:
        level = level_idx % 6
        if by_spice[level]:
            result.append(by_spice[level].pop(0))
        level_idx += 1

        # Break if we've exhausted all books
        if all(len(books) == 0 for books in by_spice.values()):
            break

    return result


def rate_starter_books(
    db: Session,
    user_id: int,
    ratings: list[dict],  # [{"book_id": 1, "rating": 5}, ...]
) -> dict:
    """
    Save ratings from the onboarding book selection.

    Args:
        db: Database session
        user_id: User ID
        ratings: List of {book_id, rating} dicts

    Returns:
        Dict with results
    """
    saved = 0
    skipped = 0

    for item in ratings:
        book_id = item.get("book_id")
        rating_value = item.get("rating")

        if not book_id or not rating_value:
            skipped += 1
            continue

        # Check if rating already exists
        existing = (
            db.query(Rating).filter(Rating.user_id == user_id, Rating.book_id == book_id).first()
        )

        if existing:
            existing.rating = rating_value
            existing.updated_at = datetime.utcnow()
        else:
            rating = Rating(
                user_id=user_id,
                book_id=book_id,
                rating=rating_value,
                source="onboarding",
            )
            db.add(rating)

        saved += 1

    db.commit()

    # Compute similarity after rating if we have enough
    rating_count = (
        db.query(func.count(Rating.id))
        .filter(Rating.user_id == user_id, Rating.rating > 0)
        .scalar()
    )

    similarity_computed = False
    if rating_count >= 5:
        try:
            compute_user_similarity(db, user_id)
            similarity_computed = True
        except Exception:
            pass  # Not critical if this fails

    return {
        "saved": saved,
        "skipped": skipped,
        "total_ratings": rating_count,
        "similarity_computed": similarity_computed,
        "can_get_recommendations": rating_count >= 5,
    }


def get_trope_options(db: Session) -> list[dict]:
    """
    Get available tropes for the preference questionnaire.

    Returns:
        List of trope dicts with name, slug, description
    """
    tropes = db.query(BookTag).filter(BookTag.category == "trope").order_by(BookTag.name).all()

    return [
        {
            "slug": tag.slug,
            "name": tag.name,
            "description": tag.description,
        }
        for tag in tropes
    ]
