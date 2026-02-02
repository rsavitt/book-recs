"""
External API clients for book metadata enrichment.

Supports:
- Open Library API (covers, metadata, works)
- Google Books API (covers, metadata, descriptions)
"""

import asyncio
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import get_settings

settings = get_settings()


@dataclass
class BookMetadata:
    """Enriched book metadata from external APIs."""

    title: str | None = None
    author: str | None = None
    description: str | None = None
    cover_url: str | None = None
    page_count: int | None = None
    publication_year: int | None = None
    publisher: str | None = None
    subjects: list[str] | None = None
    open_library_id: str | None = None
    google_books_id: str | None = None


class OpenLibraryClient:
    """Client for Open Library API."""

    BASE_URL = "https://openlibrary.org"
    COVERS_URL = "https://covers.openlibrary.org"

    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=10.0,
            headers={"User-Agent": "RomantasyRecommender/1.0"},
        )

    async def close(self):
        await self.client.aclose()

    async def search_by_isbn(self, isbn: str) -> BookMetadata | None:
        """
        Search for a book by ISBN.

        Args:
            isbn: ISBN-10 or ISBN-13

        Returns:
            BookMetadata if found, None otherwise
        """
        try:
            response = await self.client.get(f"/isbn/{isbn}.json")
            if response.status_code != 200:
                return None

            data = response.json()
            return await self._parse_edition(data, isbn)

        except Exception:
            return None

    async def search_by_title_author(
        self, title: str, author: str
    ) -> BookMetadata | None:
        """
        Search for a book by title and author.

        Args:
            title: Book title
            author: Author name

        Returns:
            BookMetadata if found, None otherwise
        """
        try:
            response = await self.client.get(
                "/search.json",
                params={
                    "title": title,
                    "author": author,
                    "limit": 1,
                },
            )
            if response.status_code != 200:
                return None

            data = response.json()
            docs = data.get("docs", [])

            if not docs:
                return None

            doc = docs[0]
            return self._parse_search_result(doc)

        except Exception:
            return None

    async def _parse_edition(self, data: dict, isbn: str) -> BookMetadata:
        """Parse edition data from Open Library."""
        # Get work data for description
        description = None
        works = data.get("works", [])
        if works:
            work_key = works[0].get("key")
            if work_key:
                description = await self._get_work_description(work_key)

        # Build cover URL
        cover_url = None
        covers = data.get("covers", [])
        if covers:
            cover_id = covers[0]
            cover_url = f"{self.COVERS_URL}/b/id/{cover_id}-L.jpg"
        elif isbn:
            # Try ISBN-based cover URL
            cover_url = f"{self.COVERS_URL}/b/isbn/{isbn}-L.jpg"

        # Extract publication year
        publish_date = data.get("publish_date", "")
        publication_year = self._extract_year(publish_date)

        return BookMetadata(
            title=data.get("title"),
            description=description,
            cover_url=cover_url,
            page_count=data.get("number_of_pages"),
            publication_year=publication_year,
            publisher=self._first_or_none(data.get("publishers", [])),
            subjects=data.get("subjects", [])[:10],  # Limit subjects
            open_library_id=data.get("key", "").replace("/books/", ""),
        )

    def _parse_search_result(self, doc: dict) -> BookMetadata:
        """Parse search result from Open Library."""
        # Build cover URL from cover_i
        cover_url = None
        cover_i = doc.get("cover_i")
        if cover_i:
            cover_url = f"{self.COVERS_URL}/b/id/{cover_i}-L.jpg"

        return BookMetadata(
            title=doc.get("title"),
            author=self._first_or_none(doc.get("author_name", [])),
            cover_url=cover_url,
            publication_year=doc.get("first_publish_year"),
            subjects=doc.get("subject", [])[:10],
            open_library_id=doc.get("key", "").replace("/works/", ""),
        )

    async def _get_work_description(self, work_key: str) -> str | None:
        """Get description from work record."""
        try:
            response = await self.client.get(f"{work_key}.json")
            if response.status_code != 200:
                return None

            data = response.json()
            description = data.get("description")

            if isinstance(description, dict):
                return description.get("value")
            elif isinstance(description, str):
                return description

            return None

        except Exception:
            return None

    @staticmethod
    def _extract_year(date_str: str) -> int | None:
        """Extract year from a date string."""
        if not date_str:
            return None

        import re

        match = re.search(r"\b(19|20)\d{2}\b", date_str)
        if match:
            return int(match.group())
        return None

    @staticmethod
    def _first_or_none(lst: list) -> Any | None:
        """Return first element or None."""
        return lst[0] if lst else None


