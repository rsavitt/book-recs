#!/usr/bin/env python3
"""
Process local data files and upload to Railway via bulk API.

Usage:
  # With Kaggle CSV:
  python upload_to_railway.py --csv path/to/books.csv

  # With UCSD dataset (will download if not present):
  python upload_to_railway.py --ucsd

  # Specify custom API URL:
  python upload_to_railway.py --csv books.csv --api-url https://your-app.railway.app
"""

import argparse
import csv
import gzip
import json
import sys
import urllib.request
from pathlib import Path
from typing import Iterator

import requests

# Default Railway URL
DEFAULT_API_URL = "https://book-recs-production.up.railway.app"

# Data directory
DATA_DIR = Path(__file__).parent / "data"

# UCSD URLs (new location as of 2025)
UCSD_URLS = {
    "romance_books": "https://mcauleylab.ucsd.edu/public_datasets/gdrive/goodreads/byGenre/goodreads_books_romance.json.gz",
    "romance_interactions": "https://mcauleylab.ucsd.edu/public_datasets/gdrive/goodreads/byGenre/goodreads_interactions_romance.json.gz",
}

# Romantasy detection
ROMANTASY_AUTHORS = {
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
    "leigh bardugo",
    "kresley cole",
    "ilona andrews",
    "nalini singh",
    "grace draven",
    "ruby dixon",
    "jaymin eve",
    "leia stone",
    "j. bree",
    "penelope douglas",
    "kathryn ann kingsley",
    "k.m. shea",
    "amelia hutchins",
    "c.n. crawford",
    "stacia stark",
    "kelly st. clare",
    "emma hamm",
    "k.a. tucker",
}

ROMANTASY_KEYWORDS = [
    "fae",
    "faerie",
    "dragon",
    "kingdom",
    "throne",
    "crown",
    "witch",
    "magic",
    "curse",
    "court",
    "realm",
    "shadow",
    "vampire",
    "wolf",
    "mate",
    "bond",
    "wings",
    "immortal",
    "romantasy",
    "fantasy romance",
]


def normalize_author(author: str) -> str:
    import unicodedata

    normalized = unicodedata.normalize("NFKD", author)
    normalized = "".join(c for c in normalized if not unicodedata.combining(c))
    return normalized.lower().strip()


def is_likely_romantasy(title: str, author: str, shelves: list[str] = None) -> tuple[bool, float]:
    """Check if a book is likely romantasy."""
    title_lower = title.lower()
    author_norm = normalize_author(author)
    shelves = shelves or []

    confidence = 0.0

    # Check author
    for known in ROMANTASY_AUTHORS:
        if known in author_norm:
            confidence += 0.5
            break

    # Check shelves
    romantasy_shelves = ["romantasy", "fantasy-romance", "romantic-fantasy", "fae-romance"]
    if any(rs in shelf.lower() for shelf in shelves for rs in romantasy_shelves):
        confidence += 0.4

    has_fantasy = any(s in [sh.lower() for sh in shelves] for s in ["fantasy", "paranormal"])
    has_romance = any(s in [sh.lower() for sh in shelves] for s in ["romance", "romantic"])
    if has_fantasy and has_romance:
        confidence += 0.3

    # Check title
    keyword_count = sum(1 for kw in ROMANTASY_KEYWORDS if kw in title_lower)
    confidence += min(0.2, keyword_count * 0.05)

    return confidence >= 0.3, min(1.0, confidence)


def download_file(url: str, dest: Path) -> bool:
    """Download a file with progress."""
    if dest.exists():
        print(f"  Already downloaded: {dest.name}")
        return True

    print(f"  Downloading: {url}")
    try:

        def reporthook(block_num, block_size, total_size):
            downloaded = block_num * block_size
            if total_size > 0:
                percent = min(100, downloaded * 100 / total_size)
                mb = downloaded / (1024 * 1024)
                print(f"\r    {percent:.1f}% ({mb:.1f} MB)", end="", flush=True)

        urllib.request.urlretrieve(url, dest, reporthook)
        print()
        return True
    except Exception as e:
        print(f"\n  Error: {e}")
        return False


