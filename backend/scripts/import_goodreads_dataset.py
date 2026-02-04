#!/usr/bin/env python3
"""
Import book and rating data from the UCSD Goodreads dataset.

Dataset: https://mengtingwan.github.io/data/goodreads.html
Citation: Mengting Wan, Julian McAuley, "Item Recommendation on Monotonic Behavior Chains",
          RecSys 2018.

This script downloads and processes the fantasy genre subset, filtering for romantasy books.
"""

import gzip
import json
import os
import sys
import urllib.request
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.database import Base
from app.models.book import Book, BookEdition, BookTag
from app.models.rating import Rating
from app.models.user import User

# UCSD Goodreads dataset URLs
# Using the genre-specific subsets for smaller downloads
DATASET_URLS = {
    # Fantasy genre books and interactions
    "fantasy_books": "https://datarepo.eng.ucsd.edu/mcauley_group/gdrive/goodreads/byGenre/goodreads_books_fantasy_paranormal.json.gz",
    "fantasy_interactions": "https://datarepo.eng.ucsd.edu/mcauley_group/gdrive/goodreads/byGenre/goodreads_interactions_fantasy_paranormal.json.gz",
    # Romance genre books and interactions
    "romance_books": "https://datarepo.eng.ucsd.edu/mcauley_group/gdrive/goodreads/byGenre/goodreads_books_romance.json.gz",
    "romance_interactions": "https://datarepo.eng.ucsd.edu/mcauley_group/gdrive/goodreads/byGenre/goodreads_interactions_romance.json.gz",
}

# Data directory
DATA_DIR = Path(__file__).parent / "data"

# Romantasy indicators - books with these in title/description are likely romantasy
ROMANTASY_TITLE_KEYWORDS = [
    "fae",
    "faerie",
    "fairy",
    "dragon",
    "kingdom",
    "throne",
    "crown",
    "prince",
    "princess",
    "queen",
    "king",
    "witch",
    "magic",
    "curse",
    "court",
    "realm",
    "shadow",
    "blood",
    "night",
    "dark",
    "moon",
    "star",
    "wings",
    "immortal",
    "vampire",
    "wolf",
    "mate",
    "bond",
    "chosen",
    "prophecy",
    "warrior",
]

# Known romantasy authors
ROMANTASY_AUTHORS = [
    "sarah j. maas",
    "jennifer l. armentrout",
    "rebecca yarros",
    "holly black",
    "carissa broadbent",
    "elise kova",
    "kerri maniscalco",
    "raven kennedy",
    "scarlett st. clair",
    "laura thalassa",
    "k.a. tucker",
    "brigid kemmerer",
    "leigh bardugo",
    "kresley cole",
    "ilona andrews",
    "nalini singh",
    "grace draven",
    "kathryn ann kingsley",
    "ruby dixon",
    "a.k. caggiano",
    "c.n. crawford",
    "k.m. shea",
    "amelia hutchins",
    "jaymin eve",
    "leia stone",
    "kelly st. clare",
    "stacia stark",
    "kate & the couch",
    "c. rochelle",
    "j. bree",
    "mariana zapata",
    "penelope douglas",
]

# Tropes to look for in shelves/tags
ROMANTASY_TROPES = {
    "enemies-to-lovers": ["enemies to lovers", "enemies-to-lovers", "hate to love"],
    "fated-mates": ["fated mates", "fated-mates", "mate bond", "soulmates", "soul mates"],
    "slow-burn": ["slow burn", "slow-burn", "slowburn"],
    "forced-proximity": ["forced proximity", "forced-proximity", "stuck together"],
    "fake-relationship": [
        "fake relationship",
        "fake-relationship",
        "fake dating",
        "pretend relationship",
    ],
    "morally-gray": ["morally grey", "morally gray", "villain", "antihero", "dark hero"],
    "found-family": ["found family", "found-family", "chosen family"],
    "fae": ["fae", "faerie", "fairy", "faeries", "fae romance"],
    "dragon": ["dragon", "dragons", "dragon rider", "dragon shifter"],
    "witch": ["witch", "witches", "witchcraft"],
    "vampire": ["vampire", "vampires", "vampire romance"],
    "shifter": ["shifter", "shape shifter", "shapeshifter", "werewolf", "wolf shifter"],
    "academy": ["academy", "magical academy", "magic school"],
    "royal": ["royalty", "royal", "prince", "princess", "king", "queen"],
    "dark-romance": ["dark romance", "dark-romance", "dark fantasy romance"],
    "reverse-harem": ["reverse harem", "reverse-harem", "why choose", "polyamory"],
    "spicy": ["spicy", "steamy", "adult romance", "smut", "explicit"],
    "ya": ["young adult", "ya", "teen", "ya fantasy"],
}


