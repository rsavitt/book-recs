#!/usr/bin/env python3
"""
Import book data from Kaggle's Goodreads datasets.

This is a simpler alternative that uses smaller, pre-processed datasets.
You'll need to download the CSV files manually from Kaggle (requires account):

Option 1: Goodreads Books dataset (~10K books)
https://www.kaggle.com/datasets/jealousleopard/goodreadsbooks

Option 2: Best Books dataset (curated lists)
https://www.kaggle.com/datasets/meetnaren/goodreads-best-books

Usage:
1. Download CSV from Kaggle
2. Place in backend/scripts/data/
3. Run: python import_kaggle_books.py [filename.csv]
"""

import csv
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.database import Base
from app.models.book import Book, BookTag
from app.models.user import User
from app.models.rating import Rating

DATA_DIR = Path(__file__).parent / "data"

# Romantasy keywords for filtering
ROMANTASY_KEYWORDS = [
    "romantasy", "fantasy romance", "romantic fantasy",
    "fae", "faerie", "dragon", "witch", "magic", "kingdom",
    "throne", "crown", "vampire", "shifter", "mate", "bond",
    "court", "immortal", "wings", "shadow", "dark"
]

ROMANTASY_AUTHORS = {
    "sarah j. maas", "jennifer l. armentrout", "rebecca yarros",
    "holly black", "carissa broadbent", "elise kova",
    "kerri maniscalco", "raven kennedy", "scarlett st. clair",
    "laura thalassa", "leigh bardugo", "kresley cole",
    "ilona andrews", "nalini singh", "grace draven",
    "ruby dixon", "jaymin eve", "leia stone", "j. bree",
    "penelope douglas", "kathryn ann kingsley", "k.m. shea"
}


def normalize_author(author: str) -> str:
    """Normalize author name."""
    import unicodedata
    normalized = unicodedata.normalize('NFKD', author)
    normalized = ''.join(c for c in normalized if not unicodedata.combining(c))
    return normalized.lower().strip()


def is_romantasy(title: str, author: str, genres: str = "") -> bool:
    """Check if a book is likely romantasy."""
    title_lower = title.lower()
    author_lower = normalize_author(author)
    genres_lower = genres.lower() if genres else ""

    # Check author
    for known_author in ROMANTASY_AUTHORS:
        if known_author in author_lower:
            return True

    # Check for genre indicators
    if "fantasy" in genres_lower and "romance" in genres_lower:
        return True
    if "romantasy" in genres_lower:
        return True

    # Check title keywords
    keyword_count = sum(1 for kw in ROMANTASY_KEYWORDS if kw in title_lower)
    if keyword_count >= 2:
        return True

    return False


def import_goodreads_books_csv(session, file_path: Path) -> int:
    """
    Import from the standard Goodreads books CSV format.
    Expected columns: bookID, title, authors, average_rating, isbn, isbn13,
                     language_code, num_pages, ratings_count, text_reviews_count
    """
    print(f"Importing from {file_path.name}...")

    imported = 0
    skipped = 0

    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            title = row.get('title', row.get('Title', ''))
            author = row.get('authors', row.get('Author', row.get('author', '')))

            if not title or not author:
                skipped += 1
                continue

            # Check if romantasy (be permissive for this import)
            genres = row.get('genres', row.get('shelves', ''))
            if not is_romantasy(title, author, genres):
                skipped += 1
                continue

            # Check for duplicates
            existing = session.query(Book).filter(
                Book.title == title[:500],
                Book.author_normalized == normalize_author(author)[:255]
            ).first()

            if existing:
                skipped += 1
                continue

            # Parse year
            pub_year = None
            year_str = row.get('publication_year', row.get('Year', row.get('original_publication_year', '')))
            if year_str:
                try:
                    pub_year = int(float(year_str))
                    if pub_year < 1800 or pub_year > 2030:
                        pub_year = None
                except (ValueError, TypeError):
                    pass

            # Parse page count
            pages = None
            pages_str = row.get('num_pages', row.get('pages', row.get('  num_pages', '')))
            if pages_str:
                try:
                    pages = int(float(pages_str))
                except (ValueError, TypeError):
                    pass

            # Create book
            book = Book(
                title=title[:500],
                author=author.split(',')[0].strip()[:255],  # First author only
                author_normalized=normalize_author(author)[:255],
                isbn_13=row.get('isbn13', '')[:13] if row.get('isbn13') else None,
                isbn_10=row.get('isbn', '')[:10] if row.get('isbn') else None,
                page_count=pages,
                publication_year=pub_year,
                is_romantasy=True,
                romantasy_confidence=0.5,
            )

            session.add(book)
            imported += 1

            if imported % 100 == 0:
                session.commit()
                print(f"  Imported {imported} books...")

    session.commit()
    print(f"Imported {imported} books, skipped {skipped}")
    return imported


