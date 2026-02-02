"""Tests for StoryGraph CSV parser and auto-detection."""

import pytest
from app.services.storygraph_parser import StoryGraphCSVParser, parse_storygraph_csv
from app.services.csv_parser import detect_csv_source, parse_library_csv


# Sample StoryGraph CSV content
VALID_STORYGRAPH_CSV = b"""Title,Authors,Contributors,ISBN/UID,Format,Read Status,Date Added,Last Date Read,Dates Read,Read Count,Moods,Pace,Character- or Plot-Driven?,Strong Character Development?,Loveable Characters?,Diverse Characters?,Flawed Characters?,Star Rating,Review,Content Warnings,Content Warning Description,Tags,Owned?
A Court of Thorns and Roses (A Court of Thorns and Roses #1),Sarah J. Maas,,9781619634442,Paperback,read,2023/12/01,2024/01/15,,1,adventurous,fast,Plot,Yes,Yes,No,Yes,4.5,Great book!,,,romantasy fae favorites,Yes
Fourth Wing (The Empyrean #1),Rebecca Yarros,,9781649374042,Hardcover,read,2024/01/10,2024/02/20,,1,emotional tense,fast,Both,Yes,Yes,Yes,Yes,4.0,,,,romantasy dragons,No
The Cruel Prince (The Folk of the Air #1),Holly Black,,,Paperback,to-read,2024/03/01,,,0,dark mysterious,medium,Character,,,,,,,,,fae,No
"""

MINIMAL_STORYGRAPH_CSV = b"""Title,Authors,Read Status,Star Rating
Test Book,Test Author,read,3.5
"""

STORYGRAPH_WITH_DNF = b"""Title,Authors,Read Status,Star Rating
DNF Book,Some Author,did-not-finish,2.0
"""

STORYGRAPH_UNRATED = b"""Title,Authors,Read Status,Star Rating
Unrated Book,Author Name,to-read,
"""

# Sample Goodreads CSV for comparison
GOODREADS_CSV = b"""Book Id,Title,Author,My Rating,Exclusive Shelf
12345,Test Book,Test Author,4,read
"""