def read_gzip_json_lines(file_path: Path) -> Iterator[dict]:
    """Read gzipped JSON lines file."""
    with gzip.open(file_path, "rt", encoding="utf-8") as f:
        for line in f:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def process_ucsd_books(data_dir: Path, limit: int = 2000) -> list[dict]:
    """Process UCSD romance books dataset."""
    books_file = data_dir / "goodreads_books_romance.json.gz"

    if not books_file.exists():
        print("Downloading UCSD romance books...")
        download_file(UCSD_URLS["romance_books"], books_file)

    print(f"Processing books (limit: {limit})...")
    books = []
    processed = 0

    for book_data in read_gzip_json_lines(books_file):
        processed += 1
        if processed % 10000 == 0:
            print(f"  Processed {processed}, found {len(books)} romantasy...")

        if len(books) >= limit:
            break

        title = book_data.get("title", "")
        authors = book_data.get("authors", [])
        author = authors[0].get("author_id", "Unknown") if authors else "Unknown"
        shelves = [s.get("name", "") for s in book_data.get("popular_shelves", [])]

        is_romantasy, confidence = is_likely_romantasy(title, author, shelves)
        if not is_romantasy:
            continue

        goodreads_id = book_data.get("book_id")
        if not goodreads_id:
            continue

        books.append(
            {
                "title": title[:500],
                "author": author[:255],
                "goodreads_id": goodreads_id,
                "isbn_13": book_data.get("isbn13"),
                "isbn_10": book_data.get("isbn"),
                "description": (book_data.get("description") or "")[:5000] or None,
                "cover_url": book_data.get("image_url"),
                "page_count": int(book_data["num_pages"]) if book_data.get("num_pages") else None,
                "publication_year": (
                    int(book_data["publication_year"])
                    if book_data.get("publication_year")
                    else None
                ),
                "is_romantasy": True,
                "romantasy_confidence": confidence,
            }
        )

    print(f"Found {len(books)} romantasy books")
    return books


def process_ucsd_interactions(
    data_dir: Path, book_ids: set[str], max_users: int = 5000
) -> tuple[list[dict], list[dict]]:
    """Process UCSD interactions for the given book IDs."""
    interactions_file = data_dir / "goodreads_interactions_romance.json.gz"

    if not interactions_file.exists():
        print("Downloading UCSD romance interactions...")
        download_file(UCSD_URLS["romance_interactions"], interactions_file)

    print(f"Processing interactions (max users: {max_users})...")
    users = {}
    ratings = []
    processed = 0

    for interaction in read_gzip_json_lines(interactions_file):
        processed += 1
        if processed % 100000 == 0:
            print(f"  Processed {processed}, {len(users)} users, {len(ratings)} ratings...")

        book_id = interaction.get("book_id")
        user_id = interaction.get("user_id")
        rating = interaction.get("rating")

        if book_id not in book_ids or not rating or rating < 1:
            continue

        # Track user
        if user_id not in users:
            if len(users) >= max_users:
                continue
            users[user_id] = {"external_id": user_id}

        ratings.append(
            {
                "external_user_id": user_id,
                "goodreads_book_id": book_id,
                "rating": min(5, max(1, int(rating))),
            }
        )

    print(f"Found {len(users)} users with {len(ratings)} ratings")
    return list(users.values()), ratings


def process_kaggle_csv(csv_path: Path) -> list[dict]:
    """Process Kaggle books CSV."""
    print(f"Processing CSV: {csv_path}")
    books = []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            title = row.get("title", row.get("Title", ""))
            author = row.get("authors", row.get("Author", row.get("author", "")))

            if not title or not author:
                continue

            is_romantasy, confidence = is_likely_romantasy(title, author)
            if not is_romantasy:
                continue

            # Parse year
            pub_year = None
            year_str = row.get(
                "publication_year", row.get("Year", row.get("original_publication_year", ""))
            )
            if year_str:
                try:
                    pub_year = int(float(year_str))
                    if pub_year < 1800 or pub_year > 2030:
                        pub_year = None
                except (ValueError, TypeError):
                    pass

            # Parse pages
            pages = None
            pages_str = row.get("num_pages", row.get("pages", ""))
            if pages_str:
                try:
                    pages = int(float(pages_str))
                except (ValueError, TypeError):
                    pass

            books.append(
                {
                    "title": title[:500],
                    "author": author.split(",")[0].strip()[:255],
                    "isbn_13": row.get("isbn13", "")[:13] or None,
                    "isbn_10": row.get("isbn", "")[:10] or None,
                    "page_count": pages,
                    "publication_year": pub_year,
                    "is_romantasy": True,
                    "romantasy_confidence": confidence,
                }
            )

    print(f"Found {len(books)} romantasy books in CSV")
    return books


