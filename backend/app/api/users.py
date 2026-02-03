from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.user import UserPreferencesUpdate, UserProfile
from app.services import auth_service, user_service

router = APIRouter()


@router.get("/profile", response_model=UserProfile)
async def get_profile(
    current_user=Depends(auth_service.get_current_user),
    db: Session = Depends(get_db),
):
    """Get current user's profile with stats."""
    return user_service.get_user_profile(db, current_user.id)


@router.patch("/preferences")
async def update_preferences(
    preferences: UserPreferencesUpdate,
    current_user=Depends(auth_service.get_current_user),
    db: Session = Depends(get_db),
):
    """Update user preferences (spice level, YA preference, etc.)."""
    user_service.update_preferences(db, current_user.id, preferences)
    return {"status": "updated"}


@router.get("/{username}/public", response_model=UserProfile)
async def get_public_profile(
    username: str,
    db: Session = Depends(get_db),
):
    """Get a user's public profile (if they've opted in)."""
    profile = user_service.get_public_profile(db, username)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or profile is private",
        )
    return profile


@router.get("/neighbors")
async def get_similar_users(
    current_user=Depends(auth_service.get_current_user),
    db: Session = Depends(get_db),
    limit: int = 20,
):
    """Get users with similar reading tastes."""
    return user_service.get_similar_users(db, current_user.id, limit)
