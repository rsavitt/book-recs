#!/usr/bin/env python3
"""
Import romantasy books from Open Library API.

Searches for books by known romantasy authors and imports them.
"""

import argparse
import json
import time

import requests

DEFAULT_API_URL = "https://book-recs-production.up.railway.app"

# Known romantasy authors to search for
ROMANTASY_AUTHORS = [
    "Sarah J. Maas",
    "Jennifer L. Armentrout",
    "Rebecca Yarros",
    "Holly Black",
    "Leigh Bardugo",
    "Carissa Broadbent",
    "Elise Kova",
    "Kerri Maniscalco",
    "Raven Kennedy",
    "Scarlett St. Clair",
    "Laura Thalassa",
    "Kresley Cole",
    "Ilona Andrews",
    "Nalini Singh",
    "Grace Draven",
    "Ruby Dixon",
    "Jaymin Eve",
    "Leia Stone",
    "J. Bree",
    "Penelope Douglas",
    "Kathryn Ann Kingsley",
    "K.M. Shea",
    "Amelia Hutchins",
    "C.N. Crawford",
    "Stacia Stark",
    "Kelly St. Clare",
    "K.A. Tucker",
    "Brigid Kemmerer",
    "Cassandra Clare",
    "Sabaa Tahir",
    "V.E. Schwab",
    "Marie Lu",
    "Renee Ahdieh",
    "Laini Taylor",
    "Susan Dennard",
    "Alexandra Bracken",
    "Stephanie Garber",
    "Adalyn Grace",
    "Danielle L. Jensen",
    "Eliza Raine",
    "C.S. Pacat",
    "Olivie Blake",
    "Hannah Nicole Maehrer",
    "Lauren Roberts",
    "Chloe C. Penaranda",
    "K.A. Knight",
    "Caroline Peckham",
    "Susanne Valenti",
]


def search_open_library(author: str, limit: int = 20) -> list[dict]:
    """Search Open Library for books by an author."""
    books = []

    url = "https://openlibrary.org/search.json"
    params = {
        "author": author,
        "limit": limit,
        "fields": "key,title,author_name,first_publish_year,isbn,cover_i,number_of_pages_median",
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        for doc in data.get("docs", []):
            title = doc.get("title", "")
            if not title:
                continue

            # Get cover URL
            cover_url = None
            cover_id = doc.get("cover_i")
            if cover_id:
                cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"

            # Get ISBN
            isbn_13 = None
            isbn_10 = None
            isbns = doc.get("isbn", [])
            for isbn in isbns:
                if len(isbn) == 13 and not isbn_13:
                    isbn_13 = isbn
                elif len(isbn) == 10 and not isbn_10:
                    isbn_10 = isbn

            books.append(
                {
                    "title": title[:500],
                    "author": author[:255],
                    "isbn_13": isbn_13,
                    "isbn_10": isbn_10,
                    "cover_url": cover_url,
                    "page_count": doc.get("number_of_pages_median"),
                    "publication_year": doc.get("first_publish_year"),
                    "is_romantasy": True,
                    "romantasy_confidence": 0.7,  # High confidence since we're searching by author
                }
            )

    except Exception as e:
        print(f"  Error searching for {author}: {e}")

    return books


def upload_books(api_url: str, books: list[dict], batch_size: int = 50) -> int:
    """Upload books in batches."""
    total_created = 0
    url = f"{api_url}/api/v1/admin/bulk/books"

    for i in range(0, len(books), batch_size):
        batch = books[i : i + batch_size]
        print(f"    Uploading batch {i//batch_size + 1}...")

        try:
            response = requests.post(url, json=batch, timeout=60)
            response.raise_for_status()
            result = response.json()
            total_created += result.get("created", 0)
        except Exception as e:
            print(f"      Error: {e}")

    return total_created


def main():
    parser = argparse.ArgumentParser(description="Import books from Open Library")
    parser.add_argument("--api-url", type=str, default=DEFAULT_API_URL)
    parser.add_argument("--books-per-author", type=int, default=15)
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between API calls")

    args = parser.parse_args()

    print("=" * 60)
    print("Open Library Importer")
    print("=" * 60)
    print(f"API URL: {args.api_url}")
    print(f"Searching {len(ROMANTASY_AUTHORS)} authors...")

    all_books = []

    for i, author in enumerate(ROMANTASY_AUTHORS):
        print(f"\n[{i+1}/{len(ROMANTASY_AUTHORS)}] Searching: {author}")
        books = search_open_library(author, limit=args.books_per_author)
        print(f"  Found {len(books)} books")
        all_books.extend(books)

        # Rate limiting
        time.sleep(args.delay)

    print(f"\n{'='*60}")
    print(f"Total books found: {len(all_books)}")

    # Deduplicate by title
    seen = set()
    unique_books = []
    for book in all_books:
        key = (book["title"].lower(), book["author"].lower())
        if key not in seen:
            seen.add(key)
            unique_books.append(book)

    print(f"Unique books: {len(unique_books)}")

    print("\nUploading to Railway...")
    created = upload_books(args.api_url, unique_books)
    print(f"\nBooks created: {created}")

    # Check stats
    print("\nFinal stats:")
    try:
        response = requests.get(f"{args.api_url}/api/v1/admin/stats", timeout=30)
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Could not fetch stats: {e}")


if __name__ == "__main__":
    main()
