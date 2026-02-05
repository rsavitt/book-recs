"""
Database seeding script.

Populates the database with:
1. Tag/trope definitions
2. Romantasy seed books with metadata

Run with: python -m app.scripts.seed_database
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.orm import Session

from app.core.database import Base, SessionLocal, engine
from app.data.romantasy_seed import ROMANTASY_SEED_BOOKS
from app.data.tags import TAGS
from app.models.book import Book, BookTag


def create_tables():
    """Create all database tables."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created.")


def seed_tags(db: Session) -> dict[str, BookTag]:
    """
    Seed the book_tags table with predefined tags.

    Returns:
        Dict mapping tag slugs to BookTag objects
    """
    print(f"Seeding {len(TAGS)} tags...")

    tag_map = {}

    for tag_data in TAGS:
        # Check if tag already exists
        existing = db.query(BookTag).filter(BookTag.slug == tag_data["slug"]).first()

        if existing:
            tag_map[tag_data["slug"]] = existing
            continue

        tag = BookTag(
            name=tag_data["name"],
            slug=tag_data["slug"],
            category=tag_data["category"],
            description=tag_data.get("description"),
            is_romantasy_indicator=tag_data.get("is_romantasy_indicator", False),
        )
        db.add(tag)
        tag_map[tag_data["slug"]] = tag

    db.commit()
    print(f"Tags seeded. Total: {len(tag_map)}")

    return tag_map


def seed_romantasy_books(db: Session, tag_map: dict[str, BookTag]) -> int:
    """
    Seed the books table with Romantasy seed list.

    Args:
        db: Database session
        tag_map: Dict mapping tag slugs to BookTag objects

    Returns:
        Number of books added
    """
    print(f"Seeding {len(ROMANTASY_SEED_BOOKS)} Romantasy books...")

    added = 0
    updated = 0

    for book_data in ROMANTASY_SEED_BOOKS:
        # Check if book already exists (by ISBN or title+author)
        existing = None

        if book_data.get("isbn13"):
            existing = db.query(Book).filter(Book.isbn_13 == book_data["isbn13"]).first()

        if not existing:
            existing = (
                db.query(Book)
                .filter(
                    Book.title == book_data["title"],
                    Book.author == book_data["author"],
                )
                .first()
            )

        if existing:
            # Update existing book with seed data
            existing.is_romantasy = True
            existing.romantasy_confidence = 1.0  # Seed list = 100% confidence
            existing.spice_level = book_data.get("spice_level")
            existing.is_ya = book_data.get("is_ya")
            existing.series_name = book_data.get("series_name")
            existing.series_position = book_data.get("series_position")

            # Add tags
            _add_tags_to_book(existing, book_data.get("tags", []), tag_map)

            updated += 1
            continue

        # Create new book
        book = Book(
            title=book_data["title"],
            author=book_data["author"],
            author_normalized=book_data["author"].lower().replace(".", "").strip(),
            isbn_13=book_data.get("isbn13"),
            publication_year=book_data.get("publication_year"),
            series_name=book_data.get("series_name"),
            series_position=book_data.get("series_position"),
            is_romantasy=True,
            romantasy_confidence=1.0,  # Seed list = 100% confidence
            spice_level=book_data.get("spice_level"),
            is_ya=book_data.get("is_ya"),
        )

        # Add tags
        _add_tags_to_book(book, book_data.get("tags", []), tag_map)

        db.add(book)
        added += 1

    db.commit()
    print(f"Books seeded. Added: {added}, Updated: {updated}")

    return added


def _add_tags_to_book(book: Book, tag_slugs: list[str], tag_map: dict[str, BookTag]):
    """Add tags to a book."""
    existing_slugs = {tag.slug for tag in book.tags}

    for slug in tag_slugs:
        if slug in existing_slugs:
            continue

        tag = tag_map.get(slug)
        if tag:
            book.tags.append(tag)


def print_stats(db: Session):
    """Print database statistics after seeding."""
    book_count = db.query(Book).count()
    romantasy_count = db.query(Book).filter(Book.is_romantasy).count()
    tag_count = db.query(BookTag).count()

    print("\n=== Database Statistics ===")
    print(f"Total books: {book_count}")
    print(f"Romantasy books: {romantasy_count}")
    print(f"Tags defined: {tag_count}")

    # Tag category breakdown
    print("\nTags by category:")
    from sqlalchemy import func

    categories = db.query(BookTag.category, func.count(BookTag.id)).group_by(BookTag.category).all()
    for category, count in categories:
        print(f"  {category}: {count}")

    # Spice level breakdown
    print("\nRomantasy books by spice level:")
    spice_levels = (
        db.query(Book.spice_level, func.count(Book.id))
        .filter(Book.is_romantasy)
        .group_by(Book.spice_level)
        .order_by(Book.spice_level)
        .all()
    )
    for level, count in spice_levels:
        level_str = str(level) if level is not None else "Unknown"
        print(f"  Level {level_str}: {count}")

    # YA vs Adult breakdown
    print("\nRomantasy books by age category:")
    ya_count = db.query(Book).filter(Book.is_romantasy, Book.is_ya).count()
    adult_count = db.query(Book).filter(Book.is_romantasy, not Book.is_ya).count()
    unknown_count = db.query(Book).filter(Book.is_romantasy, Book.is_ya is None).count()
    print(f"  YA: {ya_count}")
    print(f"  Adult: {adult_count}")
    print(f"  Unknown: {unknown_count}")


def main():
    """Main seeding function."""
    print("Starting database seeding...\n")

    # Create tables
    create_tables()

    # Create session
    db = SessionLocal()

    try:
        # Seed tags first
        tag_map = seed_tags(db)

        # Seed Romantasy books
        seed_romantasy_books(db, tag_map)

        # Print stats
        print_stats(db)

        print("\n✓ Database seeding complete!")

    except Exception as e:
        print(f"\n✗ Error during seeding: {e}")
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
