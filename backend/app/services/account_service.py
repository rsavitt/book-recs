"""
Account management service.

Handles:
- Account deletion (GDPR compliance)
- Data export
- Privacy settings
"""

import json
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.user import User
from app.models.book import Book
from app.models.rating import Rating, Shelf
from app.models.similarity import UserSimilarity


def export_user_data(db: Session, user_id: int) -> dict[str, Any]:
    """
    Export all user data in a portable format.

    This provides GDPR-compliant data portability.

    Args:
        db: Database session
        user_id: User ID to export

    Returns:
        Dict containing all user data
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {}

    # Get user's ratings with book info
    ratings = (
        db.query(Rating, Book)
        .join(Book, Book.id == Rating.book_id)
        .filter(Rating.user_id == user_id)
        .all()
    )

    # Get user's shelves
    shelves = (
        db.query(Shelf, Book)
        .join(Book, Book.id == Shelf.book_id)
        .filter(Shelf.user_id == user_id)
        .all()
    )

    # Build export
    export = {
        "export_date": datetime.utcnow().isoformat(),
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "display_name": user.display_name,
            "bio": user.bio,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "preferences": {
                "spice_preference": user.spice_preference,
                "prefers_ya": user.prefers_ya,
                "is_public": user.is_public,
                "allow_data_for_recs": user.allow_data_for_recs,
            },
        },
        "ratings": [
            {
                "book_title": book.title,
                "book_author": book.author,
                "isbn13": book.isbn_13,
                "rating": rating.rating,
                "date_read": rating.date_read.isoformat() if rating.date_read else None,
                "date_added": rating.date_added.isoformat() if rating.date_added else None,
                "source": rating.source,
            }
            for rating, book in ratings
        ],
        "shelves": [
            {
                "book_title": book.title,
                "book_author": book.author,
                "shelf_name": shelf.shelf_name,
            }
            for shelf, book in shelves
        ],
    }

    return export


def delete_user_account(db: Session, user_id: int) -> bool:
    """
    Permanently delete a user account and all associated data.

    This is GDPR-compliant account deletion ("right to be forgotten").

    Args:
        db: Database session
        user_id: User ID to delete

    Returns:
        True if successful, False if user not found
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False

    # Delete in order to respect foreign key constraints

    # 1. Delete user similarities (both directions)
    db.query(UserSimilarity).filter(
        (UserSimilarity.user_id == user_id) | (UserSimilarity.neighbor_id == user_id)
    ).delete(synchronize_session=False)

    # 2. Delete shelves
    db.query(Shelf).filter(Shelf.user_id == user_id).delete(synchronize_session=False)

    # 3. Delete ratings
    db.query(Rating).filter(Rating.user_id == user_id).delete(synchronize_session=False)

    # 4. Delete user
    db.delete(user)

    db.commit()
    return True


def anonymize_user_data(db: Session, user_id: int) -> bool:
    """
    Anonymize user data instead of deleting.

    This keeps the ratings for recommendation quality but removes
    personally identifiable information.

    Args:
        db: Database session
        user_id: User ID to anonymize

    Returns:
        True if successful
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False

    # Anonymize user info
    anonymous_id = f"anonymous_{user_id}"
    user.email = f"{anonymous_id}@deleted.local"
    user.username = anonymous_id
    user.display_name = "Deleted User"
    user.bio = None
    user.hashed_password = "DELETED"
    user.is_public = False
    user.allow_data_for_recs = False  # Stop using their data

    # Delete shelves (contain user-specific tags)
    db.query(Shelf).filter(Shelf.user_id == user_id).delete(synchronize_session=False)

    # Delete similarities
    db.query(UserSimilarity).filter(
        (UserSimilarity.user_id == user_id) | (UserSimilarity.neighbor_id == user_id)
    ).delete(synchronize_session=False)

    db.commit()
    return True


def update_privacy_settings(
    db: Session,
    user_id: int,
    is_public: bool | None = None,
    allow_data_for_recs: bool | None = None,
) -> bool:
    """
    Update user privacy settings.

    Args:
        db: Database session
        user_id: User ID
        is_public: Whether profile is public
        allow_data_for_recs: Whether to use data for recommendations

    Returns:
        True if successful
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False

    if is_public is not None:
        user.is_public = is_public

    if allow_data_for_recs is not None:
        user.allow_data_for_recs = allow_data_for_recs

        # If opting out, delete their similarities
        if not allow_data_for_recs:
            db.query(UserSimilarity).filter(
                (UserSimilarity.user_id == user_id) | (UserSimilarity.neighbor_id == user_id)
            ).delete(synchronize_session=False)

    db.commit()
    return True