class GoogleBooksClient:
    """Client for Google Books API."""

    BASE_URL = "https://www.googleapis.com/books/v1"

    def __init__(self):
        self.api_key = settings.GOOGLE_BOOKS_API_KEY
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=10.0,
        )

    async def close(self):
        await self.client.aclose()

    async def search_by_isbn(self, isbn: str) -> BookMetadata | None:
        """
        Search for a book by ISBN.

        Args:
            isbn: ISBN-10 or ISBN-13

        Returns:
            BookMetadata if found, None otherwise
        """
        return await self._search(f"isbn:{isbn}")

    async def search_by_title_author(
        self, title: str, author: str
    ) -> BookMetadata | None:
        """
        Search for a book by title and author.

        Args:
            title: Book title
            author: Author name

        Returns:
            BookMetadata if found, None otherwise
        """
        query = f'intitle:"{title}" inauthor:"{author}"'
        return await self._search(query)

    async def _search(self, query: str) -> BookMetadata | None:
        """Execute a search query."""
        try:
            params = {"q": query, "maxResults": 1}
            if self.api_key:
                params["key"] = self.api_key

            response = await self.client.get("/volumes", params=params)
            if response.status_code != 200:
                return None

            data = response.json()
            items = data.get("items", [])

            if not items:
                return None

            return self._parse_volume(items[0])

        except Exception:
            return None

    def _parse_volume(self, item: dict) -> BookMetadata:
        """Parse a volume item from Google Books."""
        volume_info = item.get("volumeInfo", {})

        # Get cover URL (prefer larger images)
        cover_url = None
        image_links = volume_info.get("imageLinks", {})
        for size in ["large", "medium", "small", "thumbnail"]:
            if size in image_links:
                cover_url = image_links[size]
                # Convert to HTTPS
                if cover_url.startswith("http://"):
                    cover_url = cover_url.replace("http://", "https://")
                break

        # Extract publication year
        published_date = volume_info.get("publishedDate", "")
        publication_year = None
        if published_date:
            try:
                publication_year = int(published_date[:4])
            except (ValueError, IndexError):
                pass

        return BookMetadata(
            title=volume_info.get("title"),
            author=self._first_or_none(volume_info.get("authors", [])),
            description=volume_info.get("description"),
            cover_url=cover_url,
            page_count=volume_info.get("pageCount"),
            publication_year=publication_year,
            publisher=volume_info.get("publisher"),
            subjects=volume_info.get("categories", []),
            google_books_id=item.get("id"),
        )

    @staticmethod
    def _first_or_none(lst: list) -> Any | None:
        """Return first element or None."""
        return lst[0] if lst else None


class MetadataEnricher:
    """
    Service for enriching book metadata from external APIs.

    Tries multiple sources and merges results.
    """

    def __init__(self):
        self.open_library = OpenLibraryClient()
        self.google_books = GoogleBooksClient()

    async def close(self):
        await self.open_library.close()
        await self.google_books.close()

    async def enrich_by_isbn(self, isbn: str) -> BookMetadata | None:
        """
        Enrich book metadata by ISBN, trying multiple sources.

        Args:
            isbn: ISBN-10 or ISBN-13

        Returns:
            Merged BookMetadata from all sources
        """
        # Try both APIs in parallel
        ol_task = self.open_library.search_by_isbn(isbn)
        gb_task = self.google_books.search_by_isbn(isbn)

        ol_result, gb_result = await asyncio.gather(ol_task, gb_task)

        return self._merge_metadata(ol_result, gb_result)

    async def enrich_by_title_author(
        self, title: str, author: str
    ) -> BookMetadata | None:
        """
        Enrich book metadata by title and author, trying multiple sources.

        Args:
            title: Book title
            author: Author name

        Returns:
            Merged BookMetadata from all sources
        """
        # Try both APIs in parallel
        ol_task = self.open_library.search_by_title_author(title, author)
        gb_task = self.google_books.search_by_title_author(title, author)

        ol_result, gb_result = await asyncio.gather(ol_task, gb_task)

        return self._merge_metadata(ol_result, gb_result)

    @staticmethod
    def _merge_metadata(
        ol: BookMetadata | None, gb: BookMetadata | None
    ) -> BookMetadata | None:
        """
        Merge metadata from multiple sources.

        Prefers Open Library for covers (higher quality),
        Google Books for descriptions (more complete).
        """
        if not ol and not gb:
            return None

        if not ol:
            return gb

        if not gb:
            return ol

        # Merge, preferring non-None values
        return BookMetadata(
            title=ol.title or gb.title,
            author=ol.author or gb.author,
            description=gb.description or ol.description,  # Prefer Google for descriptions
            cover_url=ol.cover_url or gb.cover_url,  # Prefer Open Library for covers
            page_count=ol.page_count or gb.page_count,
            publication_year=ol.publication_year or gb.publication_year,
            publisher=ol.publisher or gb.publisher,
            subjects=_merge_lists(ol.subjects, gb.subjects),
            open_library_id=ol.open_library_id,
            google_books_id=gb.google_books_id,
        )


def _merge_lists(
    list1: list[str] | None, list2: list[str] | None
) -> list[str] | None:
    """Merge two lists, removing duplicates."""
    if not list1 and not list2:
        return None

    combined = set(list1 or []) | set(list2 or [])
    return list(combined)[:15]  # Limit to 15 items


# Convenience functions for synchronous use
def enrich_book_metadata_sync(
    isbn: str | None = None,
    title: str | None = None,
    author: str | None = None,
) -> BookMetadata | None:
    """
    Synchronous wrapper for metadata enrichment.

    Args:
        isbn: ISBN-10 or ISBN-13 (preferred)
        title: Book title (fallback)
        author: Author name (fallback)

    Returns:
        BookMetadata if found, None otherwise
    """
    async def _enrich():
        enricher = MetadataEnricher()
        try:
            if isbn:
                result = await enricher.enrich_by_isbn(isbn)
                if result:
                    return result

            if title and author:
                return await enricher.enrich_by_title_author(title, author)

            return None
        finally:
            await enricher.close()

    return asyncio.run(_enrich())
