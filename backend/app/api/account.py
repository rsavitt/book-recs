"""
Account management API endpoints.

Handles:
- Data export
- Account deletion
- Privacy settings
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import auth_service
from app.services.account_service import (
    export_user_data,
    delete_user_account,
    update_privacy_settings,
)

router = APIRouter()


class PrivacySettingsUpdate(BaseModel):
    is_public: bool | None = None
    allow_data_for_recs: bool | None = None


class DeleteAccountRequest(BaseModel):
    confirm_password: str


@router.get("/export")
async def export_data(
    current_user=Depends(auth_service.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Export all user data.

    Returns a JSON file containing all user data including:
    - Profile information
    - Ratings and reading history
    - Shelf/tag assignments
    """
    data = export_user_data(db, current_user.id)

    return JSONResponse(
        content=data,
        headers={
            "Content-Disposition": f'attachment; filename="{current_user.username}_data_export.json"'
        },
    )


@router.delete("/delete")
async def delete_account(
    request: DeleteAccountRequest,
    current_user=Depends(auth_service.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Permanently delete user account.

    Requires password confirmation. This action cannot be undone.
    All user data will be permanently deleted.
    """
    # Verify password
    if not auth_service.verify_password(request.confirm_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
        )

    success = delete_user_account(db, current_user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete account",
        )

    return {"message": "Account deleted successfully"}


@router.patch("/privacy")
async def update_privacy(
    settings: PrivacySettingsUpdate,
    current_user=Depends(auth_service.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update privacy settings.

    - is_public: Whether profile is visible to other users
    - allow_data_for_recs: Whether to use rating data for recommendations
    """
    success = update_privacy_settings(
        db,
        current_user.id,
        is_public=settings.is_public,
        allow_data_for_recs=settings.allow_data_for_recs,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update settings",
        )

    return {"message": "Privacy settings updated"}


@router.get("/privacy")
async def get_privacy_settings(
    current_user=Depends(auth_service.get_current_user),
):
    """Get current privacy settings."""
    return {
        "is_public": current_user.is_public,
        "allow_data_for_recs": current_user.allow_data_for_recs,
    }
