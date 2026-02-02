"""
StoryGraph CSV parser.

Handles parsing and validation of StoryGraph library export CSV files.
"""

import csv
import io
import math
import re
from datetime import date, datetime

from app.services.csv_parser import ParsedBook


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


def truncate_field(value: str, max_length: int, field_name: str = "") -> str:
    """Truncate a field to maximum length with warning."""
    if len(value) > max_length:
        return value[:max_length]
    return value


# StoryGraph CSV headers
# Title, Authors, Contributors, ISBN/UID, Format, Read Status, Date Added,
# Last Date Read, Dates Read, Read Count, Moods, Pace, Character- or Plot-Driven?,
# Strong Character Development?, Loveable Characters?, Diverse Characters?,
# Flawed Characters?, Star Rating, Review, Content Warnings,
# Content Warning Description, Tags, Owned?

REQUIRED_HEADERS = ["Title"]  # Minimal requirement

# Headers that indicate this is a StoryGraph export
STORYGRAPH_INDICATORS = ["Read Status", "Star Rating", "ISBN/UID", "Moods", "Pace"]


class StoryGraphCSVParser:
    """Parser for StoryGraph library export CSV files."""

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
        Validate that the content is a valid StoryGraph export.

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
                "This doesn't appear to be a valid library export."
            )
            return False

        # Check for StoryGraph-specific headers
        has_storygraph_header = any(
            h in reader.fieldnames for h in STORYGRAPH_INDICATORS
        )
        if not has_storygraph_header:
            self.errors.append(
                "This doesn't appear to be a StoryGraph export. "
                "Missing expected StoryGraph headers like 'Read Status' or 'Star Rating'."
            )
            return False

        return True

    def parse(self):
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
        # Get title
        raw_title = row.get("Title", "").strip()
        if not raw_title:
            return None

        # Sanitize and truncate title
        raw_title = sanitize_formula_injection(raw_title)
        raw_title = truncate_field(raw_title, MAX_TITLE_LENGTH, "title")

        # Parse title and extract series info
        title, series_name, series_position = self._parse_title(raw_title)

        # Parse author - StoryGraph uses "Authors" (plural) or sometimes "Author"
        author = row.get("Authors", "").strip() or row.get("Author", "").strip()
        if not author:
            return None

        # Sanitize and truncate author
        author = sanitize_formula_injection(author)
        author = truncate_field(author, MAX_AUTHOR_LENGTH, "author")

        # StoryGraph may have multiple authors separated by commas
        # Take the first one as primary author
        authors_list = [a.strip() for a in author.split(",") if a.strip()]
        primary_author = authors_list[0] if authors_list else author
        additional_authors = authors_list[1:] if len(authors_list) > 1 else []

        # Parse ISBN - StoryGraph uses "ISBN/UID" without the ="..." wrapper
        isbn_uid = row.get("ISBN/UID", "").strip()
        isbn, isbn13 = self._parse_isbn_uid(isbn_uid)

        # Parse rating - StoryGraph uses float (0.0-5.0), convert to int (0-5)
        rating = self._parse_rating(row.get("Star Rating", ""))

        # Parse dates - StoryGraph uses YYYY/MM/DD format
        date_read = self._parse_date(row.get("Last Date Read", ""))
        date_added = self._parse_date(row.get("Date Added", ""))

        # Parse read status - map StoryGraph values to Goodreads equivalents
        read_status = self._map_read_status(row.get("Read Status", "").strip())

        # Parse tags (equivalent to shelves) - sanitize and limit length
        tags_str = row.get("Tags", "")
        tags = [
            truncate_field(sanitize_formula_injection(t.strip()), MAX_SHELF_LENGTH)
            for t in tags_str.split(",")
            if t.strip()
        ]

        # Generate a pseudo book ID from ISBN or title+author hash
        book_id = self._generate_book_id(isbn13 or isbn, title, primary_author)

        # Sanitize and truncate review
        review = row.get("Review", "").strip() or None
        if review:
            review = sanitize_formula_injection(review)
            review = truncate_field(review, MAX_REVIEW_LENGTH)

        return ParsedBook(
            goodreads_book_id=book_id,  # Using this field for compatibility
            title=title,
            author=primary_author,
            author_last_first=None,  # StoryGraph doesn't provide this
            additional_authors=additional_authors,
            isbn=isbn,
            isbn13=isbn13,
            rating=rating,
            average_goodreads_rating=None,  # StoryGraph doesn't provide this
            publisher=None,  # StoryGraph doesn't provide this
            binding=row.get("Format", "").strip() or None,
            page_count=None,  # StoryGraph doesn't provide this
            publication_year=None,  # StoryGraph doesn't provide this
            original_publication_year=None,  # StoryGraph doesn't provide this
            date_read=date_read,
            date_added=date_added,
            shelves=tags,
            exclusive_shelf=read_status,
            review=review,
            spoiler=False,  # StoryGraph doesn't have this field
            private_notes=None,  # StoryGraph doesn't have this
            series_name=series_name,
            series_position=series_position,
        )

    def _parse_title(self, raw_title: str) -> tuple[str, str | None, float | None]:
        """
        Parse title and extract series information.

        StoryGraph titles may include series info in various formats:
        - "Title (Series, #N)"
        - "Title (Series #N)"
        - "Title"

        Returns:
            Tuple of (clean_title, series_name, series_position)
        """
        # Pattern 1: "Title (Series Name, #N)" - with comma
        series_pattern_comma = r"^(.+?)\s*\((.+?),\s*#?([\d.]+)\)\s*$"
        match = re.match(series_pattern_comma, raw_title)

        if match:
            title = match.group(1).strip()
            series_name = match.group(2).strip()
            try:
                series_position = float(match.group(3))
            except ValueError:
                series_position = None
            return title, series_name, series_position

        # Pattern 2: "Title (Series Name #N)" - without comma, # as delimiter
        series_pattern_hash = r"^(.+?)\s*\((.+?)\s+#([\d.]+)\)\s*$"
        match = re.match(series_pattern_hash, raw_title)

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

    def _parse_isbn_uid(self, isbn_uid: str) -> tuple[str | None, str | None]:
        """
        Parse ISBN/UID field from StoryGraph.

        StoryGraph doesn't use the ="..." wrapper that Goodreads uses.
        The field may contain ISBN-10, ISBN-13, or a UID.

        Returns:
            Tuple of (isbn10, isbn13)
        """
        if not isbn_uid:
            return None, None

        # Clean up the value
        cleaned = re.sub(r"[^0-9Xx]", "", isbn_uid)

        if not cleaned:
            return None, None

        if len(cleaned) == 13:
            return None, cleaned
        elif len(cleaned) == 10:
            return cleaned, None

        # Invalid length - might be a StoryGraph UID, ignore
        return None, None

    def _parse_rating(self, rating_str: str) -> int:
        """
        Parse StoryGraph rating (0.0-5.0 float) to integer (0-5).

        Uses ceiling to round up (e.g., 3.5 -> 4).
        Returns 0 for unrated.
        """
        if not rating_str or not rating_str.strip():
            return 0

        try:
            float_rating = float(rating_str.strip())
            if float_rating <= 0:
                return 0
            # Round up using ceiling
            return min(5, math.ceil(float_rating))
        except ValueError:
            return 0

    def _parse_date(self, date_str: str) -> date | None:
        """Parse date from StoryGraph format (YYYY/MM/DD)."""
        if not date_str or not date_str.strip():
            return None

        date_str = date_str.strip()

        # StoryGraph primarily uses YYYY/MM/DD
        formats = [
            "%Y/%m/%d",  # 2024/01/15
            "%Y-%m-%d",  # 2024-01-15
            "%m/%d/%Y",  # 01/15/2024
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        return None

    def _map_read_status(self, status: str) -> str | None:
        """
        Map StoryGraph read status to Goodreads-compatible values.

        StoryGraph uses:
        - "read"
        - "currently-reading"
        - "to-read"
        - "did-not-finish"

        We map these to our standard format (without hyphens for consistency).
        """
        if not status:
            return None

        status_lower = status.lower().strip()

        status_map = {
            "read": "read",
            "currently-reading": "currently-reading",
            "currently reading": "currently-reading",
            "to-read": "to-read",
            "to read": "to-read",
            "did-not-finish": "did-not-finish",
            "did not finish": "did-not-finish",
            "dnf": "did-not-finish",
        }

        return status_map.get(status_lower, status_lower)

    def _generate_book_id(
        self, isbn: str | None, title: str, author: str
    ) -> str:
        """
        Generate a consistent book ID for StoryGraph imports.

        Uses ISBN if available, otherwise creates a hash from title+author.
        Prefixed with 'sg-' to distinguish from Goodreads IDs.
        """
        if isbn:
            return f"sg-isbn-{isbn}"

        # Create a simple hash from title and author
        combined = f"{title.lower()}|{author.lower()}"
        # Use a simple hash
        hash_val = hash(combined) & 0xFFFFFFFF  # Keep positive
        return f"sg-{hash_val}"


def parse_storygraph_csv(
    content: bytes,
) -> tuple[list[ParsedBook], list[str], list[str]]:
    """
    Convenience function to parse a StoryGraph CSV export.

    Args:
        content: Raw bytes of the CSV file

    Returns:
        Tuple of (books, errors, warnings)
    """
    parser = StoryGraphCSVParser(content)

    if not parser.validate():
        return [], parser.errors, parser.warnings

    books = list(parser.parse())
    return books, parser.errors, parser.warnings
