#!/usr/bin/env python3
"""
Generate synthetic user ratings for testing the recommendation system.

This creates realistic-looking rating patterns:
- Users who love ACOTAR also tend to love Fourth Wing, Blood & Ash
- Users who love Holly Black tend to rate other dark fae books highly
- Introduces realistic variance (not everyone loves every book)

Run this AFTER seed_books.py to populate ratings.
"""

import hashlib
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.database import Base
from app.models.book import Book
from app.models.rating import Rating
from app.models.user import User

# Define reader "personas" - users with similar taste patterns
READER_PERSONAS = [
    {
        "name": "acotar_fan",
        "loves": ["sarah j. maas", "jennifer l. armentrout", "carissa broadbent"],
        "tropes": ["fae", "enemies-to-lovers", "morally-gray"],
        "spice_pref": (3, 5),  # prefers spicy
        "count": 30,  # number of users with this persona
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
        "spice_pref": (0, 2),  # prefers clean/YA
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
        "loves": [],  # no strong preferences
        "tropes": [],
        "spice_pref": (0, 5),
        "count": 25,  # random readers
    },
]


def normalize_author(author: str) -> str:
    """Normalize author name for matching."""
    import unicodedata

    normalized = unicodedata.normalize("NFKD", author)
    normalized = "".join(c for c in normalized if not unicodedata.combining(c))
    return normalized.lower().strip()


def calculate_rating(book: Book, persona: dict) -> int:
    """
    Calculate a rating for a book based on persona preferences.
    Returns 1-5 or 0 if the user wouldn't rate this book.
    """
    base_rating = 3.5  # Start neutral-positive

    author_norm = normalize_author(book.author)

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
        if book.spice_level < min_spice:
            base_rating -= 0.5  # Too clean
        elif book.spice_level > max_spice:
            base_rating -= 0.5  # Too spicy

    # Add randomness
    base_rating += random.gauss(0, 0.7)

    # Clamp to 1-5
    rating = max(1, min(5, round(base_rating)))

    # Some books just don't get rated (30% chance to skip)
    if random.random() < 0.3:
        return 0

    return rating


def generate_ratings(session, clear_existing: bool = False):
    """Generate synthetic ratings for all personas."""

    if clear_existing:
        # Delete sample users and their ratings
        sample_users = (
            session.query(User).filter(User.hashed_password == "SYNTHETIC_NO_LOGIN").all()
        )
        for user in sample_users:
            session.query(Rating).filter(Rating.user_id == user.id).delete()
            session.delete(user)
        session.commit()
        print("Cleared existing synthetic data")

    # Get all books
    books = session.query(Book).all()
    if not books:
        print("No books found! Run seed_books.py first.")
        return

    print(f"Found {len(books)} books")

    user_count = 0
    rating_count = 0

    for persona in READER_PERSONAS:
        print(f"\nCreating {persona['count']} '{persona['name']}' readers...")

        for i in range(persona["count"]):
            # Create user
            user_hash = hashlib.md5(
                f"{persona['name']}_{i}_{random.random()}".encode()
            ).hexdigest()[:8]
            username = f"{persona['name'][:10]}_{user_hash}"

            # Check for existing
            if session.query(User).filter(User.username == username).first():
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
            session.add(user)
            session.flush()
            user_count += 1

            # Rate books
            books_to_rate = random.sample(books, min(len(books), random.randint(8, 25)))

            for book in books_to_rate:
                rating_value = calculate_rating(book, persona)
                if rating_value == 0:
                    continue

                rating = Rating(
                    user_id=user.id, book_id=book.id, rating=rating_value, source="synthetic"
                )
                session.add(rating)
                rating_count += 1

        session.commit()

    print(f"\n{'='*50}")
    print(f"Generated {user_count} users with {rating_count} ratings")
    print(f"Average ratings per user: {rating_count / user_count:.1f}")

    # Show rating distribution
    print("\nRating distribution:")
    for r in range(1, 6):
        count = (
            session.query(Rating).filter(Rating.rating == r, Rating.source == "synthetic").count()
        )
        pct = count / rating_count * 100 if rating_count > 0 else 0
        bar = "█" * int(pct / 2)
        print(f"  {r}★: {count:4d} ({pct:5.1f}%) {bar}")


def main():
    print("=" * 50)
    print("Synthetic Rating Generator")
    print("=" * 50)

    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Check for --clear flag
        clear = "--clear" in sys.argv

        generate_ratings(session, clear_existing=clear)

        # Final stats
        print("\n" + "=" * 50)
        print("DATABASE TOTALS")
        print("=" * 50)
        print(f"Total books: {session.query(Book).count()}")
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
