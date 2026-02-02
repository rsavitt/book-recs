"""
Admin API endpoints for managing classification and seed data.

These endpoints are for administrative use and should be protected
in production.
"""

import random
import hashlib
import gzip
import json
import tempfile
import urllib.request
import unicodedata
from pathlib import Path

from fastapi import APIRouter, Depends, BackgroundTasks, Query, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.classification import (
    reclassify_all_books,
    get_classification_stats,
)
from app.services.similarity import compute_all_similarities
from app.data.tags import TAGS
from app.data.romantasy_seed import SEED_BOOK_COUNT
from app.models.book import Book, BookTag, BookEdition
from app.models.user import User
from app.models.rating import Rating

router = APIRouter()


# ============== Bulk Upload Models ==============

class BulkBookData(BaseModel):
    title: str
    author: str
    goodreads_id: str | None = None
    isbn_13: str | None = None
    isbn_10: str | None = None
    description: str | None = None
    cover_url: str | None = None
    page_count: int | None = None
    publication_year: int | None = None
    series_name: str | None = None
    series_position: float | None = None
    is_romantasy: bool = True
    romantasy_confidence: float = 0.5
    spice_level: int | None = None
    is_ya: bool | None = None
    tags: list[str] | None = None


class BulkUserData(BaseModel):
    external_id: str  # For mapping ratings later
    username: str | None = None
    spice_preference: int | None = None


class BulkRatingData(BaseModel):
    external_user_id: str  # Maps to BulkUserData.external_id
    goodreads_book_id: str | None = None  # Maps to book by goodreads_id
    book_title: str | None = None  # Or match by title
    book_author: str | None = None  # And author
    rating: int  # 1-5


class BulkUploadResponse(BaseModel):
    status: str
    created: int
    skipped: int
    errors: list[str]


# ============== Bulk Upload Endpoints ==============

@router.post("/bulk/books", response_model=BulkUploadResponse)
async def bulk_upload_books(
    books: list[BulkBookData] = Body(...),
    db: Session = Depends(get_db),
):
    """
    Bulk upload books to the database.

    Skips books that already exist (matched by goodreads_id, isbn, or title+author).
    """
    created = 0
    skipped = 0
    errors = []

    for book_data in books:
        try:
            # Check for existing book
            existing = None

            if book_data.goodreads_id:
                existing = db.query(BookEdition).filter(
                    BookEdition.goodreads_book_id == book_data.goodreads_id
                ).first()

            if not existing and book_data.isbn_13:
                existing = db.query(Book).filter(Book.isbn_13 == book_data.isbn_13).first()

            if not existing:
                # Check by normalized title + author
                author_norm = unicodedata.normalize('NFKD', book_data.author)
                author_norm = ''.join(c for c in author_norm if not unicodedata.combining(c)).lower().strip()

                existing = db.query(Book).filter(
                    Book.title == book_data.title,
                    Book.author_normalized == author_norm
                ).first()

            if existing:
                skipped += 1
                continue

            # Create book
            author_norm = unicodedata.normalize('NFKD', book_data.author)
            author_norm = ''.join(c for c in author_norm if not unicodedata.combining(c)).lower().strip()

            book = Book(
                title=book_data.title[:500],
                author=book_data.author[:255],
                author_normalized=author_norm[:255],
                description=book_data.description[:5000] if book_data.description else None,
                cover_url=book_data.cover_url,
                page_count=book_data.page_count,
                publication_year=book_data.publication_year,
                series_name=book_data.series_name[:255] if book_data.series_name else None,
                series_position=book_data.series_position,
                is_romantasy=book_data.is_romantasy,
                romantasy_confidence=book_data.romantasy_confidence,
                spice_level=book_data.spice_level,
                is_ya=book_data.is_ya,
                isbn_13=book_data.isbn_13[:13] if book_data.isbn_13 else None,
                isbn_10=book_data.isbn_10[:10] if book_data.isbn_10 else None,
            )
            db.add(book)
            db.flush()

            # Create edition with goodreads_id if provided
            if book_data.goodreads_id:
                edition = BookEdition(
                    book_id=book.id,
                    goodreads_book_id=book_data.goodreads_id,
                )
                db.add(edition)

            # Add tags
            if book_data.tags:
                for tag_name in book_data.tags:
                    slug = tag_name.lower().replace(" ", "-")
                    tag = db.query(BookTag).filter(BookTag.slug == slug).first()
                    if not tag:
                        tag = BookTag(
                            name=tag_name.replace("-", " ").title(),
                            slug=slug,
                            category="trope",
                            is_romantasy_indicator=True,
                        )
                        db.add(tag)
                        db.flush()
                    if tag not in book.tags:
                        book.tags.append(tag)

            created += 1

            # Commit in batches
            if created % 100 == 0:
                db.commit()

        except Exception as e:
            errors.append(f"Error with '{book_data.title}': {str(e)}")

    db.commit()

    return BulkUploadResponse(
        status="success",
        created=created,
        skipped=skipped,
        errors=errors[:10],  # Limit error messages
    )


