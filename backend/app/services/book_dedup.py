"""
Book deduplication and normalization service.

Handles matching imported books to existing canonical records,
creating new records when needed, and normalizing metadata.
"""

import re
import unicodedata
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.models.book import Book, BookEdition
from app.services.csv_parser import ParsedBook


@dataclass
class DeduplicationResult:
    """Result of attempting to deduplicate a book."""

    book: Book
    edition: BookEdition
    is_new_book: bool
    is_new_edition: bool
    match_method: str  # "isbn13", "isbn10", "goodreads_id", "fuzzy_title_author"


class BookDeduplicator:
    """Service for deduplicating and normalizing book records."""

    # Threshold for fuzzy matching (0-1, higher = stricter)
    FUZZY_THRESHOLD = 0.85

    def __init__(self, db: Session):
        self.db = db

    def find_or_create(self, parsed: ParsedBook) -> DeduplicationResult:
        """
        Find an existing book record or create a new one.

        Matching priority:
        1. ISBN-13 (most reliable)
        2. ISBN-10
        3. Goodreads Book ID (edition-specific)
        4. Fuzzy title + author match

        Args:
            parsed: ParsedBook from CSV parser

        Returns:
            DeduplicationResult with the matched/created book and edition
        """
        # Try ISBN-13 match first
        if parsed.isbn13:
            result = self._match_by_isbn13(parsed)
            if result:
                return result

        # Try ISBN-10 match
        if parsed.isbn:
            result = self._match_by_isbn10(parsed)
            if result:
                return result

        # Try Goodreads ID match (checks editions)
        result = self._match_by_goodreads_id(parsed)
        if result:
            return result

        # Try fuzzy title + author match
        result = self._match_by_fuzzy_title_author(parsed)
        if result:
            return result

        # No match found - create new book and edition
        return self._create_new_book(parsed)

    def _match_by_isbn13(self, parsed: ParsedBook) -> DeduplicationResult | None:
        """Try to match by ISBN-13."""
        # Check canonical books first
        book = self.db.query(Book).filter(Book.isbn_13 == parsed.isbn13).first()
        if book:
            edition = self._find_or_create_edition(book, parsed)
            return DeduplicationResult(
                book=book,
                edition=edition,
                is_new_book=False,
                is_new_edition=edition.id is None,
                match_method="isbn13",
            )

        # Check editions
        edition = self.db.query(BookEdition).filter(BookEdition.isbn_13 == parsed.isbn13).first()
        if edition:
            return DeduplicationResult(
                book=edition.book,
                edition=edition,
                is_new_book=False,
                is_new_edition=False,
                match_method="isbn13",
            )

        return None

    def _match_by_isbn10(self, parsed: ParsedBook) -> DeduplicationResult | None:
        """Try to match by ISBN-10."""
        book = self.db.query(Book).filter(Book.isbn_10 == parsed.isbn).first()
        if book:
            edition = self._find_or_create_edition(book, parsed)
            return DeduplicationResult(
                book=book,
                edition=edition,
                is_new_book=False,
                is_new_edition=edition.id is None,
                match_method="isbn10",
            )

        edition = self.db.query(BookEdition).filter(BookEdition.isbn_10 == parsed.isbn).first()
        if edition:
            return DeduplicationResult(
                book=edition.book,
                edition=edition,
                is_new_book=False,
                is_new_edition=False,
                match_method="isbn10",
            )

        return None

    def _match_by_goodreads_id(self, parsed: ParsedBook) -> DeduplicationResult | None:
        """Try to match by Goodreads Book ID."""
        edition = (
            self.db.query(BookEdition)
            .filter(BookEdition.goodreads_book_id == parsed.goodreads_book_id)
            .first()
        )
        if edition:
            return DeduplicationResult(
                book=edition.book,
                edition=edition,
                is_new_book=False,
                is_new_edition=False,
                match_method="goodreads_id",
            )

        return None

    def _match_by_fuzzy_title_author(self, parsed: ParsedBook) -> DeduplicationResult | None:
        """Try to match by fuzzy title + author comparison."""
        normalized_title = self._normalize_title(parsed.title)
        normalized_author = self._normalize_author(parsed.author)

        # Query potential matches
        candidates = (
            self.db.query(Book)
            .filter(
                Book.author_normalized == normalized_author,
            )
            .all()
        )

        for candidate in candidates:
            candidate_title = self._normalize_title(candidate.title)
            similarity = self._string_similarity(normalized_title, candidate_title)

            if similarity >= self.FUZZY_THRESHOLD:
                edition = self._find_or_create_edition(candidate, parsed)
                return DeduplicationResult(
                    book=candidate,
                    edition=edition,
                    is_new_book=False,
                    is_new_edition=edition.id is None,
                    match_method="fuzzy_title_author",
                )

        return None

    def _create_new_book(self, parsed: ParsedBook) -> DeduplicationResult:
        """Create a new canonical book record and edition."""
        book = Book(
            title=parsed.title,
            author=parsed.author,
            author_normalized=self._normalize_author(parsed.author),
            isbn_13=parsed.isbn13,
            isbn_10=parsed.isbn,
            page_count=parsed.page_count,
            publication_year=parsed.original_publication_year or parsed.publication_year,
            series_name=parsed.series_name,
            series_position=parsed.series_position,
            is_romantasy=False,  # Will be classified later
            romantasy_confidence=0.0,
        )
        self.db.add(book)
        self.db.flush()  # Get the ID

        edition = BookEdition(
            book_id=book.id,
            isbn_13=parsed.isbn13,
            isbn_10=parsed.isbn,
            goodreads_book_id=parsed.goodreads_book_id,
            title_variant=None,  # Same as canonical
            format=parsed.binding,
            publisher=parsed.publisher,
            publication_year=parsed.publication_year,
        )
        self.db.add(edition)

        return DeduplicationResult(
            book=book,
            edition=edition,
            is_new_book=True,
            is_new_edition=True,
            match_method="new",
        )

    def _find_or_create_edition(self, book: Book, parsed: ParsedBook) -> BookEdition:
        """Find existing edition or create a new one for a matched book."""
        # Check if this exact edition exists
        if parsed.goodreads_book_id:
            edition = (
                self.db.query(BookEdition)
                .filter(
                    BookEdition.book_id == book.id,
                    BookEdition.goodreads_book_id == parsed.goodreads_book_id,
                )
                .first()
            )
            if edition:
                return edition

        # Check by ISBN
        if parsed.isbn13:
            edition = (
                self.db.query(BookEdition)
                .filter(
                    BookEdition.book_id == book.id,
                    BookEdition.isbn_13 == parsed.isbn13,
                )
                .first()
            )
            if edition:
                return edition

        # Create new edition
        edition = BookEdition(
            book_id=book.id,
            isbn_13=parsed.isbn13,
            isbn_10=parsed.isbn,
            goodreads_book_id=parsed.goodreads_book_id,
            format=parsed.binding,
            publisher=parsed.publisher,
            publication_year=parsed.publication_year,
        )
        self.db.add(edition)

        return edition

    @staticmethod
    def _normalize_title(title: str) -> str:
        """
        Normalize a title for comparison.

        - Lowercase
        - Remove articles (the, a, an)
        - Remove punctuation
        - Normalize unicode
        - Collapse whitespace
        """
        # Normalize unicode
        title = unicodedata.normalize("NFKD", title)
        title = title.encode("ascii", "ignore").decode("ascii")

        # Lowercase
        title = title.lower()

        # Remove leading articles
        title = re.sub(r"^(the|a|an)\s+", "", title)

        # Remove punctuation
        title = re.sub(r"[^\w\s]", "", title)

        # Collapse whitespace
        title = re.sub(r"\s+", " ", title).strip()

        return title

    @staticmethod
    def _normalize_author(author: str) -> str:
        """
        Normalize an author name for comparison.

        - Lowercase
        - Remove middle initials
        - Remove punctuation
        - Normalize unicode
        """
        # Normalize unicode
        author = unicodedata.normalize("NFKD", author)
        author = author.encode("ascii", "ignore").decode("ascii")

        # Lowercase
        author = author.lower()

        # Remove single letter initials (J. K. Rowling -> Rowling)
        author = re.sub(r"\b[a-z]\.\s*", "", author)

        # Remove punctuation
        author = re.sub(r"[^\w\s]", "", author)

        # Collapse whitespace
        author = re.sub(r"\s+", " ", author).strip()

        return author

    @staticmethod
    def _string_similarity(s1: str, s2: str) -> float:
        """
        Calculate similarity between two strings using Levenshtein ratio.

        Returns a value between 0 (completely different) and 1 (identical).
        """
        if s1 == s2:
            return 1.0

        if not s1 or not s2:
            return 0.0

        # Use Levenshtein distance
        len1, len2 = len(s1), len(s2)
        if len1 < len2:
            s1, s2 = s2, s1
            len1, len2 = len2, len1

        # Early exit for very different lengths
        if len1 - len2 > len1 * 0.3:
            return 0.0

        # Calculate Levenshtein distance
        distances = range(len2 + 1)
        for i1, c1 in enumerate(s1):
            new_distances = [i1 + 1]
            for i2, c2 in enumerate(s2):
                if c1 == c2:
                    new_distances.append(distances[i2])
                else:
                    new_distances.append(
                        1 + min(distances[i2], distances[i2 + 1], new_distances[-1])
                    )
            distances = new_distances

        # Convert distance to similarity ratio
        max_len = max(len1, len2)
        return 1.0 - (distances[-1] / max_len)


def deduplicate_book(db: Session, parsed: ParsedBook) -> DeduplicationResult:
    """
    Convenience function to deduplicate a single book.

    Args:
        db: Database session
        parsed: ParsedBook from CSV parser

    Returns:
        DeduplicationResult
    """
    deduplicator = BookDeduplicator(db)
    return deduplicator.find_or_create(parsed)
