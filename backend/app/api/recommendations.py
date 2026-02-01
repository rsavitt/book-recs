from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.recommendation import RecommendationResponse, RecommendationFilters
from app.services import auth_service, recommendation_service

router = APIRouter()


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
    # Pagination
    limit: int = Query(20, le=50),
    offset: int = Query(0),
):
    """
    Get personalized Romantasy recommendations.

    Recommendations are based on users with similar reading tastes.
    Filter by spice level, age category, and tropes.
    """
    filters = RecommendationFilters(
        spice_min=spice_min,
        spice_max=spice_max,
        is_ya=is_ya,
        include_tropes=tropes,
        exclude_tropes=exclude_tropes,
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
