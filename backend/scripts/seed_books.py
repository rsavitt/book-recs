"""
Seed database with sample romantasy books.

Run this after init_db to populate the database with books.
Usage: python -m scripts.seed_books
"""

import unicodedata

from app.core.database import SessionLocal
from app.models.book import Book, BookTag


def normalize_author(name: str) -> str:
    """Normalize author name for matching."""
    normalized = unicodedata.normalize("NFKD", name)
    ascii_name = normalized.encode("ASCII", "ignore").decode("ASCII")
    return ascii_name.lower().strip()


TROPES = [
    {"name": "Enemies to Lovers", "slug": "enemies-to-lovers", "category": "trope"},
    {"name": "Forced Proximity", "slug": "forced-proximity", "category": "trope"},
    {"name": "Fated Mates", "slug": "fated-mates", "category": "trope"},
    {"name": "Slow Burn", "slug": "slow-burn", "category": "trope"},
    {"name": "Grumpy/Sunshine", "slug": "grumpy-sunshine", "category": "trope"},
    {"name": "Found Family", "slug": "found-family", "category": "trope"},
    {"name": "Morally Grey", "slug": "morally-grey", "category": "trope"},
    {"name": "Touch Her and Die", "slug": "touch-her-and-die", "category": "trope"},
    {"name": "Only One Bed", "slug": "only-one-bed", "category": "trope"},
    {"name": "Forbidden Love", "slug": "forbidden-love", "category": "trope"},
    {"name": "Second Chance", "slug": "second-chance", "category": "trope"},
    {"name": "Fake Dating", "slug": "fake-dating", "category": "trope"},
    {"name": "Who Did This to You", "slug": "who-did-this-to-you", "category": "trope"},
    {"name": "Possessive Hero", "slug": "possessive-hero", "category": "trope"},
    {"name": "Strong Female Lead", "slug": "strong-female-lead", "category": "trope"},
]


