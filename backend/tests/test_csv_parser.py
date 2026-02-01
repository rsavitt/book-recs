"""Tests for Goodreads CSV parser."""

import pytest
from app.services.csv_parser import GoodreadsCSVParser, parse_goodreads_csv


# Sample Goodreads CSV content
VALID_CSV = b"""Book Id,Title,Author,Author l-f,Additional Authors,ISBN,ISBN13,My Rating,Average Rating,Publisher,Binding,Number of Pages,Year Published,Original Publication Year,Date Read,Date Added,Bookshelves,Bookshelves with positions,Exclusive Shelf,My Review,Spoiler,Private Notes
12345,A Court of Thorns and Roses (A Court of Thorns and Roses #1),Sarah J. Maas,"Maas, Sarah J.",,="1619634449",="9781619634442",5,4.25,Bloomsbury Publishing,Paperback,432,2015,2015,2024/01/15,2023/12/01,"romantasy, fae, favorites","romantasy (#1), fae (#2), favorites (#3)",read,Great book!,false,
67890,Fourth Wing (The Empyrean #1),Rebecca Yarros,"Yarros, Rebecca",,="1649374046",="9781649374042",4,4.56,Red Tower Books,Hardcover,528,2023,2023,2024/02/20,2024/01/10,romantasy,romantasy (#1),read,,false,
11111,The Cruel Prince (The Folk of the Air #1),Holly Black,"Black, Holly",,,,3,4.05,Little Brown Books,Paperback,370,2018,2018,,,to-read,to-read (#1),to-read,,false,
"""

MINIMAL_CSV = b"""Book Id,Title,Author,My Rating
99999,Test Book,Test Author,4
"""

INVALID_CSV = b"""Wrong,Headers,Here
1,2,3
"""

EMPTY_CSV = b""


class TestGoodreadsCSVParser:
    """Test cases for GoodreadsCSVParser."""

    def test_validate_valid_csv(self):
        """Valid Goodreads CSV should pass validation."""
        parser = GoodreadsCSVParser(VALID_CSV)
        assert parser.validate() is True
        assert len(parser.errors) == 0

    def test_validate_minimal_csv(self):
        """Minimal CSV with required headers should pass."""
        parser = GoodreadsCSVParser(MINIMAL_CSV)
        assert parser.validate() is True

    def test_validate_invalid_headers(self):
        """CSV with wrong headers should fail validation."""
        parser = GoodreadsCSVParser(INVALID_CSV)
        assert parser.validate() is False
        assert len(parser.errors) > 0
        assert "Missing required headers" in parser.errors[0]

    def test_validate_empty_csv(self):
        """Empty CSV should fail validation."""
        parser = GoodreadsCSVParser(EMPTY_CSV)
        assert parser.validate() is False

    def test_parse_full_record(self):
        """Parse a full Goodreads record with all fields."""
        parser = GoodreadsCSVParser(VALID_CSV)
        assert parser.validate()

        books = list(parser.parse())
        assert len(books) == 3

        # Check first book (ACOTAR)
        book = books[0]
        assert book.goodreads_book_id == "12345"
        assert book.title == "A Court of Thorns and Roses"
        assert book.author == "Sarah J. Maas"
        assert book.isbn == "1619634449"
        assert book.isbn13 == "9781619634442"
        assert book.rating == 5
        assert book.page_count == 432
        assert book.publication_year == 2015
        assert book.series_name == "A Court of Thorns and Roses"
        assert book.series_position == 1.0
        assert "romantasy" in book.shelves
        assert "fae" in book.shelves
        assert book.exclusive_shelf == "read"

    def test_parse_series_extraction(self):
        """Series name and position should be extracted from title."""
        parser = GoodreadsCSVParser(VALID_CSV)
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

    def test_parse_isbn_cleaning(self):
        """ISBNs should be cleaned of Goodreads formatting."""
        parser = GoodreadsCSVParser(VALID_CSV)
        books = list(parser.parse())

        book = books[0]
        # Should remove ="..." wrapper
        assert book.isbn == "1619634449"
        assert book.isbn13 == "9781619634442"

    def test_parse_date_formats(self):
        """Various date formats should be parsed correctly."""
        parser = GoodreadsCSVParser(VALID_CSV)
        books = list(parser.parse())

        book = books[0]
        assert book.date_read is not None
        assert book.date_read.year == 2024
        assert book.date_read.month == 1
        assert book.date_read.day == 15

    def test_parse_unrated_book(self):
        """Unrated books (rating=0) should be handled."""
        csv_with_unrated = b"""Book Id,Title,Author,My Rating,Exclusive Shelf
12345,Unread Book,Some Author,0,to-read
"""
        parser = GoodreadsCSVParser(csv_with_unrated)
        books = list(parser.parse())

        assert len(books) == 1
        assert books[0].rating == 0
        assert books[0].exclusive_shelf == "to-read"

    def test_parse_missing_isbn(self):
        """Books without ISBNs should be parsed."""
        csv_no_isbn = b"""Book Id,Title,Author,My Rating,ISBN,ISBN13
12345,No ISBN Book,Some Author,4,,
"""
        parser = GoodreadsCSVParser(csv_no_isbn)
        books = list(parser.parse())

        assert len(books) == 1
        assert books[0].isbn is None
        assert books[0].isbn13 is None

    def test_parse_encoding_fallback(self):
        """Parser should handle different encodings."""
        # UTF-8 with special characters
        utf8_csv = "Book Id,Title,Author,My Rating\n1,Café Book,José García,5\n".encode("utf-8")
        parser = GoodreadsCSVParser(utf8_csv)
        books = list(parser.parse())
        assert len(books) == 1
        assert "José" in books[0].author

    def test_convenience_function(self):
        """parse_goodreads_csv convenience function should work."""
        books, errors, warnings = parse_goodreads_csv(VALID_CSV)

        assert len(books) == 3
        assert len(errors) == 0


