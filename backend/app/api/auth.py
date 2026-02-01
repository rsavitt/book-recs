from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.auth import Token, UserCreate, UserResponse
from app.services import auth_service
from app.services.password_reset import (
    request_password_reset,
    reset_password,
    verify_password_reset_token,
)

router = APIRouter()


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    existing_user = auth_service.get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    existing_username = auth_service.get_user_by_username(db, user_data.username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    user = auth_service.create_user(db, user_data)
    return user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Authenticate user and return JWT token."""
    user = auth_service.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = auth_service.create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user=Depends(auth_service.get_current_user),
):
    """Get current authenticated user info."""
    return current_user


@router.post("/forgot-password")
async def forgot_password(
    request: PasswordResetRequest,
    db: Session = Depends(get_db),
):
    """
    Request a password reset email.

    Always returns success to prevent email enumeration.
    """
    token = request_password_reset(db, request.email)

    # In production, send email here
    # For development, we return the token (remove in production!)
    return {
        "message": "If an account exists with this email, a reset link has been sent.",
        # Remove this in production:
        "_debug_token": token,
    }


@router.post("/reset-password")
async def reset_password_endpoint(
    request: PasswordResetConfirm,
    db: Session = Depends(get_db),
):
    """
    Reset password using a valid reset token.
    """
    success = reset_password(db, request.token, request.new_password)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    return {"message": "Password has been reset successfully"}


@router.get("/verify-reset-token")
async def verify_reset_token(token: str):
    """
    Verify if a password reset token is valid.

    Used by frontend to check token before showing reset form.
    """
    email = verify_password_reset_token(token)

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    return {"valid": True, "email": email}
