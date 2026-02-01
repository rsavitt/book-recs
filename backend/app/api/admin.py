"""
Admin API endpoints for managing classification and seed data.

These endpoints are for administrative use and should be protected
in production.
"""

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.classification import (
    reclassify_all_books,
    get_classification_stats,
)
from app.services.similarity import compute_all_similarities
from app.data.tags import TAGS
from app.data.romantasy_seed import SEED_BOOK_COUNT

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