def download_file(url: str, dest_path: Path) -> bool:
    """Download a file with progress indication."""
    if dest_path.exists():
        print(f"  Already downloaded: {dest_path.name}")
        return True

    print(f"  Downloading: {url}")
    try:

        def reporthook(block_num, block_size, total_size):
            downloaded = block_num * block_size
            if total_size > 0:
                percent = min(100, downloaded * 100 / total_size)
                mb_downloaded = downloaded / (1024 * 1024)
                mb_total = total_size / (1024 * 1024)
                print(
                    f"\r    {percent:.1f}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)",
                    end="",
                    flush=True,
                )

        urllib.request.urlretrieve(url, dest_path, reporthook)
        print()  # newline after progress
        return True
    except Exception as e:
        print(f"\n  Error downloading: {e}")
        return False


def read_gzip_json_lines(file_path: Path):
    """Read a gzipped JSON lines file."""
    with gzip.open(file_path, "rt", encoding="utf-8") as f:
        for line in f:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def normalize_author(author: str) -> str:
    """Normalize author name for matching."""
    import unicodedata

    # Remove accents
    normalized = unicodedata.normalize("NFKD", author)
    normalized = "".join(c for c in normalized if not unicodedata.combining(c))
    # Lowercase and strip
    return normalized.lower().strip()


def is_likely_romantasy(book: dict) -> tuple[bool, float, list[str]]:
    """
    Determine if a book is likely romantasy based on metadata.
    Returns (is_romantasy, confidence, matched_tropes)
    """
    title = book.get("title", "").lower()
    author = normalize_author(
        book.get("authors", [{}])[0].get("author_id", "") if book.get("authors") else ""
    )
    description = book.get("description", "").lower() if book.get("description") else ""
    shelves = [s.get("name", "").lower() for s in book.get("popular_shelves", [])]

    confidence = 0.0
    matched_tropes = []

    # Check author (high confidence)
    for known_author in ROMANTASY_AUTHORS:
        if known_author in author:
            confidence += 0.4
            break

    # Check title keywords
    title_matches = sum(1 for kw in ROMANTASY_TITLE_KEYWORDS if kw in title)
    if title_matches > 0:
        confidence += min(0.2, title_matches * 0.05)

    # Check shelves for romantasy indicators
    romantasy_shelf_keywords = ["romantasy", "fantasy romance", "romantic fantasy", "fae romance"]
    for shelf in shelves:
        if any(kw in shelf for kw in romantasy_shelf_keywords):
            confidence += 0.3
            break

    # Check for trope matches
    for trope_slug, trope_variants in ROMANTASY_TROPES.items():
        for variant in trope_variants:
            if any(variant in shelf for shelf in shelves):
                matched_tropes.append(trope_slug)
                confidence += 0.05
                break
            if variant in description:
                matched_tropes.append(trope_slug)
                confidence += 0.02
                break

    # Check if it's in both fantasy and romance shelves
    has_fantasy = any(
        s in ["fantasy", "paranormal", "urban-fantasy", "epic-fantasy"] for s in shelves
    )
    has_romance = any(s in ["romance", "love", "romantic"] for s in shelves)
    if has_fantasy and has_romance:
        confidence += 0.2

    # Cap confidence at 1.0
    confidence = min(1.0, confidence)

    # Consider it romantasy if confidence > 0.3
    is_romantasy = confidence >= 0.3

    return is_romantasy, confidence, list(set(matched_tropes))


def estimate_spice_level(book: dict) -> int | None:
    """Estimate spice level from shelves and description."""
    shelves = [s.get("name", "").lower() for s in book.get("popular_shelves", [])]
    description = (book.get("description", "") or "").lower()

    # Check for explicit indicators
    if any(s in shelves for s in ["erotica", "erotic", "explicit", "smut", "very-spicy"]):
        return 5
    if any(s in shelves for s in ["steamy", "hot", "spicy", "adult-romance"]):
        return 4
    if any(s in shelves for s in ["sensual", "mature"]):
        return 3
    if any(s in shelves for s in ["fade-to-black", "clean-romance"]):
        return 1
    if any(s in shelves for s in ["ya", "young-adult", "teen"]):
        return 0

    # Check description
    if any(word in description for word in ["explicit", "erotica", "graphic sex"]):
        return 5
    if any(word in description for word in ["steamy", "passionate", "sensual"]):
        return 3

    return 2  # Default middle ground


def is_ya(book: dict) -> bool | None:
    """Determine if book is YA."""
    shelves = [s.get("name", "").lower() for s in book.get("popular_shelves", [])]

    if any(s in ["ya", "young-adult", "teen", "ya-fantasy", "ya-romance"] for s in shelves):
        return True
    if any(s in ["adult", "adult-fiction", "adult-fantasy", "new-adult"] for s in shelves):
        return False

    return None