@router.post("/bulk/users", response_model=BulkUploadResponse)
async def bulk_upload_users(
    users: list[BulkUserData] = Body(...),
    db: Session = Depends(get_db),
):
    """
    Bulk upload synthetic users for rating data.

    Creates users with BULK_IMPORT_NO_LOGIN password (can't log in).
    The external_id is stored in the username for later rating mapping.
    """
    created = 0
    skipped = 0
    errors = []

    for user_data in users:
        try:
            # Generate username from external_id
            user_hash = hashlib.md5(user_data.external_id.encode()).hexdigest()[:8]
            username = user_data.username or f"bulk_{user_hash}"

            # Check if exists
            existing = db.query(User).filter(User.username == username).first()
            if existing:
                skipped += 1
                continue

            user = User(
                email=f"{username}@bulk.imported",
                username=username,
                hashed_password="BULK_IMPORT_NO_LOGIN",
                display_name=f"Reader {user_hash[:4].upper()}",
                is_public=True,
                allow_data_for_recs=True,
                spice_preference=user_data.spice_preference,
            )
            db.add(user)
            created += 1

            if created % 500 == 0:
                db.commit()

        except Exception as e:
            errors.append(f"Error with user '{user_data.external_id}': {str(e)}")

    db.commit()

    return BulkUploadResponse(
        status="success",
        created=created,
        skipped=skipped,
        errors=errors[:10],
    )


@router.post("/bulk/ratings", response_model=BulkUploadResponse)
async def bulk_upload_ratings(
    ratings: list[BulkRatingData] = Body(...),
    db: Session = Depends(get_db),
):
    """
    Bulk upload ratings.

    Matches users by external_id hash and books by goodreads_id or title+author.
    """
    created = 0
    skipped = 0
    errors = []

    # Cache for lookups
    user_cache: dict[str, int] = {}
    book_cache: dict[str, int] = {}

    for rating_data in ratings:
        try:
            # Get user ID
            if rating_data.external_user_id not in user_cache:
                user_hash = hashlib.md5(rating_data.external_user_id.encode()).hexdigest()[:8]
                username = f"bulk_{user_hash}"
                user = db.query(User).filter(User.username == username).first()
                if user:
                    user_cache[rating_data.external_user_id] = user.id
                else:
                    skipped += 1
                    continue

            user_id = user_cache[rating_data.external_user_id]

            # Get book ID
            book_id = None
            cache_key = rating_data.goodreads_book_id or f"{rating_data.book_title}|{rating_data.book_author}"

            if cache_key in book_cache:
                book_id = book_cache[cache_key]
            else:
                if rating_data.goodreads_book_id:
                    edition = db.query(BookEdition).filter(
                        BookEdition.goodreads_book_id == rating_data.goodreads_book_id
                    ).first()
                    if edition:
                        book_id = edition.book_id

                if not book_id and rating_data.book_title and rating_data.book_author:
                    author_norm = unicodedata.normalize('NFKD', rating_data.book_author)
                    author_norm = ''.join(c for c in author_norm if not unicodedata.combining(c)).lower().strip()

                    book = db.query(Book).filter(
                        Book.title == rating_data.book_title,
                        Book.author_normalized == author_norm
                    ).first()
                    if book:
                        book_id = book.id

                if book_id:
                    book_cache[cache_key] = book_id

            if not book_id:
                skipped += 1
                continue

            # Check for existing rating
            existing = db.query(Rating).filter(
                Rating.user_id == user_id,
                Rating.book_id == book_id
            ).first()
            if existing:
                skipped += 1
                continue

            # Create rating
            rating = Rating(
                user_id=user_id,
                book_id=book_id,
                rating=max(1, min(5, rating_data.rating)),
                source="bulk_import",
            )
            db.add(rating)
            created += 1

            if created % 1000 == 0:
                db.commit()

        except Exception as e:
            errors.append(f"Error with rating: {str(e)}")

    db.commit()

    return BulkUploadResponse(
        status="success",
        created=created,
        skipped=skipped,
        errors=errors[:10],
    )


# ============== Stats & Classification ==============

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


# UCSD Goodreads dataset import
UCSD_URLS = {
    "romance_books": "https://datarepo.eng.ucsd.edu/mcauley_group/gdrive/goodreads/byGenre/goodreads_books_romance.json.gz",
    "romance_interactions": "https://datarepo.eng.ucsd.edu/mcauley_group/gdrive/goodreads/byGenre/goodreads_interactions_romance.json.gz",
}

