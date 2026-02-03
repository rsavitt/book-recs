from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.book import Book
from app.models.rating import Rating, Shelf
from app.models.similarity import UserSimilarity
from app.models.user import User
from app.schemas.user import RatingStats, SimilarUser, UserPreferencesUpdate, UserProfile


def get_user_profile(db: Session, user_id: int) -> UserProfile:
    """Get user profile with reading stats."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None

    # Calculate stats
    stats = _calculate_rating_stats(db, user_id)
    top_shelves = _get_top_shelves(db, user_id)

    return UserProfile(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        bio=user.bio,
        is_public=user.is_public,
        created_at=user.created_at,
        last_import_at=user.last_import_at,
        stats=stats,
        top_shelves=top_shelves,
        spice_preference=user.spice_preference,
        prefers_ya=user.prefers_ya,
        exclude_why_choose=user.exclude_why_choose,
    )


def _calculate_rating_stats(db: Session, user_id: int) -> RatingStats:
    """Calculate rating statistics for a user."""
    ratings = db.query(Rating).filter(Rating.user_id == user_id).all()

    if not ratings:
        return RatingStats(
            total_books=0,
            total_rated=0,
            average_rating=0.0,
            rating_distribution={1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
        )

    rated = [r for r in ratings if r.rating > 0]
    distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in rated:
        if r.rating in distribution:
            distribution[r.rating] += 1

    avg = sum(r.rating for r in rated) / len(rated) if rated else 0.0

    return RatingStats(
        total_books=len(ratings),
        total_rated=len(rated),
        average_rating=round(avg, 2),
        rating_distribution=distribution,
    )


def _get_top_shelves(db: Session, user_id: int, limit: int = 10) -> list[str]:
    """Get user's most used shelves."""
    result = (
        db.query(Shelf.shelf_name, func.count(Shelf.id).label("count"))
        .filter(Shelf.user_id == user_id)
        .group_by(Shelf.shelf_name)
        .order_by(func.count(Shelf.id).desc())
        .limit(limit)
        .all()
    )
    return [row.shelf_name for row in result]


def update_preferences(db: Session, user_id: int, preferences: UserPreferencesUpdate) -> None:
    """Update user preferences."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return

    update_data = preferences.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()


def get_public_profile(db: Session, username: str) -> UserProfile | None:
    """Get a user's public profile if they've opted in."""
    user = db.query(User).filter(User.username == username, User.is_public).first()
    if not user:
        return None
    return get_user_profile(db, user.id)


def get_similar_users(db: Session, user_id: int, limit: int = 20) -> list[SimilarUser]:
    """Get users with similar reading tastes."""
    similarities = (
        db.query(UserSimilarity)
        .filter(UserSimilarity.user_id == user_id)
        .order_by(UserSimilarity.adjusted_similarity.desc())
        .limit(limit)
        .all()
    )

    results = []
    for sim in similarities:
        neighbor = db.query(User).filter(User.id == sim.neighbor_id).first()
        if not neighbor or not neighbor.is_public:
            continue

        # Get shared high-rated books
        shared_favorites = _get_shared_favorites(db, user_id, sim.neighbor_id)

        results.append(
            SimilarUser(
                username=neighbor.username,
                display_name=neighbor.display_name,
                similarity_score=round(sim.adjusted_similarity, 3),
                overlap_count=sim.overlap_count,
                shared_favorites=shared_favorites[:5],
            )
        )

    return results


def _get_shared_favorites(db: Session, user_id: int, neighbor_id: int, min_rating: int = 4) -> list[str]:
    """Get books that both users rated highly."""
    user_favorites = (
        db.query(Rating.book_id)
        .filter(Rating.user_id == user_id, Rating.rating >= min_rating)
        .subquery()
    )

    shared = (
        db.query(Book.title)
        .join(Rating, Rating.book_id == Book.id)
        .filter(
            Rating.user_id == neighbor_id,
            Rating.rating >= min_rating,
            Rating.book_id.in_(user_favorites),
        )
        .limit(10)
        .all()
    )

    return [row.title for row in shared]