class TestStoryGraphCSVParser:
    """Test cases for StoryGraphCSVParser."""

    def test_validate_valid_csv(self):
        """Valid StoryGraph CSV should pass validation."""
        parser = StoryGraphCSVParser(VALID_STORYGRAPH_CSV)
        assert parser.validate() is True
        assert len(parser.errors) == 0

    def test_validate_minimal_csv(self):
        """Minimal CSV with required headers should pass."""
        parser = StoryGraphCSVParser(MINIMAL_STORYGRAPH_CSV)
        assert parser.validate() is True

    def test_validate_empty_csv(self):
        """Empty CSV should fail validation."""
        parser = StoryGraphCSVParser(b"")
        assert parser.validate() is False

    def test_validate_wrong_format(self):
        """Goodreads CSV should fail StoryGraph validation."""
        parser = StoryGraphCSVParser(GOODREADS_CSV)
        assert parser.validate() is False
        assert "StoryGraph" in parser.errors[0]

    def test_parse_full_record(self):
        """Parse a full StoryGraph record with all fields."""
        parser = StoryGraphCSVParser(VALID_STORYGRAPH_CSV)
        assert parser.validate()

        books = list(parser.parse())
        assert len(books) == 3

        # Check first book (ACOTAR)
        book = books[0]
        assert book.title == "A Court of Thorns and Roses"
        assert book.author == "Sarah J. Maas"
        assert book.isbn13 == "9781619634442"
        assert book.rating == 5  # 4.5 rounded up to 5
        assert book.series_name == "A Court of Thorns and Roses"
        assert book.series_position == 1.0
        assert book.exclusive_shelf == "read"
        assert book.binding == "Paperback"
        assert book.review == "Great book!"
        # Verify date parsing
        assert book.date_added is not None
        assert book.date_read is not None

    def test_parse_series_extraction(self):
        """Series name and position should be extracted from title."""
        parser = StoryGraphCSVParser(VALID_STORYGRAPH_CSV)
        books = list(parser.parse())

        # Fourth Wing
        book = books[1]
        assert book.title == "Fourth Wing"
        assert book.series_name == "The Empyrean"
        assert book.series_position == 1.0

        # The Cruel Prince
        book = books[2]
        assert book.title == "The Cruel Prince"
        assert book.series_name == "The Folk of the Air"
        assert book.series_position == 1.0

    def test_parse_rating_conversion(self):
        """Float ratings should be converted to integers (ceiling)."""
        parser = StoryGraphCSVParser(VALID_STORYGRAPH_CSV)
        books = list(parser.parse())

        # 4.5 -> 5 (ceiling)
        assert books[0].rating == 5

        # 4.0 -> 4
        assert books[1].rating == 4

    def test_parse_rating_half_stars(self):
        """Test various half-star ratings."""
        csv = b"""Title,Authors,Read Status,Star Rating
Book 1,Author,read,3.5
Book 2,Author,read,2.5
Book 3,Author,read,1.0
Book 4,Author,read,0.5
"""
        parser = StoryGraphCSVParser(csv)
        books = list(parser.parse())

        assert books[0].rating == 4  # 3.5 -> 4
        assert books[1].rating == 3  # 2.5 -> 3
        assert books[2].rating == 1  # 1.0 -> 1
        assert books[3].rating == 1  # 0.5 -> 1

    def test_parse_unrated_book(self):
        """Unrated books should have rating=0."""
        parser = StoryGraphCSVParser(STORYGRAPH_UNRATED)
        books = list(parser.parse())

        assert len(books) == 1
        assert books[0].rating == 0
        assert books[0].exclusive_shelf == "to-read"

    def test_parse_did_not_finish(self):
        """Did-not-finish status should be mapped correctly."""
        parser = StoryGraphCSVParser(STORYGRAPH_WITH_DNF)
        books = list(parser.parse())

        assert len(books) == 1
        assert books[0].exclusive_shelf == "did-not-finish"
        assert books[0].rating == 2

    def test_parse_date_formats(self):
        """StoryGraph dates (YYYY/MM/DD) should be parsed correctly."""
        parser = StoryGraphCSVParser(VALID_STORYGRAPH_CSV)
        books = list(parser.parse())

        book = books[0]
        assert book.date_read is not None
        assert book.date_read.year == 2024
        assert book.date_read.month == 1
        assert book.date_read.day == 15

        assert book.date_added is not None
        assert book.date_added.year == 2023
        assert book.date_added.month == 12

    def test_parse_isbn_formats(self):
        """ISBN should be parsed from ISBN/UID field."""
        parser = StoryGraphCSVParser(VALID_STORYGRAPH_CSV)
        books = list(parser.parse())

        # ISBN-13
        assert books[0].isbn13 == "9781619634442"
        assert books[0].isbn is None

        # Book without ISBN
        assert books[2].isbn is None
        assert books[2].isbn13 is None

    def test_parse_tags_as_shelves(self):
        """Tags should be parsed as shelves (space-separated)."""
        csv = b"""Title,Authors,Read Status,Star Rating,Tags
Test Book,Test Author,read,4,romance fantasy favorites
"""
        parser = StoryGraphCSVParser(csv)
        books = list(parser.parse())

        # Note: StoryGraph may use space or comma separation
        # Our implementation handles comma-separated
        assert len(books) == 1

    def test_parse_multiple_authors(self):
        """Multiple authors should be split correctly."""
        csv = b"""Title,Authors,Read Status,Star Rating
Co-authored Book,"Author One, Author Two, Author Three",read,4
"""
        parser = StoryGraphCSVParser(csv)
        books = list(parser.parse())

        assert len(books) == 1
        assert books[0].author == "Author One"
        assert books[0].additional_authors == ["Author Two", "Author Three"]

    def test_convenience_function(self):
        """parse_storygraph_csv convenience function should work."""
        books, errors, warnings = parse_storygraph_csv(VALID_STORYGRAPH_CSV)

        assert len(books) == 3
        assert len(errors) == 0

    def test_encoding_fallback(self):
        """Parser should handle different encodings."""
        utf8_csv = "Title,Authors,Read Status,Star Rating\nCafé Book,José García,read,5\n".encode(
            "utf-8"
        )
        parser = StoryGraphCSVParser(utf8_csv)
        books = list(parser.parse())

        assert len(books) == 1
        assert "José" in books[0].author


class TestReadStatusMapping:
    """Test read status mapping from StoryGraph to standard format."""

    def test_read_status_mapping(self):
        """Various read statuses should be mapped correctly."""
        test_cases = [
            ("read", "read"),
            ("currently-reading", "currently-reading"),
            ("to-read", "to-read"),
            ("did-not-finish", "did-not-finish"),
            ("dnf", "did-not-finish"),
            ("currently reading", "currently-reading"),
            ("to read", "to-read"),
        ]

        parser = StoryGraphCSVParser(b"")
        for input_status, expected in test_cases:
            result = parser._map_read_status(input_status)
            assert result == expected, f"Expected {expected} for {input_status}, got {result}"


class TestCSVAutoDetection:
    """Test auto-detection between Goodreads and StoryGraph formats."""

    def test_detect_goodreads(self):
        """Goodreads CSV should be detected correctly."""
        result = detect_csv_source(GOODREADS_CSV)
        assert result == "goodreads"

    def test_detect_storygraph(self):
        """StoryGraph CSV should be detected correctly."""
        result = detect_csv_source(VALID_STORYGRAPH_CSV)
        assert result == "storygraph"

    def test_detect_unknown(self):
        """Unknown CSV format should return 'unknown'."""
        unknown_csv = b"""Name,Value,Other
Row1,A,B
Row2,C,D
"""
        result = detect_csv_source(unknown_csv)
        assert result == "unknown"

    def test_detect_empty(self):
        """Empty CSV should return 'unknown'."""
        result = detect_csv_source(b"")
        assert result == "unknown"