def upload_books(api_url: str, books: list[dict], batch_size: int = 100) -> int:
    """Upload books in batches."""
    total_created = 0
    url = f"{api_url}/api/v1/admin/bulk/books"

    for i in range(0, len(books), batch_size):
        batch = books[i : i + batch_size]
        print(f"  Uploading books {i+1}-{i+len(batch)}...")

        try:
            response = requests.post(url, json=batch, timeout=60)
            response.raise_for_status()
            result = response.json()
            total_created += result.get("created", 0)
            print(f"    Created: {result.get('created')}, Skipped: {result.get('skipped')}")
        except Exception as e:
            print(f"    Error: {e}")

    return total_created


def upload_users(api_url: str, users: list[dict], batch_size: int = 500) -> int:
    """Upload users in batches."""
    total_created = 0
    url = f"{api_url}/api/v1/admin/bulk/users"

    for i in range(0, len(users), batch_size):
        batch = users[i : i + batch_size]
        print(f"  Uploading users {i+1}-{i+len(batch)}...")

        try:
            response = requests.post(url, json=batch, timeout=60)
            response.raise_for_status()
            result = response.json()
            total_created += result.get("created", 0)
            print(f"    Created: {result.get('created')}, Skipped: {result.get('skipped')}")
        except Exception as e:
            print(f"    Error: {e}")

    return total_created


def upload_ratings(api_url: str, ratings: list[dict], batch_size: int = 1000) -> int:
    """Upload ratings in batches."""
    total_created = 0
    url = f"{api_url}/api/v1/admin/bulk/ratings"

    for i in range(0, len(ratings), batch_size):
        batch = ratings[i : i + batch_size]
        print(f"  Uploading ratings {i+1}-{i+len(batch)}...")

        try:
            response = requests.post(url, json=batch, timeout=120)
            response.raise_for_status()
            result = response.json()
            total_created += result.get("created", 0)
            print(f"    Created: {result.get('created')}, Skipped: {result.get('skipped')}")
        except Exception as e:
            print(f"    Error: {e}")

    return total_created


def main():
    parser = argparse.ArgumentParser(description="Upload book data to Railway")
    parser.add_argument("--csv", type=str, help="Path to Kaggle CSV file")
    parser.add_argument("--ucsd", action="store_true", help="Use UCSD Goodreads dataset")
    parser.add_argument("--api-url", type=str, default=DEFAULT_API_URL, help="Railway API URL")
    parser.add_argument("--book-limit", type=int, default=2000, help="Max books to import")
    parser.add_argument("--max-users", type=int, default=5000, help="Max users to import")
    parser.add_argument("--books-only", action="store_true", help="Only upload books, no ratings")

    args = parser.parse_args()

    if not args.csv and not args.ucsd:
        print("Error: Specify --csv or --ucsd")
        print("\nExamples:")
        print("  python upload_to_railway.py --ucsd")
        print("  python upload_to_railway.py --csv data/books.csv")
        sys.exit(1)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Book Data Uploader")
    print("=" * 60)
    print(f"API URL: {args.api_url}")

    if args.ucsd:
        print("\n1. Processing UCSD dataset...")
        books = process_ucsd_books(DATA_DIR, limit=args.book_limit)

        print("\n2. Uploading books...")
        books_created = upload_books(args.api_url, books)
        print(f"Total books created: {books_created}")

        if not args.books_only:
            book_ids = {b["goodreads_id"] for b in books if b.get("goodreads_id")}

            print("\n3. Processing interactions...")
            users, ratings = process_ucsd_interactions(DATA_DIR, book_ids, max_users=args.max_users)

            print("\n4. Uploading users...")
            users_created = upload_users(args.api_url, users)
            print(f"Total users created: {users_created}")

            print("\n5. Uploading ratings...")
            ratings_created = upload_ratings(args.api_url, ratings)
            print(f"Total ratings created: {ratings_created}")

    elif args.csv:
        csv_path = Path(args.csv)
        if not csv_path.exists():
            csv_path = DATA_DIR / args.csv

        if not csv_path.exists():
            print(f"Error: CSV not found at {args.csv}")
            sys.exit(1)

        print("\n1. Processing CSV...")
        books = process_kaggle_csv(csv_path)

        print("\n2. Uploading books...")
        books_created = upload_books(args.api_url, books)
        print(f"Total books created: {books_created}")

    # Check final stats
    print("\n" + "=" * 60)
    print("Checking final stats...")
    try:
        response = requests.get(f"{args.api_url}/api/v1/admin/stats", timeout=30)
        stats = response.json()
        print(json.dumps(stats, indent=2))
    except Exception as e:
        print(f"Could not fetch stats: {e}")

    print("\nDone!")


if __name__ == "__main__":
    main()