ROMANTASY_AUTHORS = {
    "sarah j. maas", "jennifer l. armentrout", "rebecca yarros",
    "holly black", "carissa broadbent", "elise kova",
    "kerri maniscalco", "raven kennedy", "scarlett st. clair",
    "laura thalassa", "leigh bardugo", "kresley cole",
    "ilona andrews", "nalini singh", "grace draven",
    "ruby dixon", "jaymin eve", "leia stone", "j. bree",
    "penelope douglas", "kathryn ann kingsley", "k.m. shea",
}

ROMANTASY_KEYWORDS = [
    "fae", "faerie", "dragon", "kingdom", "throne", "crown",
    "witch", "magic", "curse", "court", "realm", "shadow",
    "vampire", "wolf", "mate", "bond", "wings", "immortal",
]


def _ucsd_normalize_author(author: str) -> str:
    normalized = unicodedata.normalize('NFKD', author)
    normalized = ''.join(c for c in normalized if not unicodedata.combining(c))
    return normalized.lower().strip()


def _is_likely_romantasy(book_data: dict) -> tuple[bool, float]:
    """Check if a book is likely romantasy."""
    title = book_data.get("title", "").lower()
    authors = book_data.get("authors", [])
    author = authors[0].get("author_id", "") if authors else ""
    author_norm = _ucsd_normalize_author(author)
    shelves = [s.get("name", "").lower() for s in book_data.get("popular_shelves", [])]

    confidence = 0.0

    # Check author
    for known in ROMANTASY_AUTHORS:
        if known in author_norm:
            confidence += 0.5
            break

    # Check shelves for romantasy indicators
    romantasy_shelves = ["romantasy", "fantasy-romance", "romantic-fantasy", "fae-romance"]
    if any(rs in shelf for shelf in shelves for rs in romantasy_shelves):
        confidence += 0.4

    # Check if both fantasy and romance
    has_fantasy = any(s in shelves for s in ["fantasy", "paranormal", "urban-fantasy"])
    has_romance = any(s in shelves for s in ["romance", "romantic", "love"])
    if has_fantasy and has_romance:
        confidence += 0.3

    # Check title keywords
    keyword_count = sum(1 for kw in ROMANTASY_KEYWORDS if kw in title)
    confidence += min(0.2, keyword_count * 0.05)

    return confidence >= 0.3, min(1.0, confidence)


def _get_or_create_tag(db: Session, tag_name: str, category: str = "trope") -> BookTag:
    slug = tag_name.lower().replace(" ", "-")
    tag = db.query(BookTag).filter(BookTag.slug == slug).first()
    if not tag:
        tag = BookTag(
            name=tag_name.replace("-", " ").title(),
            slug=slug,
            category=category,
            is_romantasy_indicator=True
        )
        db.add(tag)
        db.flush()
    return tag


def _import_ucsd_books(db: Session, book_limit: int = 2000) -> dict[str, int]:
    """Download and import books from UCSD dataset."""
    import logging
    logger = logging.getLogger(__name__)

    book_id_map = {}
    books_processed = 0
    romantasy_count = 0

    url = UCSD_URLS["romance_books"]
    logger.info(f"Downloading {url}...")

    try:
        with tempfile.NamedTemporaryFile(suffix='.json.gz', delete=False) as tmp:
            urllib.request.urlretrieve(url, tmp.name)
            tmp_path = tmp.name

        logger.info("Processing books...")
        with gzip.open(tmp_path, 'rt', encoding='utf-8') as f:
            for line in f:
                if romantasy_count >= book_limit:
                    break

                books_processed += 1
                if books_processed % 5000 == 0:
                    logger.info(f"Processed {books_processed}, found {romantasy_count} romantasy")

                try:
                    book_data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                is_romantasy, confidence = _is_likely_romantasy(book_data)
                if not is_romantasy:
                    continue

                goodreads_id = book_data.get("book_id")
                if not goodreads_id or goodreads_id in book_id_map:
                    continue

                # Check if already exists
                existing = db.query(BookEdition).filter(
                    BookEdition.goodreads_book_id == goodreads_id
                ).first()
                if existing:
                    book_id_map[goodreads_id] = existing.book_id
                    continue

                title = book_data.get("title", "Unknown")[:500]
                authors = book_data.get("authors", [])
                author = authors[0].get("author_id", "Unknown") if authors else "Unknown"

                book = Book(
                    title=title,
                    author=author[:255],
                    author_normalized=_ucsd_normalize_author(author)[:255],
                    description=(book_data.get("description") or "")[:5000] or None,
                    cover_url=book_data.get("image_url"),
                    page_count=int(book_data["num_pages"]) if book_data.get("num_pages") else None,
                    publication_year=int(book_data["publication_year"]) if book_data.get("publication_year") else None,
                    is_romantasy=True,
                    romantasy_confidence=confidence,
                    isbn_13=book_data.get("isbn13", "")[:13] or None,
                    isbn_10=book_data.get("isbn", "")[:10] or None,
                )
                db.add(book)
                db.flush()

                # Link goodreads ID
                edition = BookEdition(
                    book_id=book.id,
                    goodreads_book_id=goodreads_id,
                )
                db.add(edition)

                book_id_map[goodreads_id] = book.id
                romantasy_count += 1

                if romantasy_count % 200 == 0:
                    db.commit()

        db.commit()
        Path(tmp_path).unlink(missing_ok=True)

    except Exception as e:
        logger.error(f"Error importing books: {e}")
        raise

    return book_id_map