def extract_series_info(book: dict) -> tuple[str | None, float | None]:
    """Extract series name and position from book title or series field."""
    title = book.get("title", "")
    series = book.get("series", [])

    if series:
        # Use first series entry
        s = series[0] if isinstance(series, list) else series
        if isinstance(s, dict):
            return s.get("title"), s.get("position")
        elif isinstance(s, str):
            return s, None

    # Try to parse from title (common pattern: "Title (Series Name #1)")
    import re

    match = re.search(r"\(([^#]+)#?(\d+\.?\d*)?\)", title)
    if match:
        series_name = match.group(1).strip()
        position = float(match.group(2)) if match.group(2) else None
        return series_name, position

    return None, None


def get_or_create_tag(session, tag_name: str, category: str = "trope") -> BookTag:
    """Get or create a book tag."""
    slug = tag_name.lower().replace(" ", "-")
    tag = session.query(BookTag).filter(BookTag.slug == slug).first()
    if not tag:
        tag = BookTag(
            name=tag_name.replace("-", " ").title(),
            slug=slug,
            category=category,
            is_romantasy_indicator=(category == "trope"),
        )
        session.add(tag)
        session.flush()
    return tag


def import_books(session, data_dir: Path, limit: int | None = None) -> dict[str, int]:
    """
    Import books from the dataset.
    Returns mapping of goodreads_book_id -> our book_id
    """
    print("\nProcessing books...")

    # Track book IDs: goodreads_id -> our_id
    book_id_map = {}

    # Process both fantasy and romance books
    books_processed = 0
    romantasy_count = 0

    for genre in ["fantasy", "romance"]:
        file_path = (
            data_dir / f"goodreads_books_{genre}_paranormal.json.gz"
            if genre == "fantasy"
            else data_dir / f"goodreads_books_{genre}.json.gz"
        )

        if not file_path.exists():
            print(f"  Skipping {genre} - file not found")
            continue

        print(f"  Processing {genre} books...")

        for book_data in read_gzip_json_lines(file_path):
            if limit and romantasy_count >= limit:
                break

            books_processed += 1
            if books_processed % 10000 == 0:
                print(
                    f"    Processed {books_processed} books, found {romantasy_count} romantasy..."
                )

            # Check if it's romantasy
            is_romantasy, confidence, tropes = is_likely_romantasy(book_data)
            if not is_romantasy:
                continue

            goodreads_id = book_data.get("book_id")
            if not goodreads_id:
                continue

            # Skip if we already have this book
            if goodreads_id in book_id_map:
                continue

            # Check if book already exists by goodreads_id
            existing_edition = (
                session.query(BookEdition)
                .filter(BookEdition.goodreads_book_id == goodreads_id)
                .first()
            )
            if existing_edition:
                book_id_map[goodreads_id] = existing_edition.book_id
                continue

            # Extract book data
            title = book_data.get("title", "Unknown")
            authors = book_data.get("authors", [])
            author = authors[0].get("author_id", "Unknown") if authors else "Unknown"

            # Get actual author name from author_id if possible
            # The dataset uses author IDs, not names - we'll need to clean this up
            # For now, use what's available

            series_name, series_position = extract_series_info(book_data)
            spice = estimate_spice_level(book_data)
            ya = is_ya(book_data)

            # Create book
            book = Book(
                title=title[:500],  # Truncate to fit
                author=author[:255] if author else "Unknown",
                author_normalized=normalize_author(author)[:255] if author else "unknown",
                description=(
                    book_data.get("description", "")[:5000]
                    if book_data.get("description")
                    else None
                ),
                cover_url=book_data.get("image_url"),
                page_count=int(book_data.get("num_pages")) if book_data.get("num_pages") else None,
                publication_year=(
                    int(book_data.get("publication_year"))
                    if book_data.get("publication_year")
                    else None
                ),
                series_name=series_name[:255] if series_name else None,
                series_position=series_position,
                is_romantasy=True,
                romantasy_confidence=confidence,
                spice_level=spice,
                is_ya=ya,
                isbn_13=book_data.get("isbn13")[:13] if book_data.get("isbn13") else None,
                isbn_10=book_data.get("isbn")[:10] if book_data.get("isbn") else None,
            )

            session.add(book)
            session.flush()  # Get the ID

            # Create edition linking to goodreads
            edition = BookEdition(
                book_id=book.id,
                goodreads_book_id=goodreads_id,
                isbn_13=book_data.get("isbn13"),
                isbn_10=book_data.get("isbn"),
            )
            session.add(edition)

            # Add trope tags
            for trope in tropes:
                tag = get_or_create_tag(session, trope, "trope")
                if tag not in book.tags:
                    book.tags.append(tag)

            book_id_map[goodreads_id] = book.id
            romantasy_count += 1

            # Commit periodically
            if romantasy_count % 500 == 0:
                session.commit()
                print(f"    Committed {romantasy_count} romantasy books...")

        if limit and romantasy_count >= limit:
            break

    session.commit()
    print(f"  Imported {romantasy_count} romantasy books from {books_processed} total")

    return book_id_map


