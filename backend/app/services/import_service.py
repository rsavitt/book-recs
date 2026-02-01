"""
Goodreads CSV import service.

Handles the full import pipeline:
1. Validate and parse CSV
2. Deduplicate books
3. Enrich metadata
4. Create ratings and shelves
5. Trigger similarity recomputation
"""

import asyncio
import re
import uuid
from datetime import datetime
from typing import Callable

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.book import Book
from app.models.rating import Rating, Shelf
from app.models.user import User
from app.schemas.imports import ImportStatus, ImportResult
from app.services.csv_parser import GoodreadsCSVParser, ParsedBook
from app.services.book_dedup import BookDeduplicator, DeduplicationResult
from app.services.external_apis import MetadataEnricher


# In-memory store for import status (replace with Redis/DB in production)
_import_status: dict[str, dict] = {}


def validate_and_create_import(db: Session, user_id: int, content: bytes) -> str:
    """
    Validate the uploaded file is a Goodreads export and create an import job.

    Returns the import_id for tracking.
    """
    parser = GoodreadsCSVParser(content)

    if not parser.validate():
        raise ValueError("; ".join(parser.errors))

    # Count books for progress tracking
    books = list(parser.parse())
    total_books = len(books)

    if total_books == 0:
        raise ValueError("No valid books found in the CSV file")

    # Create import job
    import_id = str(uuid.uuid4())
    _import_status[import_id] = {
        "import_id": import_id,
        "user_id": user_id,
        "status": "pending",
        "message": "Validating file...",
        "progress": 0,
        "books_processed": 0,
        "books_total": total_books,
        "books_imported": 0,
        "books_skipped": 0,
        "new_books_added": 0,
        "errors": [],
        "started_at": datetime.utcnow(),
    }

    return import_id


def process_import(import_id: str, user_id: int, content: bytes) -> None:
    """
    Process the Goodreads CSV import.

    This runs as a background task.
    """
    # Update status
    _import_status[import_id]["status"] = "processing"
    _import_status[import_id]["message"] = "Parsing CSV..."

    # Parse CSV
    parser = GoodreadsCSVParser(content)
    if not parser.validate():
        _import_status[import_id]["status"] = "failed"
        _import_status[import_id]["errors"] = parser.errors
        return

    books = list(parser.parse())
    _import_status[import_id]["warnings"] = parser.warnings

    # Process books
    db = SessionLocal()
    try:
        _process_books(db, import_id, user_id, books)

        # Update user's last import time
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.last_import_at = datetime.utcnow()
            db.commit()

        _import_status[import_id]["status"] = "completed"
        _import_status[import_id]["message"] = "Import complete"
        _import_status[import_id]["completed_at"] = datetime.utcnow()

    except Exception as e:
        db.rollback()
        _import_status[import_id]["status"] = "failed"
        _import_status[import_id]["errors"].append(f"Import failed: {str(e)}")

    finally:
        db.close()


def _process_books(
    db: Session,
    import_id: str,
    user_id: int,
    books: list[ParsedBook],
) -> None:
    """Process all books from the import."""
    deduplicator = BookDeduplicator(db)
    total = len(books)

    for i, parsed in enumerate(books):
        try:
            _process_single_book(db, deduplicator, user_id, parsed, import_id)

            # Update progress
            _import_status[import_id]["books_processed"] = i + 1
            _import_status[import_id]["progress"] = int((i + 1) / total * 100)

            # Commit in batches
            if (i + 1) % 50 == 0:
                db.commit()
                _import_status[import_id]["message"] = f"Processing books ({i + 1}/{total})..."

        except Exception as e:
            _import_status[import_id]["errors"].append(
                f"Book '{parsed.title}': {str(e)}"
            )
            _import_status[import_id]["books_skipped"] += 1

    # Final commit
    db.commit()


def _process_single_book(
    db: Session,
    deduplicator: BookDeduplicator,
    user_id: int,
    parsed: ParsedBook,
    import_id: str,
) -> None:
    """Process a single book from the import."""
    # Deduplicate and get/create book record
    result = deduplicator.find_or_create(parsed)

    if result.is_new_book:
        _import_status[import_id]["new_books_added"] += 1

    # Create or update rating (only if rated)
    if parsed.rating > 0:
        _create_or_update_rating(db, user_id, result.book.id, parsed)
        _import_status[import_id]["books_imported"] += 1
    elif parsed.exclusive_shelf in ("read", "currently-reading", "to-read"):
        # Track unrated but shelved books
        _create_or_update_rating(db, user_id, result.book.id, parsed)
        _import_status[import_id]["books_imported"] += 1
    else:
        _import_status[import_id]["books_skipped"] += 1

    # Create shelf records
    _create_shelves(db, user_id, result.book.id, parsed)