class TestTitleParsing:
    """Test series extraction from titles."""

    def test_standard_series_format(self):
        """Standard format: Title (Series, #N)."""
        parser = GoodreadsCSVParser(b"")
        title, series, pos = parser._parse_title(
            "A Court of Thorns and Roses (A Court of Thorns and Roses, #1)"
        )
        assert title == "A Court of Thorns and Roses"
        assert series == "A Court of Thorns and Roses"
        assert pos == 1.0

    def test_series_without_comma(self):
        """Format without comma: Title (Series #N)."""
        parser = GoodreadsCSVParser(b"")
        title, series, pos = parser._parse_title("Fourth Wing (The Empyrean #1)")
        assert title == "Fourth Wing"
        assert series == "The Empyrean"
        assert pos == 1.0

    def test_decimal_series_position(self):
        """Novella with decimal position: Title (Series, #1.5)."""
        parser = GoodreadsCSVParser(b"")
        title, series, pos = parser._parse_title("A Court of Frost and Starlight (ACOTAR, #3.1)")
        assert title == "A Court of Frost and Starlight"
        assert series == "ACOTAR"
        assert pos == 3.1

    def test_no_series(self):
        """Standalone book without series info."""
        parser = GoodreadsCSVParser(b"")
        title, series, pos = parser._parse_title("The House in the Cerulean Sea")
        assert title == "The House in the Cerulean Sea"
        assert series is None
        assert pos is None

    def test_parentheses_in_title(self):
        """Title with parentheses that aren't series info."""
        parser = GoodreadsCSVParser(b"")
        # This should NOT be parsed as series
        title, series, pos = parser._parse_title("Book Title (Not a Series)")
        assert title == "Book Title (Not a Series)"
        assert series is None


class TestISBNCleaning:
    """Test ISBN cleaning and validation."""

    def test_clean_goodreads_format(self):
        """Remove Goodreads =\"...\" wrapper."""
        parser = GoodreadsCSVParser(b"")
        assert parser._clean_isbn('="9781619634442"') == "9781619634442"
        assert parser._clean_isbn('="1619634449"') == "1619634449"

    def test_clean_with_hyphens(self):
        """Remove hyphens from ISBN."""
        parser = GoodreadsCSVParser(b"")
        assert parser._clean_isbn("978-1-61963-444-2") == "9781619634442"

    def test_invalid_length(self):
        """Invalid ISBN length should return None."""
        parser = GoodreadsCSVParser(b"")
        assert parser._clean_isbn("12345") is None
        assert parser._clean_isbn("12345678901234") is None

    def test_empty_isbn(self):
        """Empty ISBN should return None."""
        parser = GoodreadsCSVParser(b"")
        assert parser._clean_isbn("") is None
        assert parser._clean_isbn('=""') is None
