"""Integration tests for the import pipeline."""

from io import BytesIO

from fastapi.testclient import TestClient

from app.services.book_dedup import BookDeduplicator
from app.services.csv_parser import parse_goodreads_csv


class TestCSVImportEndpoint:
    """Test CSV import API endpoint."""

    def test_upload_valid_csv(self, client: TestClient, auth_headers, sample_csv):
        """Should accept and process a valid Goodreads CSV."""
        files = {"file": ("goodreads_export.csv", BytesIO(sample_csv), "text/csv")}

        response = client.post(
            "/api/v1/imports/goodreads",
            headers=auth_headers,
            files=files,
        )

        assert response.status_code == 200
        data = response.json()
        assert "import_id" in data
        assert data["status"] in ["pending", "processing", "completed"]

    def test_upload_invalid_csv(self, client: TestClient, auth_headers):
        """Should reject invalid CSV file."""
        invalid_csv = b"wrong,headers,here\n1,2,3\n"
        files = {"file": ("invalid.csv", BytesIO(invalid_csv), "text/csv")}

        response = client.post(
            "/api/v1/imports/goodreads",
            headers=auth_headers,
            files=files,
        )

        # Should return error about invalid format
        assert response.status_code in [400, 422]

    def test_upload_empty_file(self, client: TestClient, auth_headers):
        """Should reject empty file."""
        files = {"file": ("empty.csv", BytesIO(b""), "text/csv")}

        response = client.post(
            "/api/v1/imports/goodreads",
            headers=auth_headers,
            files=files,
        )

        assert response.status_code in [400, 422]

    def test_upload_unauthenticated(self, client: TestClient, sample_csv):
        """Should reject unauthenticated upload."""
        files = {"file": ("goodreads_export.csv", BytesIO(sample_csv), "text/csv")}

        response = client.post(
            "/api/v1/imports/goodreads",
            files=files,
        )

        assert response.status_code == 401


class TestImportPipelineIntegration:
    """Integration tests for the full import pipeline."""

    def test_parse_and_dedupe_workflow(self, db, sample_csv):
        """Test parsing CSV and deduplicating books."""
        # Step 1: Parse the CSV
        books, errors, warnings = parse_goodreads_csv(sample_csv)

        assert len(errors) == 0
        assert len(books) == 2

        # Verify parsed data
        acotar = books[0]
        assert acotar.title == "A Court of Thorns and Roses"
        assert acotar.author == "Sarah J. Maas"
        assert acotar.rating == 5
        assert acotar.series_name == "A Court of Thorns and Roses"
        assert acotar.series_position == 1.0

        fourth_wing = books[1]
        assert fourth_wing.title == "Fourth Wing"
        assert fourth_wing.series_name == "The Empyrean"

    def test_import_creates_books_and_ratings(self, db, sample_csv, test_user):
        """Test that import creates books and ratings in database."""
        from app.models.book import Book
        from app.models.rating import Rating

        # Parse CSV
        parsed_books, errors, warnings = parse_goodreads_csv(sample_csv)
        assert len(parsed_books) == 2

        # Create deduplicator
        deduplicator = BookDeduplicator(db)

        # Process each book
        for parsed in parsed_books:
            result = deduplicator.find_or_create(parsed)

            # Create rating if user rated the book
            if parsed.rating > 0:
                rating = Rating(
                    user_id=test_user.id,
                    book_id=result.book.id,
                    rating=parsed.rating,
                )
                db.add(rating)

        db.commit()

        # Verify books were created
        books = db.query(Book).all()
        assert len(books) >= 2

        # Verify ratings were created
        ratings = db.query(Rating).filter(Rating.user_id == test_user.id).all()
        assert len(ratings) == 2
        assert any(r.rating == 5 for r in ratings)
        assert any(r.rating == 4 for r in ratings)


class TestImportEdgeCases:
    """Test edge cases in import processing."""

    def test_import_duplicate_books(self, db, test_user):
        """Test importing the same book twice."""
        csv1 = b"""Book Id,Title,Author,My Rating,ISBN13
12345,Test Book,Test Author,4,="9781234567890"
"""
        csv2 = b"""Book Id,Title,Author,My Rating,ISBN13
67890,Test Book,Test Author,5,="9781234567890"
"""

        # Parse both CSVs
        books1, _, _ = parse_goodreads_csv(csv1)
        books2, _, _ = parse_goodreads_csv(csv2)

        deduplicator = BookDeduplicator(db)

        # First import
        result1 = deduplicator.find_or_create(books1[0])
        assert result1.is_new_book is True
        book_id = result1.book.id

        # Second import should find same book
        result2 = deduplicator.find_or_create(books2[0])
        assert result2.is_new_book is False
        assert result2.book.id == book_id

    def test_import_book_without_isbn(self, db):
        """Test importing a book without ISBN."""
        csv = b"""Book Id,Title,Author,My Rating
12345,A Book Without ISBN,Some Author,3
"""
        books, errors, warnings = parse_goodreads_csv(csv)

        assert len(books) == 1
        assert books[0].isbn is None
        assert books[0].isbn13 is None

        # Should still be able to deduplicate
        deduplicator = BookDeduplicator(db)
        result = deduplicator.find_or_create(books[0])
        assert result.book is not None

    def test_import_unrated_books(self, db, test_user):
        """Test importing books that haven't been rated (to-read shelf)."""
        csv = b"""Book Id,Title,Author,My Rating,Exclusive Shelf
12345,Want to Read Book,Some Author,0,to-read
67890,Currently Reading,Other Author,0,currently-reading
"""
        books, errors, warnings = parse_goodreads_csv(csv)

        assert len(books) == 2
        assert books[0].rating == 0
        assert books[0].exclusive_shelf == "to-read"
        assert books[1].exclusive_shelf == "currently-reading"

    def test_import_preserves_shelves(self, db):
        """Test that user shelves are preserved during import."""
        csv = b"""Book Id,Title,Author,My Rating,Bookshelves
12345,Tagged Book,Some Author,4,"romantasy, favorites, fae, 2024-reads"
"""
        books, errors, warnings = parse_goodreads_csv(csv)

        assert len(books) == 1
        assert "romantasy" in books[0].shelves
        assert "favorites" in books[0].shelves
        assert "fae" in books[0].shelves
        assert "2024-reads" in books[0].shelves
