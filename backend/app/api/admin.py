"""
Admin API endpoints for managing classification and seed data.

These endpoints are for administrative use and should be protected
in production.
"""

import random
import hashlib

from fastapi import APIRouter, Depends, BackgroundTasks, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.classification import (
    reclassify_all_books,
    get_classification_stats,
)
from app.services.similarity import compute_all_similarities
from app.data.tags import TAGS
from app.data.romantasy_seed import SEED_BOOK_COUNT
from app.models.book import Book
from app.models.user import User
from app.models.rating import Rating

router = APIRouter()


@router.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    """
    Get classification and database statistics.

    Returns counts of books, Romantasy classifications, tags, etc.
    """
    classification_stats = get_classification_stats(db)

    return {
        "classification": classification_stats,
        "seed_data": {
            "tag_definitions": len(TAGS),
            "seed_books": SEED_BOOK_COUNT,
        },
    }


@router.post("/reclassify")
async def trigger_reclassification(
    background_tasks: BackgroundTasks,
    min_confidence: float = 0.6,
    db: Session = Depends(get_db),
):
    """
    Trigger reclassification of all books.

    This re-analyzes shelf signals from all users to update
    Romantasy classifications. Should be run periodically as
    more users import their libraries.

    Args:
        min_confidence: Minimum confidence to classify as Romantasy (0.0-1.0)
    """
    # Run in background since this can take a while
    background_tasks.add_task(reclassify_all_books, db, min_confidence)

    return {
        "status": "started",
        "message": "Reclassification started in background",
    }


@router.get("/tags")
async def list_all_tags():
    """
    List all tag definitions.

    Returns the full tag catalog with metadata.
    """
    return {
        "total": len(TAGS),
        "tags": TAGS,
    }


@router.get("/tags/by-category")
async def list_tags_by_category():
    """
    List tags grouped by category.
    """
    by_category = {}

    for tag in TAGS:
        category = tag["category"]
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(tag)

    return by_category


@router.get("/romantasy-indicators")
async def list_romantasy_indicators():
    """
    List tags that are strong Romantasy indicators.

    These are the tags that, when present in user shelves,
    strongly suggest a book is Romantasy.
    """
    indicators = [tag for tag in TAGS if tag.get("is_romantasy_indicator", False)]

    return {
        "total": len(indicators),
        "indicators": indicators,
    }


