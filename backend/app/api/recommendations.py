from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.book import Book
from app.schemas.recommendation import RecommendationFilters, RecommendationResponse
from app.services import auth_service, recommendation_service

router = APIRouter()


@router.get("/popular", response_model=list[RecommendationResponse])
async def get_popular_books(
    db: Session = Depends(get_db),
    limit: int = Query(20, le=50),
):
    """
    Get popular Romantasy books (no login required).

    Returns highly-rated books that are good starting points.
    """
    # Get books with highest average ratings (minimum 1 rating for seeded data)
    popular = (
        db.query(Book)
        .filter(Book.is_romantasy)
        .order_by(Book.romantasy_confidence.desc(), Book.publication_year.desc())
        .limit(limit)
        .all()
    )

    return [
        RecommendationResponse(
            book_id=book.id,
            title=book.title,
            author=book.author,
            cover_url=book.cover_url,
            spice_level=book.spice_level,
            is_ya=book.is_ya,
            score=book.romantasy_confidence or 0.9,
            reason="Popular in the Romantasy community",
        )
        for book in popular
    ]


@router.post("/quick", response_model=list[RecommendationResponse])
async def get_quick_recommendations(
    liked_book_ids: list[int] = Body(..., embed=True),
    db: Session = Depends(get_db),
    limit: int = Query(20, le=50),
):
    """
    Get quick recommendations based on selected favorite books (no login required).

    Select a few books you love and get instant recommendations.
    """
    if not liked_book_ids:
        return []

    # Get the liked books
    liked_books = db.query(Book).filter(Book.id.in_(liked_book_ids)).all()
    if not liked_books:
        return []

    # Collect authors and series from liked books
    liked_authors = {b.author_normalized for b in liked_books}
    liked_series = {b.series_name for b in liked_books if b.series_name}

    # Get tags from liked books
    liked_tag_ids = set()
    for book in liked_books:
        for tag in book.tags:
            liked_tag_ids.add(tag.id)

    # Find similar books:
    # 1. Same series (different books)
    # 2. Same author (different books)
    # 3. Similar tropes/tags
    recommendations = []
    seen_ids = set(liked_book_ids)

    # Same series, different books
    if liked_series:
        series_books = (
            db.query(Book)
            .filter(
                Book.series_name.in_(liked_series),
                Book.id.notin_(seen_ids),
                Book.is_romantasy,
            )
            .order_by(Book.series_position)
            .limit(10)
            .all()
        )
        for book in series_books:
            if book.id not in seen_ids:
                recommendations.append((book, 0.95, f"More from the {book.series_name} series"))
                seen_ids.add(book.id)

    # Same author, different books
    author_books = (
        db.query(Book)
        .filter(
            Book.author_normalized.in_(liked_authors),
            Book.id.notin_(seen_ids),
            Book.is_romantasy,
        )
        .limit(10)
        .all()
    )
    for book in author_books:
        if book.id not in seen_ids:
            recommendations.append((book, 0.9, f"More from {book.author}"))
            seen_ids.add(book.id)

    # Similar tags - find books with overlapping tags
    if liked_tag_ids:
        from sqlalchemy import func

        from app.models.book import book_tag_association

        similar_books = (
            db.query(Book, func.count(book_tag_association.c.tag_id).label('tag_count'))
            .join(book_tag_association, Book.id == book_tag_association.c.book_id)
            .filter(
                book_tag_association.c.tag_id.in_(liked_tag_ids),
                Book.id.notin_(seen_ids),
                Book.is_romantasy,
            )
            .group_by(Book.id)
            .order_by(func.count(book_tag_association.c.tag_id).desc())
            .limit(20)
            .all()
        )
        for book, tag_count in similar_books:
            if book.id not in seen_ids:
                recommendations.append((book, 0.7 + (tag_count * 0.05), "Similar vibes to books you like"))
                seen_ids.add(book.id)

    # Sort by score and limit
    recommendations.sort(key=lambda x: x[1], reverse=True)

    return [
        RecommendationResponse(
            book_id=book.id,
            title=book.title,
            author=book.author,
            cover_url=book.cover_url,
            spice_level=book.spice_level,
            is_ya=book.is_ya,
            score=score,
            reason=reason,
        )
        for book, score, reason in recommendations[:limit]
    ]


@router.get("/", response_model=list[RecommendationResponse])
async def get_recommendations(
    current_user=Depends(auth_service.get_current_user),
    db: Session = Depends(get_db),
    # Filters
    spice_min: int | None = Query(None, ge=0, le=5),
    spice_max: int | None = Query(None, ge=0, le=5),
    is_ya: bool | None = Query(None),
    tropes: list[str] | None = Query(None),
    exclude_tropes: list[str] | None = Query(None),
    exclude_why_choose: bool | None = Query(None, description="Filter out Why Choose/Reverse Harem books. Defaults to user preference."),
    # Pagination
    limit: int = Query(20, le=50),
    offset: int = Query(0),
):
    """
    Get personalized Romantasy recommendations.

    Recommendations are based on users with similar reading tastes.
    Filter by spice level, age category, tropes, and Why Choose preference.
    """
    # Use user preference as default for exclude_why_choose
    if exclude_why_choose is None:
        exclude_why_choose = current_user.exclude_why_choose

    filters = RecommendationFilters(
        spice_min=spice_min,
        spice_max=spice_max,
        is_ya=is_ya,
        include_tropes=tropes,
        exclude_tropes=exclude_tropes,
        exclude_why_choose=exclude_why_choose,
    )

    return recommendation_service.get_recommendations(
        db,
        user_id=current_user.id,
        filters=filters,
        limit=limit,
        offset=offset,
    )


@router.post("/{book_id}/feedback")
async def submit_feedback(
    book_id: int,
    feedback: str = Query(..., regex="^(interested|not_interested|already_read)$"),
    current_user=Depends(auth_service.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Submit feedback on a recommendation.

    - interested: Save to "want to read" list
    - not_interested: Hide from future recommendations
    - already_read: Mark as read (will prompt for rating)
    """
    recommendation_service.record_feedback(
        db,
        user_id=current_user.id,
        book_id=book_id,
        feedback=feedback,
    )
    return {"status": "recorded"}


@router.get("/explain/{book_id}")
async def explain_recommendation(
    book_id: int,
    current_user=Depends(auth_service.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get detailed explanation for why a book was recommended.

    Returns information about similar users who liked this book
    and what books you have in common with them.
    """
    return recommendation_service.get_recommendation_explanation(
        db,
        user_id=current_user.id,
        book_id=book_id,
    )
