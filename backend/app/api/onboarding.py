"""
Onboarding API endpoints.

Handles new user onboarding flow:
- Preference questionnaire
- Starter book ratings
- Onboarding status tracking
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import auth_service
from app.services.onboarding_service import (
    get_onboarding_status,
    get_starter_books,
    get_trope_options,
    rate_starter_books,
    save_preferences,
)

router = APIRouter()


class PreferencesRequest(BaseModel):
    spice_preference: int | None = Field(None, ge=0, le=5)
    prefers_ya: bool | None = None
    favorite_tropes: list[str] | None = None
    avoid_tropes: list[str] | None = None


class BookRating(BaseModel):
    book_id: int
    rating: int = Field(..., ge=1, le=5)


class StarterRatingsRequest(BaseModel):
    ratings: list[BookRating]


@router.get("/status")
async def get_status(
    current_user=Depends(auth_service.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get onboarding completion status.

    Returns which onboarding steps are complete and what's next.
    """
    return get_onboarding_status(db, current_user.id)


@router.post("/preferences")
async def set_preferences(
    request: PreferencesRequest,
    current_user=Depends(auth_service.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Save user preferences from onboarding questionnaire.

    Sets spice level preference, YA preference, and trope preferences.
    """
    success = save_preferences(
        db,
        current_user.id,
        spice_preference=request.spice_preference,
        prefers_ya=request.prefers_ya,
        favorite_tropes=request.favorite_tropes,
        avoid_tropes=request.avoid_tropes,
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to save preferences")

    return {"message": "Preferences saved"}


@router.get("/starter-books")
async def get_starter_books_endpoint(
    current_user=Depends(auth_service.get_current_user),
    db: Session = Depends(get_db),
    limit: int = 20,
):
    """
    Get popular books for manual rating during onboarding.

    Returns a diverse set of well-known Romantasy books.
    Users can rate these to bootstrap their recommendations.
    """
    return get_starter_books(db, limit=limit)


@router.post("/starter-ratings")
async def submit_starter_ratings(
    request: StarterRatingsRequest,
    current_user=Depends(auth_service.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Submit ratings for starter books.

    After rating at least 5 books, similarity computation is triggered
    and the user can receive personalized recommendations.
    """
    ratings_data = [{"book_id": r.book_id, "rating": r.rating} for r in request.ratings]
    result = rate_starter_books(db, current_user.id, ratings_data)

    return result


@router.get("/tropes")
async def get_tropes(
    db: Session = Depends(get_db),
):
    """
    Get available tropes for preference selection.

    Returns list of tropes with names and descriptions.
    """
    return get_trope_options(db)


@router.get("/spice-levels")
async def get_spice_levels():
    """
    Get spice level descriptions for preference selection.
    """
    return [
        {"level": 0, "name": "No Spice", "description": "No romance or fade-to-black only"},
        {"level": 1, "name": "Mild", "description": "Kissing, mild physical affection"},
        {"level": 2, "name": "Warm", "description": "Some steamy scenes, closed door"},
        {"level": 3, "name": "Hot", "description": "Open door, moderate detail"},
        {"level": 4, "name": "Spicy", "description": "Explicit scenes, significant detail"},
        {"level": 5, "name": "Scorching", "description": "Very explicit, frequent scenes"},
    ]