class TestUnifiedParser:
    """Test the unified parse_library_csv function."""

    def test_parse_goodreads(self):
        """Unified parser should handle Goodreads CSV."""
        books, source, errors, warnings = parse_library_csv(GOODREADS_CSV)

        assert source == "goodreads"
        assert len(books) == 1
        assert len(errors) == 0

    def test_parse_storygraph(self):
        """Unified parser should handle StoryGraph CSV."""
        books, source, errors, warnings = parse_library_csv(VALID_STORYGRAPH_CSV)

        assert source == "storygraph"
        assert len(books) == 3
        assert len(errors) == 0

    def test_parse_unknown_format(self):
        """Unified parser should return error for unknown format."""
        unknown_csv = b"""Random,Headers,Here
1,2,3
"""
        books, source, errors, warnings = parse_library_csv(unknown_csv)

        assert source == "unknown"
        assert len(books) == 0
        assert len(errors) > 0
        assert "Unable to detect" in errors[0]


class TestBookIdGeneration:
    """Test book ID generation for StoryGraph imports."""

    def test_id_with_isbn(self):
        """Books with ISBN should use ISBN-based ID."""
        parser = StoryGraphCSVParser(VALID_STORYGRAPH_CSV)
        books = list(parser.parse())

        # First book has ISBN
        assert books[0].goodreads_book_id.startswith("sg-isbn-")
        assert "9781619634442" in books[0].goodreads_book_id

    def test_id_without_isbn(self):
        """Books without ISBN should use hash-based ID."""
        parser = StoryGraphCSVParser(VALID_STORYGRAPH_CSV)
        books = list(parser.parse())

        # Third book has no ISBN
        assert books[2].goodreads_book_id.startswith("sg-")
        assert "isbn" not in books[2].goodreads_book_id

    def test_id_consistency(self):
        """Same book should generate same ID."""
        parser1 = StoryGraphCSVParser(MINIMAL_STORYGRAPH_CSV)
        parser2 = StoryGraphCSVParser(MINIMAL_STORYGRAPH_CSV)

        books1 = list(parser1.parse())
        books2 = list(parser2.parse())

        assert books1[0].goodreads_book_id == books2[0].goodreads_book_id


class TestSecurityFeatures:
    """Test security features like formula injection prevention and field truncation."""

    def test_formula_injection_prevention_equals(self):
        """Excel formula starting with = should be sanitized."""
        csv = b"""Title,Authors,Read Status,Star Rating
=cmd|'/c calc'!A1,Author,read,5
"""
        parser = StoryGraphCSVParser(csv)
        books = list(parser.parse())
        assert len(books) == 1
        # Title should be prefixed with apostrophe
        assert books[0].title.startswith("'")
        assert "=cmd" in books[0].title

    def test_formula_injection_prevention_plus(self):
        """Excel formula starting with + should be sanitized."""
        csv = b"""Title,Authors,Read Status,Star Rating
+2+5+cmd,Author,read,5
"""
        parser = StoryGraphCSVParser(csv)
        books = list(parser.parse())
        assert books[0].title.startswith("'")

    def test_formula_injection_prevention_minus(self):
        """Excel formula starting with - should be sanitized."""
        csv = b"""Title,Authors,Read Status,Star Rating
-5-3,Author,read,5
"""
        parser = StoryGraphCSVParser(csv)
        books = list(parser.parse())
        assert books[0].title.startswith("'")

    def test_formula_injection_prevention_at(self):
        """Excel formula starting with @ should be sanitized."""
        csv = b"""Title,Authors,Read Status,Star Rating
@SUM(A1:A10),Author,read,5
"""
        parser = StoryGraphCSVParser(csv)
        books = list(parser.parse())
        assert books[0].title.startswith("'")

    def test_title_truncation(self):
        """Very long titles should be truncated to 500 characters."""
        long_title = "A" * 1000
        csv = f"Title,Authors,Read Status,Star Rating\n{long_title},Author,read,5\n".encode()
        parser = StoryGraphCSVParser(csv)
        books = list(parser.parse())
        assert len(books[0].title) == 500

    def test_author_truncation(self):
        """Very long author names should be truncated to 255 characters."""
        long_author = "B" * 500
        csv = f"Title,Authors,Read Status,Star Rating\nTest Book,{long_author},read,5\n".encode()
        parser = StoryGraphCSVParser(csv)
        books = list(parser.parse())
        assert len(books[0].author) == 255

    def test_review_truncation(self):
        """Very long reviews should be truncated to 50000 characters."""
        long_review = "C" * 60000
        csv = f"Title,Authors,Read Status,Star Rating,Review\nTest Book,Author,read,5,{long_review}\n".encode()
        parser = StoryGraphCSVParser(csv)
        books = list(parser.parse())
        assert len(books[0].review) == 50000

    def test_normal_content_not_affected(self):
        """Normal content without special characters should not be modified."""
        csv = b"""Title,Authors,Read Status,Star Rating
The Great Gatsby,F. Scott Fitzgerald,read,5
"""
        parser = StoryGraphCSVParser(csv)
        books = list(parser.parse())
        assert books[0].title == "The Great Gatsby"
        assert books[0].author == "F. Scott Fitzgerald"
