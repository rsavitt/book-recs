"""
Goodreads CSV parser.

Handles parsing and validation of Goodreads library export CSV files.
"""

import csv
import io
import re
from dataclasses import dataclass
from datetime import date
from typing import Iterator


# Maximum field lengths to prevent memory exhaustion
MAX_TITLE_LENGTH = 500
MAX_AUTHOR_LENGTH = 255
MAX_REVIEW_LENGTH = 50000
MAX_SHELF_LENGTH = 100


def sanitize_formula_injection(value: str) -> str:
    """
    Sanitize a string to prevent CSV/formula injection.

    Excel and other spreadsheet programs interpret cells starting with
    =, +, -, @, \t, or \r as formulas, which could execute arbitrary commands.
    """
    if value and value[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


def truncate_field(value: str, max_length: int) -> str:
    """Truncate a field to maximum length."""
    if len(value) > max_length:
        return value[:max_length]
    return value


@dataclass
class ParsedBook:
    """A single book entry parsed from a Goodreads CSV export."""

    goodreads_book_id: str
    title: str
    author: str
    author_last_first: str | None  # "Maas, Sarah J."
    additional_authors: list[str]
    isbn: str | None  # ISBN-10
    isbn13: str | None
    rating: int  # 0 = unrated, 1-5 = rated
    average_goodreads_rating: float | None
    publisher: str | None
    binding: str | None  # Hardcover, Paperback, Kindle, etc.
    page_count: int | None
    publication_year: int | None
    original_publication_year: int | None
    date_read: date | None
    date_added: date | None
    shelves: list[str]  # User's shelves/tags
    exclusive_shelf: str | None  # "read", "to-read", "currently-reading"
    review: str | None
    spoiler: bool
    private_notes: str | None

    # Computed fields
    series_name: str | None = None
    series_position: float | None = None


# Expected Goodreads CSV headers (core fields we need)
REQUIRED_HEADERS = ["Book Id", "Title", "Author", "My Rating"]

OPTIONAL_HEADERS = [
    "Author l-f",
    "Additional Authors",
    "ISBN",
    "ISBN13",
    "Average Rating",
    "Publisher",
    "Binding",
    "Number of Pages",
    "Year Published",
    "Original Publication Year",
    "Date Read",
    "Date Added",
    "Bookshelves",
    "Bookshelves with positions",
    "Exclusive Shelf",
    "My Review",
    "Spoiler",
    "Private Notes",
]


class GoodreadsCSVParser:
    """Parser for Goodreads library export CSV files."""

    def __init__(self, content: bytes):
        """
        Initialize parser with CSV content.

        Args:
            content: Raw bytes of the CSV file
        """
        self.content = content
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def validate(self) -> bool:
        """
        Validate that the content is a valid Goodreads export.

        Returns:
            True if valid, False otherwise. Check self.errors for details.
        """
        try:
            text = self._decode_content()
        except UnicodeDecodeError as e:
            self.errors.append(f"File encoding error: {e}")
            return False

        # Check for required headers
        reader = csv.DictReader(io.StringIO(text))
        if reader.fieldnames is None:
            self.errors.append("CSV file appears to be empty")
            return False

        missing_headers = [h for h in REQUIRED_HEADERS if h not in reader.fieldnames]
        if missing_headers:
            self.errors.append(
                f"Missing required headers: {', '.join(missing_headers)}. "
                "This doesn't appear to be a Goodreads export."
            )
            return False

        return True

    def parse(self) -> Iterator[ParsedBook]:
        """
        Parse the CSV and yield ParsedBook objects.

        Yields:
            ParsedBook objects for each valid row
        """
        text = self._decode_content()
        reader = csv.DictReader(io.StringIO(text))

        for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
            try:
                book = self._parse_row(row)
                if book:
                    yield book
            except Exception as e:
                self.warnings.append(f"Row {row_num}: Failed to parse - {e}")

    def _decode_content(self) -> str:
        """Decode CSV content, trying multiple encodings."""
        # Try UTF-8 first (most common)
        try:
            return self.content.decode("utf-8")
        except UnicodeDecodeError:
            pass

        # Try UTF-8 with BOM
        try:
            return self.content.decode("utf-8-sig")
        except UnicodeDecodeError:
            pass

        # Try Latin-1 as fallback (handles any byte sequence)
        return self.content.decode("latin-1")

    def _parse_row(self, row: dict) -> ParsedBook | None:
        """Parse a single CSV row into a ParsedBook."""
        # Skip if no book ID
        book_id = row.get("Book Id", "").strip()
        if not book_id:
            return None

        # Parse title and extract series info (with sanitization)
        raw_title = row.get("Title", "").strip()
        raw_title = sanitize_formula_injection(raw_title)
        raw_title = truncate_field(raw_title, MAX_TITLE_LENGTH)
        title, series_name, series_position = self._parse_title(raw_title)

        # Parse author (with sanitization)
        author = row.get("Author", "").strip()
        if not author:
            return None
        author = sanitize_formula_injection(author)
        author = truncate_field(author, MAX_AUTHOR_LENGTH)

        # Parse additional authors (with sanitization)
        additional_authors_str = row.get("Additional Authors", "")
        additional_authors = [
            truncate_field(sanitize_formula_injection(a.strip()), MAX_AUTHOR_LENGTH)
            for a in additional_authors_str.split(",")
            if a.strip()
        ]

        # Parse ISBNs (Goodreads wraps them in ="..." to preserve leading zeros)
        isbn = self._clean_isbn(row.get("ISBN", ""))
        isbn13 = self._clean_isbn(row.get("ISBN13", ""))

        # Parse rating (0 = unrated)
        rating = self._parse_int(row.get("My Rating", "0")) or 0

        # Parse dates
        date_read = self._parse_date(row.get("Date Read", ""))
        date_added = self._parse_date(row.get("Date Added", ""))

        # Parse shelves (with sanitization)
        shelves_str = row.get("Bookshelves", "")
        shelves = [
            truncate_field(sanitize_formula_injection(s.strip()), MAX_SHELF_LENGTH)
            for s in shelves_str.split(",")
            if s.strip()
        ]

        return ParsedBook(
            goodreads_book_id=book_id,
            title=title,
            author=author,
            author_last_first=row.get("Author l-f", "").strip() or None,
            additional_authors=additional_authors,
            isbn=isbn,
            isbn13=isbn13,
            rating=rating,
            average_goodreads_rating=self._parse_float(row.get("Average Rating", "")),
            publisher=row.get("Publisher", "").strip() or None,
            binding=row.get("Binding", "").strip() or None,
            page_count=self._parse_int(row.get("Number of Pages", "")),
            publication_year=self._parse_int(row.get("Year Published", "")),
            original_publication_year=self._parse_int(row.get("Original Publication Year", "")),
            date_read=date_read,
            date_added=date_added,
            shelves=shelves,
            exclusive_shelf=row.get("Exclusive Shelf", "").strip() or None,
            review=self._sanitize_review(row.get("My Review", "")),
            spoiler=row.get("Spoiler", "").strip().lower() == "true",
            private_notes=row.get("Private Notes", "").strip() or None,
            series_name=series_name,
            series_position=series_position,
        )

    def _sanitize_review(self, review: str) -> str | None:
        """Sanitize and truncate review field."""
        review = review.strip()
        if not review:
            return None
        review = sanitize_formula_injection(review)
        return truncate_field(review, MAX_REVIEW_LENGTH)

    def _parse_title(self, raw_title: str) -> tuple[str, str | None, float | None]:
        """
        Parse title and extract series information.

        Examples:
            "A Court of Thorns and Roses (A Court of Thorns and Roses, #1)"
            -> ("A Court of Thorns and Roses", "A Court of Thorns and Roses", 1.0)

            "Fourth Wing (The Empyrean, #1)"
            -> ("Fourth Wing", "The Empyrean", 1.0)

            "The Cruel Prince (The Folk of the Air, #1)"
            -> ("The Cruel Prince", "The Folk of the Air", 1.0)

        Returns:
            Tuple of (clean_title, series_name, series_position)
        """
        # Pattern: "Title (Series Name, #N)" or "Title (Series Name #N)"
        series_pattern = r"^(.+?)\s*\(([^,]+),?\s*#?([\d.]+)\)\s*$"
        match = re.match(series_pattern, raw_title)

        if match:
            title = match.group(1).strip()
            series_name = match.group(2).strip()
            try:
                series_position = float(match.group(3))
            except ValueError:
                series_position = None
            return title, series_name, series_position

        # No series info found
        return raw_title, None, None

    def _clean_isbn(self, isbn_str: str) -> str | None:
        """
        Clean ISBN from Goodreads format.

        Goodreads exports ISBNs as ="0123456789" to prevent Excel from
        treating them as numbers.
        """
        if not isbn_str:
            return None

        # Remove ="..." wrapper
        cleaned = isbn_str.strip().strip('="').strip('"')

        # Remove any non-alphanumeric characters (hyphens, spaces)
        cleaned = re.sub(r"[^0-9Xx]", "", cleaned)

        if not cleaned:
            return None

        # Validate length
        if len(cleaned) not in (10, 13):
            return None

        return cleaned

    def _parse_date(self, date_str: str) -> date | None:
        """Parse date from various formats."""
        if not date_str or not date_str.strip():
            return None

        date_str = date_str.strip()

        # Try common formats
        formats = [
            "%Y/%m/%d",  # 2024/01/15
            "%Y-%m-%d",  # 2024-01-15
            "%m/%d/%Y",  # 01/15/2024
            "%m/%d/%y",  # 01/15/24
            "%b %d, %Y",  # Jan 15, 2024
            "%B %d, %Y",  # January 15, 2024
        ]

        for fmt in formats:
            try:
                from datetime import datetime
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        return None

    def _parse_int(self, value: str) -> int | None:
        """Parse integer, returning None for empty/invalid values."""
        if not value or not value.strip():
            return None
        try:
            return int(value.strip())
        except ValueError:
            return None

    def _parse_float(self, value: str) -> float | None:
        """Parse float, returning None for empty/invalid values."""
        if not value or not value.strip():
            return None
        try:
            return float(value.strip())
        except ValueError:
            return None


def parse_goodreads_csv(content: bytes) -> tuple[list[ParsedBook], list[str], list[str]]:
    """
    Convenience function to parse a Goodreads CSV export.

    Args:
        content: Raw bytes of the CSV file

    Returns:
        Tuple of (books, errors, warnings)
    """
    parser = GoodreadsCSVParser(content)

    if not parser.validate():
        return [], parser.errors, parser.warnings

    books = list(parser.parse())
    return books, parser.errors, parser.warnings


def detect_csv_source(content: bytes) -> str:
    """
    Detect whether a CSV file is from Goodreads or StoryGraph.

    Args:
        content: Raw bytes of the CSV file

    Returns:
        "goodreads", "storygraph", or "unknown"
    """
    # Try to decode the content
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = content.decode("latin-1")

    # Read just the headers
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        return "unknown"

    headers = set(reader.fieldnames)

    # Goodreads-specific headers
    goodreads_indicators = {"Book Id", "My Rating", "Exclusive Shelf", "Bookshelves"}

    # StoryGraph-specific headers
    storygraph_indicators = {"Read Status", "Star Rating", "ISBN/UID", "Moods", "Pace"}

    has_goodreads = bool(headers & goodreads_indicators)
    has_storygraph = bool(headers & storygraph_indicators)

    if has_goodreads and not has_storygraph:
        return "goodreads"
    elif has_storygraph and not has_goodreads:
        return "storygraph"
    elif has_goodreads and has_storygraph:
        # Unlikely, but prefer Goodreads if both match
        return "goodreads"
    else:
        return "unknown"


def parse_library_csv(
    content: bytes,
) -> tuple[list[ParsedBook], str, list[str], list[str]]:
    """
    Parse a library CSV export, auto-detecting the source.

    Supports both Goodreads and StoryGraph exports.

    Args:
        content: Raw bytes of the CSV file

    Returns:
        Tuple of (books, source, errors, warnings)
        where source is "goodreads", "storygraph", or "unknown"
    """
    source = detect_csv_source(content)

    if source == "goodreads":
        parser = GoodreadsCSVParser(content)
        if not parser.validate():
            return [], source, parser.errors, parser.warnings
        books = list(parser.parse())
        return books, source, parser.errors, parser.warnings

    elif source == "storygraph":
        # Import here to avoid circular imports
        from app.services.storygraph_parser import StoryGraphCSVParser

        parser = StoryGraphCSVParser(content)
        if not parser.validate():
            return [], source, parser.errors, parser.warnings
        books = list(parser.parse())
        return books, source, parser.errors, parser.warnings

    else:
        return [], source, ["Unable to detect CSV format. Please upload a Goodreads or StoryGraph export."], []