BOOKS = [
    {
        "title": "A Court of Thorns and Roses",
        "author": "Sarah J. Maas",
        "series_name": "A Court of Thorns and Roses",
        "series_position": 1,
        "description": "When nineteen-year-old huntress Feyre kills a wolf in the woods, a terrifying creature arrives to demand retribution. Dragged to a treacherous magical land she knows about only from legends, Feyre discovers that her captor is not truly a beast, but one of the lethal, immortal faeries who once ruled her world.",
        "cover_url": "https://covers.openlibrary.org/b/isbn/9781635575569-L.jpg",
        "publication_year": 2015,
        "is_romantasy": True,
        "romantasy_confidence": 0.95,
        "spice_level": 2,
        "is_ya": False,
        "tropes": ["enemies-to-lovers", "fated-mates", "forced-proximity"],
    },
    {
        "title": "A Court of Mist and Fury",
        "author": "Sarah J. Maas",
        "series_name": "A Court of Thorns and Roses",
        "series_position": 2,
        "description": "Feyre has undergone more trials than one human woman can carry in her heart. Though she's now combating powerful High Lords, Feyre still faces her greatest enemy yet: the darkness growing inside her.",
        "cover_url": "https://covers.openlibrary.org/b/isbn/9781635575583-L.jpg",
        "publication_year": 2016,
        "is_romantasy": True,
        "romantasy_confidence": 0.98,
        "spice_level": 4,
        "is_ya": False,
        "tropes": ["enemies-to-lovers", "fated-mates", "found-family", "slow-burn"],
    },
    {
        "title": "A Court of Wings and Ruin",
        "author": "Sarah J. Maas",
        "series_name": "A Court of Thorns and Roses",
        "series_position": 3,
        "description": "Feyre has returned to the Spring Court, determined to gather information on Tamlin's maneuverings and the invading king threatening to bring Prythian to its knees.",
        "cover_url": "https://covers.openlibrary.org/b/isbn/9781635575606-L.jpg",
        "publication_year": 2017,
        "is_romantasy": True,
        "romantasy_confidence": 0.95,
        "spice_level": 4,
        "is_ya": False,
        "tropes": ["fated-mates", "found-family", "touch-her-and-die"],
    },
    {
        "title": "Fourth Wing",
        "author": "Rebecca Yarros",
        "series_name": "The Empyrean",
        "series_position": 1,
        "description": "Twenty-year-old Violet Sorrengail was supposed to enter the Scribe Quadrant, living a quiet life among books and history. Now, the commanding general—also known as her tough-as-talons mother—has ordered Violet to join the hundreds of candidates striving to become the elite of Navarre: dragon riders.",
        "cover_url": "https://covers.openlibrary.org/b/isbn/9781649374042-L.jpg",
        "publication_year": 2023,
        "is_romantasy": True,
        "romantasy_confidence": 0.99,
        "spice_level": 4,
        "is_ya": False,
        "tropes": ["enemies-to-lovers", "forced-proximity", "morally-grey", "touch-her-and-die"],
    },
    {
        "title": "Iron Flame",
        "author": "Rebecca Yarros",
        "series_name": "The Empyrean",
        "series_position": 2,
        "description": "Everyone expected Violet Sorrengail to die during her first year at Basgiath War College. Copy. Now, the real work begins.",
        "cover_url": "https://covers.openlibrary.org/b/isbn/9781649374172-L.jpg",
        "publication_year": 2023,
        "is_romantasy": True,
        "romantasy_confidence": 0.99,
        "spice_level": 4,
        "is_ya": False,
        "tropes": ["enemies-to-lovers", "found-family", "morally-grey"],
    },
    {
        "title": "From Blood and Ash",
        "author": "Jennifer L. Armentrout",
        "series_name": "Blood and Ash",
        "series_position": 1,
        "description": "Chosen from birth to usher in a new era, Poppy's life has never been her own. The life of the Maiden is solitary. But when Hawke arrives, he upends everything.",
        "cover_url": "https://covers.openlibrary.org/b/isbn/9781952457760-L.jpg",
        "publication_year": 2020,
        "is_romantasy": True,
        "romantasy_confidence": 0.95,
        "spice_level": 4,
        "is_ya": False,
        "tropes": ["forbidden-love", "possessive-hero", "touch-her-and-die", "who-did-this-to-you"],
    },
    {
        "title": "A Kingdom of Flesh and Fire",
        "author": "Jennifer L. Armentrout",
        "series_name": "Blood and Ash",
        "series_position": 2,
        "description": "From #1 New York Times bestselling author Jennifer L. Armentrout comes a new novel in her Blood and Ash series.",
        "cover_url": "https://covers.openlibrary.org/b/isbn/9781952457043-L.jpg",
        "publication_year": 2020,
        "is_romantasy": True,
        "romantasy_confidence": 0.95,
        "spice_level": 5,
        "is_ya": False,
        "tropes": ["fated-mates", "possessive-hero", "morally-grey"],
    },
    {
        "title": "The Serpent and the Wings of Night",
        "author": "Carissa Broadbent",
        "series_name": "Crowns of Nyaxia",
        "series_position": 1,
        "description": "The human ward of the vampire king enters a deadly competition for a chance at immortality in this dark romantic fantasy.",
        "cover_url": "https://covers.openlibrary.org/b/isbn/9781464220876-L.jpg",
        "publication_year": 2022,
        "is_romantasy": True,
        "romantasy_confidence": 0.95,
        "spice_level": 3,
        "is_ya": False,
        "tropes": ["enemies-to-lovers", "slow-burn", "forced-proximity", "strong-female-lead"],
    },
    {
        "title": "House of Salt and Sorrows",
        "author": "Erin A. Craig",
        "series_name": None,
        "series_position": None,
        "description": "In a manor by the sea, twelve sisters are cursed. Annaleigh lives a sheltered life with her eleven sisters on their island estate. But when her sisters start dying under mysterious circumstances, she must uncover the truth.",
        "cover_url": "https://covers.openlibrary.org/b/isbn/9781984831927-L.jpg",
        "publication_year": 2019,
        "is_romantasy": True,
        "romantasy_confidence": 0.8,
        "spice_level": 1,
        "is_ya": True,
        "tropes": ["slow-burn", "forbidden-love"],
    },
    {
        "title": "Kingdom of the Wicked",
        "author": "Kerri Maniscalco",
        "series_name": "Kingdom of the Wicked",
        "series_position": 1,
        "description": "Two sisters. One brutal murder. A quest for vengeance that will unleash Hell itself. Emilia and her twin sister Vittoria are streghe — witches who live secretly among humans.",
        "cover_url": "https://covers.openlibrary.org/b/isbn/9780316428453-L.jpg",
        "publication_year": 2020,
        "is_romantasy": True,
        "romantasy_confidence": 0.9,
        "spice_level": 2,
        "is_ya": True,
        "tropes": ["enemies-to-lovers", "slow-burn", "morally-grey"],
    },
    {
        "title": "Kingdom of the Cursed",
        "author": "Kerri Maniscalco",
        "series_name": "Kingdom of the Wicked",
        "series_position": 2,
        "description": "Emilia travels to the Seven Circles of Hell with the enigmatic Prince of Wrath in this sequel.",
        "cover_url": "https://covers.openlibrary.org/b/isbn/9780316428491-L.jpg",
        "publication_year": 2021,
        "is_romantasy": True,
        "romantasy_confidence": 0.92,
        "spice_level": 3,
        "is_ya": False,
        "tropes": ["enemies-to-lovers", "forced-proximity", "morally-grey"],
    },
    {
        "title": "The Cruel Prince",
        "author": "Holly Black",
        "series_name": "The Folk of the Air",
        "series_position": 1,
        "description": "Jude was seven when her parents were murdered and she and her two sisters were stolen away to the treacherous High Court of Faerie. Ten years later, she wants nothing more than to belong there.",
        "cover_url": "https://covers.openlibrary.org/b/isbn/9780316310314-L.jpg",
        "publication_year": 2018,
        "is_romantasy": True,
        "romantasy_confidence": 0.9,
        "spice_level": 1,
        "is_ya": True,
        "tropes": ["enemies-to-lovers", "morally-grey", "strong-female-lead"],
    },
    {
        "title": "The Wicked King",
        "author": "Holly Black",
        "series_name": "The Folk of the Air",
        "series_position": 2,
        "description": "Jude has bound herself to the Wicked King of Faerie, but when Cardan's power grows, she must face the consequences.",
        "cover_url": "https://covers.openlibrary.org/b/isbn/9780316310352-L.jpg",
        "publication_year": 2019,
        "is_romantasy": True,
        "romantasy_confidence": 0.9,
        "spice_level": 1,
        "is_ya": True,
        "tropes": ["enemies-to-lovers", "morally-grey", "forbidden-love"],
    },
    {
        "title": "The Queen of Nothing",
        "author": "Holly Black",
        "series_name": "The Folk of the Air",
        "series_position": 3,
        "description": "The conclusion to the Folk of the Air trilogy. Jude must face her fate and fight for Faerie.",
        "cover_url": "https://covers.openlibrary.org/b/isbn/9780316310420-L.jpg",
        "publication_year": 2019,
        "is_romantasy": True,
        "romantasy_confidence": 0.9,
        "spice_level": 2,
        "is_ya": True,
        "tropes": ["enemies-to-lovers", "morally-grey", "found-family"],
    },
    {
        "title": "Throne of Glass",
        "author": "Sarah J. Maas",
        "series_name": "Throne of Glass",
        "series_position": 1,
        "description": "After serving a year in the salt mines of Endovier, eighteen-year-old assassin Celaena Sardothien is dragged before the Crown Prince to compete for freedom in a deadly competition.",
        "cover_url": "https://covers.openlibrary.org/b/isbn/9781619630345-L.jpg",
        "publication_year": 2012,
        "is_romantasy": True,
        "romantasy_confidence": 0.85,
        "spice_level": 1,
        "is_ya": True,
        "tropes": ["slow-burn", "strong-female-lead", "found-family"],
    },
    {
        "title": "Crown of Midnight",
        "author": "Sarah J. Maas",
        "series_name": "Throne of Glass",
        "series_position": 2,
        "description": "Celaena Sardothien is the king's Champion. Yet she is far from loyal to the crown.",
        "cover_url": "https://covers.openlibrary.org/b/isbn/9781619630628-L.jpg",
        "publication_year": 2013,
        "is_romantasy": True,
        "romantasy_confidence": 0.85,
        "spice_level": 1,
        "is_ya": True,
        "tropes": ["slow-burn", "strong-female-lead", "forbidden-love"],
    },
    {
        "title": "Heir of Fire",
        "author": "Sarah J. Maas",
        "series_name": "Throne of Glass",
        "series_position": 3,
        "description": "Celaena has survived deadly contests and shattering heartbreak. Now she must travel to a new land to confront her darkest truth.",
        "cover_url": "https://covers.openlibrary.org/b/isbn/9781619630659-L.jpg",
        "publication_year": 2014,
        "is_romantasy": True,
        "romantasy_confidence": 0.88,
        "spice_level": 2,
        "is_ya": True,
        "tropes": ["slow-burn", "found-family", "enemies-to-lovers"],
    },
    {
        "title": "Powerless",
        "author": "Lauren Roberts",
        "series_name": "The Powerless Trilogy",
        "series_position": 1,
        "description": "In a world where the elite have abilities, Paedyn Gray is powerless — and must hide that secret at all costs during the deadly Purging Trials.",
        "cover_url": "https://covers.openlibrary.org/b/isbn/9781665954884-L.jpg",
        "publication_year": 2023,
        "is_romantasy": True,
        "romantasy_confidence": 0.95,
        "spice_level": 2,
        "is_ya": True,
        "tropes": ["enemies-to-lovers", "forced-proximity", "grumpy-sunshine"],
    },
    {
        "title": "Reckless",
        "author": "Lauren Roberts",
        "series_name": "The Powerless Trilogy",
        "series_position": 2,
        "description": "The thrilling sequel to Powerless. Paedyn and Kai must navigate treacherous waters.",
        "cover_url": "https://covers.openlibrary.org/b/isbn/9781665954914-L.jpg",
        "publication_year": 2024,
        "is_romantasy": True,
        "romantasy_confidence": 0.95,
        "spice_level": 3,
        "is_ya": False,
        "tropes": ["enemies-to-lovers", "slow-burn", "morally-grey"],
    },
    {
        "title": "Divine Rivals",
        "author": "Rebecca Ross",
        "series_name": "Letters of Enchantment",
        "series_position": 1,
        "description": "When two young journalists find themselves on opposite sides of a god's war, they must choose between love and duty.",
        "cover_url": "https://covers.openlibrary.org/b/isbn/9781250857439-L.jpg",
        "publication_year": 2023,
        "is_romantasy": True,
        "romantasy_confidence": 0.92,
        "spice_level": 1,
        "is_ya": True,
        "tropes": ["enemies-to-lovers", "slow-burn", "grumpy-sunshine"],
    },
    {
        "title": "Ruthless Vows",
        "author": "Rebecca Ross",
        "series_name": "Letters of Enchantment",
        "series_position": 2,
        "description": "The conclusion to the Letters of Enchantment duology. Iris and Roman must find their way back to each other.",
        "cover_url": "https://covers.openlibrary.org/b/isbn/9781250857484-L.jpg",
        "publication_year": 2024,
        "is_romantasy": True,
        "romantasy_confidence": 0.92,
        "spice_level": 2,
        "is_ya": True,
        "tropes": ["second-chance", "slow-burn", "found-family"],
    },
    {
        "title": "A Shadow in the Ember",
        "author": "Jennifer L. Armentrout",
        "series_name": "Flesh and Fire",
        "series_position": 1,
        "description": "Born shrouded in the veil of the Primals, a Maiden as the Fates promised. A prequel series to Blood and Ash.",
        "cover_url": "https://covers.openlibrary.org/b/isbn/9781952457760-L.jpg",
        "publication_year": 2021,
        "is_romantasy": True,
        "romantasy_confidence": 0.95,
        "spice_level": 5,
        "is_ya": False,
        "tropes": ["enemies-to-lovers", "slow-burn", "fated-mates", "forbidden-love"],
    },
    {
        "title": "A Light in the Flame",
        "author": "Jennifer L. Armentrout",
        "series_name": "Flesh and Fire",
        "series_position": 2,
        "description": "The fiery sequel to A Shadow in the Ember.",
        "cover_url": "https://covers.openlibrary.org/b/isbn/9781952457791-L.jpg",
        "publication_year": 2022,
        "is_romantasy": True,
        "romantasy_confidence": 0.95,
        "spice_level": 5,
        "is_ya": False,
        "tropes": ["fated-mates", "possessive-hero", "touch-her-and-die"],
    },
    {
        "title": "Daughter of No Worlds",
        "author": "Carissa Broadbent",
        "series_name": "The War of Lost Hearts",
        "series_position": 1,
        "description": "A former slave with forbidden magic. A reclusive vampire lord. An unlikely alliance that will shake the foundations of their world.",
        "cover_url": "https://covers.openlibrary.org/b/isbn/9781464220838-L.jpg",
        "publication_year": 2021,
        "is_romantasy": True,
        "romantasy_confidence": 0.92,
        "spice_level": 4,
        "is_ya": False,
        "tropes": ["slow-burn", "grumpy-sunshine", "found-family", "strong-female-lead"],
    },
    {
        "title": "The Bridge Kingdom",
        "author": "Danielle L. Jensen",
        "series_name": "The Bridge Kingdom",
        "series_position": 1,
        "description": "Lara has trained to be a lethal spy. Now, her mission is to marry the King of the Bridge Kingdom — and destroy it from within.",
        "cover_url": "https://covers.openlibrary.org/b/isbn/9781733090315-L.jpg",
        "publication_year": 2019,
        "is_romantasy": True,
        "romantasy_confidence": 0.93,
        "spice_level": 3,
        "is_ya": False,
        "tropes": ["enemies-to-lovers", "fake-dating", "slow-burn", "strong-female-lead"],
    },
    {
        "title": "The Traitor Queen",
        "author": "Danielle L. Jensen",
        "series_name": "The Bridge Kingdom",
        "series_position": 2,
        "description": "The sequel to The Bridge Kingdom. Lara must prove her loyalty.",
        "cover_url": "https://covers.openlibrary.org/b/isbn/9781733090353-L.jpg",
        "publication_year": 2020,
        "is_romantasy": True,
        "romantasy_confidence": 0.93,
        "spice_level": 3,
        "is_ya": False,
        "tropes": ["second-chance", "strong-female-lead", "found-family"],
    },
    {
        "title": "House of Earth and Blood",
        "author": "Sarah J. Maas",
        "series_name": "Crescent City",
        "series_position": 1,
        "description": "Bryce Quinlan had the perfect life until a demon murdered her closest friends. Now she seeks revenge.",
        "cover_url": "https://covers.openlibrary.org/b/isbn/9781635574043-L.jpg",
        "publication_year": 2020,
        "is_romantasy": True,
        "romantasy_confidence": 0.9,
        "spice_level": 3,
        "is_ya": False,
        "tropes": ["slow-burn", "found-family", "grumpy-sunshine"],
    },
    {
        "title": "House of Sky and Breath",
        "author": "Sarah J. Maas",
        "series_name": "Crescent City",
        "series_position": 2,
        "description": "Bryce Quinlan and Hunt Athalar are trying to get back to normal. But war is brewing.",
        "cover_url": "https://covers.openlibrary.org/b/isbn/9781635574074-L.jpg",
        "publication_year": 2022,
        "is_romantasy": True,
        "romantasy_confidence": 0.9,
        "spice_level": 4,
        "is_ya": False,
        "tropes": ["fated-mates", "found-family", "touch-her-and-die"],
    },
    {
        "title": "Zodiac Academy: The Awakening",
        "author": "Caroline Peckham",
        "series_name": "Zodiac Academy",
        "series_position": 1,
        "description": "Twin sisters discover they're Fae princesses and must attend Zodiac Academy, where the ruthless Heirs will do anything to stop them.",
        "cover_url": "https://covers.openlibrary.org/b/isbn/9781914425004-L.jpg",
        "publication_year": 2019,
        "is_romantasy": True,
        "romantasy_confidence": 0.85,
        "spice_level": 3,
        "is_ya": False,
        "tropes": ["enemies-to-lovers", "forced-proximity", "slow-burn"],
    },
]