def import_ratings(session, data_dir: Path, book_id_map: dict[str, int], max_users: int = 10000):
    """
    Import user ratings for the books we've imported.
    Creates synthetic users with hashed goodreads user IDs.
    """
    print("\nProcessing ratings...")

    # Track users: goodreads_user_id -> our_user_id
    user_id_map = {}
    user_count = 0
    rating_count = 0

    for genre in ["fantasy", "romance"]:
        file_path = (
            data_dir / f"goodreads_interactions_{genre}_paranormal.json.gz"
            if genre == "fantasy"
            else data_dir / f"goodreads_interactions_{genre}.json.gz"
        )

        if not file_path.exists():
            print(f"  Skipping {genre} interactions - file not found")
            continue

        print(f"  Processing {genre} interactions...")

        for interaction in read_gzip_json_lines(file_path):
            book_id = interaction.get("book_id")
            user_id = interaction.get("user_id")
            rating = interaction.get("rating")

            # Skip if not a book we imported or no rating
            if book_id not in book_id_map:
                continue
            if not rating or rating < 1:
                continue

            our_book_id = book_id_map[book_id]

            # Get or create user
            if user_id not in user_id_map:
                if user_count >= max_users:
                    continue  # Skip new users if we've hit the limit

                # Create synthetic user
                # Use a hash of the goodreads ID for privacy
                import hashlib

                user_hash = hashlib.md5(user_id.encode()).hexdigest()[:8]
                username = f"reader_{user_hash}"
                email = f"{username}@imported.local"

                user = User(
                    email=email,
                    username=username,
                    hashed_password="IMPORTED_NO_LOGIN",  # These users can't log in
                    display_name=f"Reader {user_hash[:4].upper()}",
                    is_public=True,
                    allow_data_for_recs=True,
                )
                session.add(user)
                session.flush()

                user_id_map[user_id] = user.id
                user_count += 1

                if user_count % 1000 == 0:
                    print(f"    Created {user_count} users...")

            our_user_id = user_id_map[user_id]

            # Check if rating already exists
            existing = (
                session.query(Rating)
                .filter(Rating.user_id == our_user_id, Rating.book_id == our_book_id)
                .first()
            )

            if existing:
                continue

            # Create rating
            rating_obj = Rating(
                user_id=our_user_id,
                book_id=our_book_id,
                rating=min(5, max(1, int(rating))),  # Ensure 1-5 range
                source="goodreads_dataset",
            )
            session.add(rating_obj)
            rating_count += 1

            # Commit periodically
            if rating_count % 5000 == 0:
                session.commit()
                print(f"    Imported {rating_count} ratings...")

    session.commit()
    print(f"  Imported {rating_count} ratings from {user_count} users")

    return rating_count, user_count


def main():
    print("=" * 60)
    print("UCSD Goodreads Dataset Importer for Romantasy Recommender")
    print("=" * 60)

    # Create data directory
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Download dataset files
    print("\n1. Downloading dataset files...")
    for name, url in DATASET_URLS.items():
        filename = url.split("/")[-1]
        dest = DATA_DIR / filename
        if not download_file(url, dest):
            print(f"Failed to download {name}, continuing anyway...")

    # Connect to database
    print("\n2. Connecting to database...")
    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Import books (limit to 5000 for reasonable size)
        print("\n3. Importing books...")
        book_limit = int(os.environ.get("BOOK_LIMIT", "5000"))
        book_id_map = import_books(session, DATA_DIR, limit=book_limit)

        if not book_id_map:
            print("No books imported! Check if files downloaded correctly.")
            return

        # Import ratings
        print("\n4. Importing ratings...")
        max_users = int(os.environ.get("MAX_USERS", "10000"))
        rating_count, user_count = import_ratings(
            session, DATA_DIR, book_id_map, max_users=max_users
        )

        # Print summary
        print("\n" + "=" * 60)
        print("IMPORT COMPLETE")
        print("=" * 60)
        print(f"Books imported: {len(book_id_map)}")
        print(f"Users created: {user_count}")
        print(f"Ratings imported: {rating_count}")
        print(f"\nData files stored in: {DATA_DIR}")
        print("\nYou can adjust limits with environment variables:")
        print("  BOOK_LIMIT=5000 (default)")
        print("  MAX_USERS=10000 (default)")

    except Exception as e:
        session.rollback()
        print(f"\nError during import: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