def _create_or_update_rating(
    db: Session,
    user_id: int,
    book_id: int,
    parsed: ParsedBook,
) -> Rating:
    """Create or update a rating record."""
    # Check for existing rating
    existing = (
        db.query(Rating)
        .filter(Rating.user_id == user_id, Rating.book_id == book_id)
        .first()
    )

    if existing:
        # Update if the imported rating is newer or has more data
        if parsed.rating > 0 and (existing.rating == 0 or parsed.date_read):
            existing.rating = parsed.rating
            existing.date_read = parsed.date_read or existing.date_read
            existing.date_added = parsed.date_added or existing.date_added
            existing.updated_at = datetime.utcnow()
        return existing

    # Create new rating
    rating = Rating(
        user_id=user_id,
        book_id=book_id,
        rating=parsed.rating,
        date_read=parsed.date_read,
        date_added=parsed.date_added,
        source="goodreads_import",
    )
    db.add(rating)
    return rating


def _create_shelves(
    db: Session,
    user_id: int,
    book_id: int,
    parsed: ParsedBook,
) -> list[Shelf]:
    """Create shelf records for a book."""
    shelves = []

    # Combine explicit shelves with exclusive shelf
    all_shelves = set(parsed.shelves)
    if parsed.exclusive_shelf:
        all_shelves.add(parsed.exclusive_shelf)

    for shelf_name in all_shelves:
        # Check if shelf already exists
        existing = (
            db.query(Shelf)
            .filter(
                Shelf.user_id == user_id,
                Shelf.book_id == book_id,
                Shelf.shelf_name == shelf_name,
            )
            .first()
        )

        if existing:
            shelves.append(existing)
            continue

        # Create new shelf
        shelf = Shelf(
            user_id=user_id,
            book_id=book_id,
            shelf_name=shelf_name,
            shelf_name_normalized=_normalize_shelf_name(shelf_name),
        )
        db.add(shelf)
        shelves.append(shelf)

    return shelves


def _normalize_shelf_name(name: str) -> str:
    """Normalize shelf name for matching."""
    # Lowercase
    name = name.lower()
    # Remove special characters, keep alphanumeric and hyphens
    name = re.sub(r"[^a-z0-9-]", "-", name)
    # Collapse multiple hyphens
    name = re.sub(r"-+", "-", name)
    # Remove leading/trailing hyphens
    name = name.strip("-")
    return name


def get_import_status(db: Session, import_id: str, user_id: int) -> ImportStatus | None:
    """Get the status of an import job."""
    status = _import_status.get(import_id)
    if not status or status["user_id"] != user_id:
        return None

    return ImportStatus(
        import_id=status["import_id"],
        status=status["status"],
        message=status.get("message"),
        progress=status.get("progress"),
        books_processed=status.get("books_processed"),
        books_total=status.get("books_total"),
        errors=status.get("errors") if status.get("errors") else None,
    )


def get_import_history(db: Session, user_id: int, limit: int = 10) -> list[ImportResult]:
    """Get user's import history."""
    results = []
    for import_id, status in _import_status.items():
        if status["user_id"] == user_id and status["status"] in ("completed", "failed"):
            results.append(
                ImportResult(
                    import_id=status["import_id"],
                    status=status["status"],
                    started_at=status["started_at"],
                    completed_at=status.get("completed_at"),
                    books_imported=status.get("books_imported", 0),
                    books_skipped=status.get("books_skipped", 0),
                    new_books_added=status.get("new_books_added", 0),
                    errors=status.get("errors", []),
                )
            )

    # Sort by started_at descending
    results.sort(key=lambda x: x.started_at, reverse=True)
    return results[:limit]


async def enrich_book_metadata_async(book_id: int) -> None:
    """
    Enrich a book's metadata from external APIs.

    This runs as a background task after import.
    """
    db = SessionLocal()
    try:
        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            return

        # Skip if already enriched
        if book.description and book.cover_url:
            return

        enricher = MetadataEnricher()
        try:
            # Try ISBN first
            metadata = None
            if book.isbn_13:
                metadata = await enricher.enrich_by_isbn(book.isbn_13)
            elif book.isbn_10:
                metadata = await enricher.enrich_by_isbn(book.isbn_10)

            # Fallback to title/author search
            if not metadata:
                metadata = await enricher.enrich_by_title_author(book.title, book.author)

            if metadata:
                # Update book with enriched metadata
                if not book.description and metadata.description:
                    book.description = metadata.description
                if not book.cover_url and metadata.cover_url:
                    book.cover_url = metadata.cover_url
                if not book.page_count and metadata.page_count:
                    book.page_count = metadata.page_count
                if not book.open_library_id and metadata.open_library_id:
                    book.open_library_id = metadata.open_library_id
                if not book.google_books_id and metadata.google_books_id:
                    book.google_books_id = metadata.google_books_id

                db.commit()

        finally:
            await enricher.close()

    finally:
        db.close()