def create_sample_ratings(session, num_users: int = 100, ratings_per_user: int = 20) -> int:
    """
    Create sample users with random ratings for testing recommendations.
    """
    import random
    import hashlib

    print(f"\nCreating {num_users} sample users with ratings...")

    # Get all book IDs
    books = session.query(Book.id).all()
    book_ids = [b.id for b in books]

    if not book_ids:
        print("No books in database!")
        return 0

    rating_count = 0

    for i in range(num_users):
        # Create user
        user_hash = hashlib.md5(f"sample_user_{i}".encode()).hexdigest()[:8]
        username = f"reader_{user_hash}"

        existing = session.query(User).filter(User.username == username).first()
        if existing:
            continue

        user = User(
            email=f"{username}@sample.local",
            username=username,
            hashed_password="SAMPLE_NO_LOGIN",
            display_name=f"Reader {i+1}",
            is_public=True,
            allow_data_for_recs=True,
        )
        session.add(user)
        session.flush()

        # Create ratings (biased toward higher ratings for more realistic data)
        sample_books = random.sample(book_ids, min(ratings_per_user, len(book_ids)))
        for book_id in sample_books:
            # Bias toward 3-5 stars (realistic rating distribution)
            rating_value = random.choices([1, 2, 3, 4, 5], weights=[5, 10, 20, 35, 30])[0]

            rating = Rating(
                user_id=user.id,
                book_id=book_id,
                rating=rating_value,
                source="sample_data"
            )
            session.add(rating)
            rating_count += 1

        if (i + 1) % 20 == 0:
            session.commit()
            print(f"  Created {i+1} users...")

    session.commit()
    print(f"Created {num_users} users with {rating_count} ratings")
    return rating_count


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Check for CSV file argument
    if len(sys.argv) > 1:
        csv_file = Path(sys.argv[1])
        if not csv_file.exists():
            csv_file = DATA_DIR / sys.argv[1]
    else:
        # Look for any CSV in data directory
        csv_files = list(DATA_DIR.glob("*.csv"))
        if csv_files:
            csv_file = csv_files[0]
            print(f"Found CSV: {csv_file.name}")
        else:
            print("No CSV file provided!")
            print("\nUsage: python import_kaggle_books.py [path/to/books.csv]")
            print("\nDownload a dataset from Kaggle:")
            print("  https://www.kaggle.com/datasets/jealousleopard/goodreadsbooks")
            print("\nOr run with --sample to create sample data without a CSV:")
            print("  python import_kaggle_books.py --sample")

            if "--sample" in sys.argv:
                csv_file = None
            else:
                return

    # Connect to database
    print("\nConnecting to database...")
    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        if csv_file and csv_file.exists():
            import_goodreads_books_csv(session, csv_file)

        # Check if we should create sample ratings
        book_count = session.query(Book).count()
        user_count = session.query(User).filter(User.hashed_password.like("%NO_LOGIN%")).count()

        if book_count > 0 and user_count < 50:
            print(f"\nFound {book_count} books but only {user_count} sample users.")
            response = input("Create sample users with ratings for testing? (y/n): ")
            if response.lower() == 'y':
                create_sample_ratings(session, num_users=100, ratings_per_user=30)

        # Summary
        print("\n" + "=" * 50)
        print("DATABASE SUMMARY")
        print("=" * 50)
        print(f"Total books: {session.query(Book).count()}")
        print(f"Romantasy books: {session.query(Book).filter(Book.is_romantasy == True).count()}")
        print(f"Total users: {session.query(User).count()}")
        print(f"Total ratings: {session.query(Rating).count()}")

    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
