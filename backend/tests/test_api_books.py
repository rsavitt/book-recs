"""Tests for books API endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestGetBook:
    """Test get book endpoint."""

    def test_get_book_by_id(self, client: TestClient, test_books):
        """Should return book by ID."""
        book = test_books[0]
        response = client.get(f"/api/v1/books/{book.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == book.id
        assert data["title"] == "A Court of Thorns and Roses"
        assert data["author"] == "Sarah J. Maas"

    def test_get_book_not_found(self, client: TestClient):
        """Should return 404 for non-existent book."""
        response = client.get("/api/v1/books/99999")

        assert response.status_code == 404


class TestSearchBooks:
    """Test book search endpoint."""

    def test_search_by_title(self, client: TestClient, test_books):
        """Should find books by title search."""
        response = client.get("/api/v1/books/?q=court")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any("Court" in book["title"] for book in data)

    def test_search_by_author(self, client: TestClient, test_books):
        """Should find books by author search."""
        response = client.get("/api/v1/books/?q=maas")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any("Maas" in book["author"] for book in data)

    def test_search_romantasy_only(self, client: TestClient, test_books):
        """Should filter to romantasy books only."""
        response = client.get("/api/v1/books/?q=&romantasy_only=true")

        assert response.status_code == 200
        data = response.json()
        # All test books are romantasy
        assert all(book.get("is_romantasy", True) for book in data)

    def test_search_empty_query(self, client: TestClient, test_books):
        """Should handle empty search query."""
        response = client.get("/api/v1/books/?q=")

        assert response.status_code == 200


class TestListRomantasy:
    """Test romantasy book listing endpoint."""

    def test_list_all_romantasy(self, client: TestClient, test_books):
        """Should list all romantasy books."""
        response = client.get("/api/v1/books/romantasy")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3  # All test books are romantasy

    def test_filter_by_spice_level(self, client: TestClient, test_books):
        """Should filter by spice level."""
        response = client.get("/api/v1/books/romantasy?spice_level=4")

        assert response.status_code == 200
        data = response.json()
        # Fourth Wing has spice level 4
        assert len(data) >= 1
        assert all(book.get("spice_level") == 4 or book.get("spice_level") is None for book in data)

    def test_filter_by_ya(self, client: TestClient, test_books):
        """Should filter by YA/Adult."""
        response = client.get("/api/v1/books/romantasy?is_ya=true")

        assert response.status_code == 200
        data = response.json()
        # The Cruel Prince is YA
        assert len(data) >= 1

    def test_pagination(self, client: TestClient, test_books):
        """Should support pagination."""
        response = client.get("/api/v1/books/romantasy?limit=2&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 2

        # Get second page
        response2 = client.get("/api/v1/books/romantasy?limit=2&offset=2")
        assert response2.status_code == 200


class TestGetTags:
    """Test tags endpoint."""

    def test_list_all_tags(self, client: TestClient, test_tags):
        """Should list all tags."""
        response = client.get("/api/v1/books/tags")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 4  # We created 4 test tags

    def test_filter_tags_by_category(self, client: TestClient, test_tags):
        """Should filter tags by category."""
        response = client.get("/api/v1/books/tags?category=trope")

        assert response.status_code == 200
        data = response.json()
        assert all(tag["category"] == "trope" for tag in data)
        # We have 3 trope tags
        assert len(data) >= 3