def seed_books():
    """Seed the database with sample romantasy books."""
    db = SessionLocal()

    try:
        # Create tags first
        print("Creating tags...")
        tag_map = {}
        for trope_data in TROPES:
            existing = db.query(BookTag).filter(BookTag.slug == trope_data["slug"]).first()
            if existing:
                tag_map[trope_data["slug"]] = existing
            else:
                tag = BookTag(
                    name=trope_data["name"],
                    slug=trope_data["slug"],
                    category=trope_data["category"],
                    is_romantasy_indicator=True,
                )
                db.add(tag)
                db.flush()
                tag_map[trope_data["slug"]] = tag

        # Create books
        print("Creating books...")
        for book_data in BOOKS:
            # Check if book already exists
            existing = db.query(Book).filter(
                Book.title == book_data["title"],
                Book.author == book_data["author"]
            ).first()

            if existing:
                print(f"  Skipping (exists): {book_data['title']}")
                continue

            tropes = book_data.pop("tropes", [])

            book = Book(
                title=book_data["title"],
                author=book_data["author"],
                author_normalized=normalize_author(book_data["author"]),
                series_name=book_data.get("series_name"),
                series_position=book_data.get("series_position"),
                description=book_data.get("description"),
                cover_url=book_data.get("cover_url"),
                publication_year=book_data.get("publication_year"),
                is_romantasy=book_data.get("is_romantasy", True),
                romantasy_confidence=book_data.get("romantasy_confidence", 0.9),
                spice_level=book_data.get("spice_level"),
                is_ya=book_data.get("is_ya"),
            )

            # Add tags
            for trope_slug in tropes:
                if trope_slug in tag_map:
                    book.tags.append(tag_map[trope_slug])

            db.add(book)
            print(f"  Added: {book_data['title']}")

        db.commit()
        print(f"\nSeeding complete! Added {len(BOOKS)} books and {len(TROPES)} tags.")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_books()
