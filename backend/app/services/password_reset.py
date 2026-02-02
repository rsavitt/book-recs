"""
Password reset service.

Handles password reset token generation, validation, and password updates.
Uses JWT tokens for secure, time-limited reset links.
"""

import secrets
from datetime import datetime, timedelta

from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.user import User
from app.services.auth_service import get_password_hash, get_user_by_email

settings = get_settings()

# Reset tokens expire after 1 hour
RESET_TOKEN_EXPIRE_HOURS = 1


def create_password_reset_token(email: str) -> str:
    """
    Create a password reset token for the given email.

    Args:
        email: User's email address

    Returns:
        JWT token for password reset
    """
    expire = datetime.utcnow() + timedelta(hours=RESET_TOKEN_EXPIRE_HOURS)
    to_encode = {
        "sub": email,
        "exp": expire,
        "type": "password_reset",
        "jti": secrets.token_hex(16),  # Unique token ID
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_password_reset_token(token: str) -> str | None:
    """
    Verify a password reset token and return the email.

    Args:
        token: JWT reset token

    Returns:
        Email address if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        # Verify it's a password reset token
        if payload.get("type") != "password_reset":
            return None

        email: str = payload.get("sub")
        return email

    except JWTError:
        return None


def reset_password(db: Session, token: str, new_password: str) -> bool:
    """
    Reset a user's password using a valid reset token.

    Args:
        db: Database session
        token: Password reset token
        new_password: New password to set

    Returns:
        True if successful, False otherwise
    """
    email = verify_password_reset_token(token)
    if not email:
        return False

    user = get_user_by_email(db, email)
    if not user:
        return False

    # Update password
    user.hashed_password = get_password_hash(new_password)
    user.updated_at = datetime.utcnow()
    db.commit()

    return True


def request_password_reset(db: Session, email: str) -> str | None:
    """
    Request a password reset for the given email.

    In production, this would send an email with the reset link.
    For now, it just returns the token (for testing).

    Args:
        db: Database session
        email: Email address to reset

    Returns:
        Reset token if user exists, None otherwise
    """
    user = get_user_by_email(db, email)
    if not user:
        # Don't reveal whether email exists
        # In production, always return success message
        return None

    token = create_password_reset_token(email)

    # TODO: Send email with reset link
    # reset_link = f"{settings.frontend_url}/reset-password?token={token}"
    # send_email(email, "Password Reset", f"Click here to reset: {reset_link}")

    return token
