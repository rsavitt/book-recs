"""Tests for book deduplication service."""

import pytest
from unittest.mock import MagicMock, patch

from app.services.book_dedup import BookDeduplicator
from app.services.csv_parser import ParsedBook


class TestBookDeduplicator:
    """Test cases for BookDeduplicator."""

    def test_normalize_title_basic(self):
        """Basic title normalization."""
        assert BookDeduplicator._normalize_title("The Book Title") == "book title"
        assert BookDeduplicator._normalize_title("A Great Book") == "great book"
        assert BookDeduplicator._normalize_title("An Example") == "example"

    def test_normalize_title_punctuation(self):
        """Punctuation should be removed."""
        assert BookDeduplicator._normalize_title("Book: A Subtitle") == "book a subtitle"
        assert BookDeduplicator._normalize_title("Book's Title!") == "books title"

    def test_normalize_title_unicode(self):
        """Unicode characters should be normalized."""
        assert BookDeduplicator._normalize_title("Café") == "cafe"
        assert BookDeduplicator._normalize_title("Naïve") == "naive"

    def test_normalize_author_basic(self):
        """Basic author normalization."""
        assert BookDeduplicator._normalize_author("Sarah J. Maas") == "sarah maas"
        assert BookDeduplicator._normalize_author("J.K. Rowling") == "rowling"
        assert BookDeduplicator._normalize_author("J. R. R. Tolkien") == "tolkien"

    def test_normalize_author_unicode(self):
        """Unicode in author names."""
        assert BookDeduplicator._normalize_author("José García") == "jose garcia"

    def test_string_similarity_identical(self):
        """Identical strings should have similarity 1.0."""
        assert BookDeduplicator._string_similarity("test", "test") == 1.0
        assert BookDeduplicator._string_similarity("", "") == 1.0

    def test_string_similarity_different(self):
        """Completely different strings should have low similarity."""
        sim = BookDeduplicator._string_similarity("abc", "xyz")
        assert sim < 0.5

    def test_string_similarity_similar(self):
        """Similar strings should have high similarity."""
        sim = BookDeduplicator._string_similarity("fourth wing", "fourth wings")
        assert sim > 0.85

    def test_string_similarity_empty(self):
        """Empty string comparisons."""
        assert BookDeduplicator._string_similarity("", "test") == 0.0
        assert BookDeduplicator._string_similarity("test", "") == 0.0


class TestParsedBookFactory:
    """Helper to create ParsedBook instances for testing."""

    @staticmethod
    def create(
        goodreads_book_id: str = "12345",
        title: str = "Test Book",
        author: str = "Test Author",
        isbn: str | None = None,
        isbn13: str | None = None,
        rating: int = 4,
        **kwargs,
    ) -> ParsedBook:
        defaults = {
            "author_last_first": None,
            "additional_authors": [],
            "average_goodreads_rating": 4.0,
            "publisher": None,
            "binding": None,
            "page_count": None,
            "publication_year": None,
            "original_publication_year": None,
            "date_read": None,
            "date_added": None,
            "shelves": [],
            "exclusive_shelf": "read",
            "review": None,
            "spoiler": False,
            "private_notes": None,
            "series_name": None,
            "series_position": None,
        }
        defaults.update(kwargs)

        return ParsedBook(
            goodreads_book_id=goodreads_book_id,
            title=title,
            author=author,
            isbn=isbn,
            isbn13=isbn13,
            rating=rating,
            **defaults,
        )


class TestDeduplicationLogic:
    """Test deduplication matching logic."""

    def test_create_new_book_when_no_match(self):
        """When no match exists, a new book should be created."""
        # Create a mock session that returns no matches
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        deduplicator = BookDeduplicator(mock_db)
        parsed = TestParsedBookFactory.create(
            title="Brand New Book",
            author="New Author",
            isbn13="9781234567890",
        )

        result = deduplicator.find_or_create(parsed)

        assert result.is_new_book is True
        assert result.is_new_edition is True
        assert result.match_method == "new"

    def test_match_by_isbn13(self):
        """Books should match on ISBN-13."""
        # Create mock book that will be "found"
        mock_book = MagicMock()
        mock_book.id = 1

        mock_db = MagicMock()
        # First query (ISBN-13 on books table) returns a match
        mock_db.query.return_value.filter.return_value.first.return_value = mock_book

        deduplicator = BookDeduplicator(mock_db)
        parsed = TestParsedBookFactory.create(
            isbn13="9781619634442",
        )

        result = deduplicator.find_or_create(parsed)

        assert result.is_new_book is False
        assert result.match_method == "isbn13"

    def test_parsed_book_with_series(self):
        """ParsedBook should properly store series info."""
        parsed = TestParsedBookFactory.create(
            title="A Court of Thorns and Roses",
            series_name="A Court of Thorns and Roses",
            series_position=1.0,
        )

        assert parsed.series_name == "A Court of Thorns and Roses"
        assert parsed.series_position == 1.0