@router.post("/compute-similarities")
async def trigger_similarity_computation(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Trigger batch computation of user similarities.

    This computes Pearson correlation between all users based on
    their book ratings. Should be run periodically (e.g., nightly)
    as users import their libraries.
    """
    background_tasks.add_task(compute_all_similarities, db)

    return {
        "status": "started",
        "message": "Similarity computation started in background",
    }


# Reader personas for generating realistic rating patterns
READER_PERSONAS = [
    {
        "name": "acotar_fan",
        "loves": ["sarah j. maas", "jennifer l. armentrout", "carissa broadbent"],
        "tropes": ["fae", "enemies-to-lovers", "morally-gray"],
        "spice_pref": (3, 5),
        "count": 30,
    },
    {
        "name": "fourth_wing_fan",
        "loves": ["rebecca yarros", "elise kova", "holly black"],
        "tropes": ["dragon", "academy", "enemies-to-lovers"],
        "spice_pref": (3, 5),
        "count": 25,
    },
    {
        "name": "ya_fantasy_fan",
        "loves": ["leigh bardugo", "holly black", "brigid kemmerer"],
        "tropes": ["found-family", "slow-burn"],
        "spice_pref": (0, 2),
        "count": 20,
    },
    {
        "name": "dark_romance_fan",
        "loves": ["scarlett st. clair", "raven kennedy", "kathryn ann kingsley"],
        "tropes": ["dark-romance", "morally-gray", "fated-mates"],
        "spice_pref": (4, 5),
        "count": 20,
    },
    {
        "name": "cozy_romantasy_fan",
        "loves": ["k.m. shea", "elise kova"],
        "tropes": ["slow-burn", "found-family"],
        "spice_pref": (1, 3),
        "count": 15,
    },
    {
        "name": "shifter_fan",
        "loves": ["ruby dixon", "jaymin eve", "leia stone"],
        "tropes": ["shifter", "fated-mates"],
        "spice_pref": (3, 5),
        "count": 15,
    },
    {
        "name": "eclectic_reader",
        "loves": [],
        "tropes": [],
        "spice_pref": (0, 5),
        "count": 25,
    },
]


def _normalize_author(author: str) -> str:
    import unicodedata
    normalized = unicodedata.normalize('NFKD', author)
    normalized = ''.join(c for c in normalized if not unicodedata.combining(c))
    return normalized.lower().strip()


def _calculate_rating(book: Book, persona: dict) -> int:
    """Calculate a rating for a book based on persona preferences."""
    base_rating = 3.5
    author_norm = _normalize_author(book.author)

    # Author match bonus
    for loved_author in persona["loves"]:
        if loved_author in author_norm:
            base_rating += 1.5
            break

    # Trope match bonus
    book_tropes = [t.slug for t in book.tags] if book.tags else []
    matching_tropes = sum(1 for t in persona["tropes"] if t in book_tropes)
    base_rating += matching_tropes * 0.3

    # Spice preference
    if book.spice_level is not None:
        min_spice, max_spice = persona["spice_pref"]
        if book.spice_level < min_spice or book.spice_level > max_spice:
            base_rating -= 0.5

    # Add randomness
    base_rating += random.gauss(0, 0.7)
    rating = max(1, min(5, round(base_rating)))

    # 30% chance to skip
    if random.random() < 0.3:
        return 0

    return rating


@router.post("/generate-sample-ratings")
async def generate_sample_ratings(
    db: Session = Depends(get_db),
    clear_existing: bool = Query(False, description="Clear existing synthetic data first"),
):
    """
    Generate synthetic user ratings for testing recommendations.

    Creates users with different reading preferences (ACOTAR fans,
    Fourth Wing fans, YA readers, etc.) and generates realistic ratings.
    """
    if clear_existing:
        # Delete synthetic users and their ratings
        synthetic_users = db.query(User).filter(
            User.hashed_password == "SYNTHETIC_NO_LOGIN"
        ).all()
        for user in synthetic_users:
            db.query(Rating).filter(Rating.user_id == user.id).delete()
            db.delete(user)
        db.commit()

    # Get all books
    books = db.query(Book).all()
    if not books:
        return {"error": "No books found. Run seed first."}

    user_count = 0
    rating_count = 0

    for persona in READER_PERSONAS:
        for i in range(persona["count"]):
            user_hash = hashlib.md5(
                f"{persona['name']}_{i}_{random.random()}".encode()
            ).hexdigest()[:8]
            username = f"{persona['name'][:10]}_{user_hash}"

            if db.query(User).filter(User.username == username).first():
                continue

            user = User(
                email=f"{username}@synthetic.local",
                username=username,
                hashed_password="SYNTHETIC_NO_LOGIN",
                display_name=f"{persona['name'].replace('_', ' ').title()} #{i+1}",
                is_public=True,
                allow_data_for_recs=True,
                spice_preference=random.randint(*persona["spice_pref"]),
            )
            db.add(user)
            db.flush()
            user_count += 1

            # Rate books
            books_to_rate = random.sample(books, min(len(books), random.randint(8, 25)))
            for book in books_to_rate:
                rating_value = _calculate_rating(book, persona)
                if rating_value == 0:
                    continue

                rating = Rating(
                    user_id=user.id,
                    book_id=book.id,
                    rating=rating_value,
                    source="synthetic"
                )
                db.add(rating)
                rating_count += 1

        db.commit()

    return {
        "status": "success",
        "users_created": user_count,
        "ratings_created": rating_count,
        "total_users": db.query(User).count(),
        "total_ratings": db.query(Rating).count(),
    }