def _import_ucsd_ratings(db: Session, book_id_map: dict[str, int], max_users: int = 5000):
    """Import ratings for imported books."""
    import logging
    logger = logging.getLogger(__name__)

    user_id_map = {}
    user_count = 0
    rating_count = 0

    url = UCSD_URLS["romance_interactions"]
    logger.info(f"Downloading {url}...")

    try:
        with tempfile.NamedTemporaryFile(suffix='.json.gz', delete=False) as tmp:
            urllib.request.urlretrieve(url, tmp.name)
            tmp_path = tmp.name

        logger.info("Processing interactions...")
        with gzip.open(tmp_path, 'rt', encoding='utf-8') as f:
            for line in f:
                try:
                    interaction = json.loads(line)
                except json.JSONDecodeError:
                    continue

                book_id = interaction.get("book_id")
                user_id = interaction.get("user_id")
                rating = interaction.get("rating")

                if book_id not in book_id_map or not rating or rating < 1:
                    continue

                our_book_id = book_id_map[book_id]

                if user_id not in user_id_map:
                    if user_count >= max_users:
                        continue

                    user_hash = hashlib.md5(user_id.encode()).hexdigest()[:8]
                    username = f"gr_{user_hash}"

                    existing = db.query(User).filter(User.username == username).first()
                    if existing:
                        user_id_map[user_id] = existing.id
                        continue

                    user = User(
                        email=f"{username}@goodreads.imported",
                        username=username,
                        hashed_password="IMPORTED_NO_LOGIN",
                        display_name=f"Reader {user_hash[:4].upper()}",
                        is_public=True,
                        allow_data_for_recs=True,
                    )
                    db.add(user)
                    db.flush()
                    user_id_map[user_id] = user.id
                    user_count += 1

                our_user_id = user_id_map[user_id]

                # Check for existing rating
                existing_rating = db.query(Rating).filter(
                    Rating.user_id == our_user_id,
                    Rating.book_id == our_book_id
                ).first()
                if existing_rating:
                    continue

                rating_obj = Rating(
                    user_id=our_user_id,
                    book_id=our_book_id,
                    rating=min(5, max(1, int(rating))),
                    source="ucsd_goodreads"
                )
                db.add(rating_obj)
                rating_count += 1

                if rating_count % 2000 == 0:
                    db.commit()
                    logger.info(f"Imported {rating_count} ratings from {user_count} users")

        db.commit()
        Path(tmp_path).unlink(missing_ok=True)

    except Exception as e:
        logger.error(f"Error importing ratings: {e}")
        raise

    return rating_count, user_count


def _run_ucsd_import(db: Session, book_limit: int, max_users: int):
    """Background task to run the full UCSD import."""
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    logger.info(f"Starting UCSD import: book_limit={book_limit}, max_users={max_users}")

    try:
        book_id_map = _import_ucsd_books(db, book_limit)
        logger.info(f"Imported {len(book_id_map)} books")

        if book_id_map:
            rating_count, user_count = _import_ucsd_ratings(db, book_id_map, max_users)
            logger.info(f"Imported {rating_count} ratings from {user_count} users")

        logger.info("UCSD import complete!")
    except Exception as e:
        logger.error(f"UCSD import failed: {e}")
        db.rollback()


@router.post("/import-ucsd-dataset")
async def import_ucsd_dataset(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    book_limit: int = Query(2000, le=10000, description="Max romantasy books to import"),
    max_users: int = Query(5000, le=20000, description="Max users to create"),
):
    """
    Import books and ratings from the UCSD Goodreads dataset.

    Downloads the romance genre subset and filters for romantasy books.
    This runs in the background as it can take several minutes.

    The dataset is from: https://mengtingwan.github.io/data/goodreads.html
    """
    background_tasks.add_task(_run_ucsd_import, db, book_limit, max_users)

    return {
        "status": "started",
        "message": f"Importing up to {book_limit} books and {max_users} users in background",
        "dataset": "UCSD Goodreads Romance Genre",
        "note": "Check /admin/stats periodically to see progress",
    }
