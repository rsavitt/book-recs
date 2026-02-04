"""Tests for recommendations API endpoints."""

from fastapi.testclient import TestClient

from app.models.similarity import UserSimilarity


class TestGetRecommendations:
    """Test recommendations endpoint."""

    def test_get_recommendations_authenticated(
        self, client: TestClient, auth_headers, test_user, test_books, test_ratings, db
    ):
        """Should return recommendations for authenticated user."""
        # Create another user with ratings to generate similarity
        from app.models.rating import Rating
        from app.models.user import User
        from app.services.auth_service import get_password_hash

        other_user = User(
            email="other@example.com",
            username="otheruser",
            hashed_password=get_password_hash("password123"),
        )
        db.add(other_user)
        db.commit()
        db.refresh(other_user)

        # Other user rates the same books similarly
        for book in test_books:
            rating = Rating(user_id=other_user.id, book_id=book.id, rating=5)
            db.add(rating)

        # Create similarity record
        similarity = UserSimilarity(
            user_id=test_user.id,
            neighbor_id=other_user.id,
            raw_similarity=0.9,
            adjusted_similarity=0.7,
            overlap_count=3,
        )
        db.add(similarity)
        db.commit()

        response = client.get("/api/v1/recommendations/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_recommendations_unauthenticated(self, client: TestClient):
        """Should reject unauthenticated request."""
        response = client.get("/api/v1/recommendations/")

        assert response.status_code == 401

    def test_filter_by_spice(self, client: TestClient, auth_headers):
        """Should accept spice filter parameters."""
        response = client.get(
            "/api/v1/recommendations/?spice_min=2&spice_max=4",
            headers=auth_headers,
        )

        assert response.status_code == 200

    def test_filter_by_ya(self, client: TestClient, auth_headers):
        """Should accept YA filter parameter."""
        response = client.get(
            "/api/v1/recommendations/?is_ya=true",
            headers=auth_headers,
        )

        assert response.status_code == 200

    def test_filter_by_tropes(self, client: TestClient, auth_headers):
        """Should accept trope filter parameters."""
        response = client.get(
            "/api/v1/recommendations/?tropes=enemies-to-lovers&tropes=slow-burn",
            headers=auth_headers,
        )

        assert response.status_code == 200


class TestSubmitFeedback:
    """Test recommendation feedback endpoint."""

    def test_submit_interested_feedback(self, client: TestClient, auth_headers, test_books):
        """Should accept 'interested' feedback."""
        book = test_books[2]  # A book the user hasn't rated

        response = client.post(
            f"/api/v1/recommendations/{book.id}/feedback?feedback=interested",
            headers=auth_headers,
        )

        assert response.status_code == 200

    def test_submit_not_interested_feedback(self, client: TestClient, auth_headers, test_books):
        """Should accept 'not_interested' feedback."""
        book = test_books[2]

        response = client.post(
            f"/api/v1/recommendations/{book.id}/feedback?feedback=not_interested",
            headers=auth_headers,
        )

        assert response.status_code == 200

    def test_submit_already_read_feedback(self, client: TestClient, auth_headers, test_books):
        """Should accept 'already_read' feedback."""
        book = test_books[2]

        response = client.post(
            f"/api/v1/recommendations/{book.id}/feedback?feedback=already_read",
            headers=auth_headers,
        )

        assert response.status_code == 200

    def test_submit_invalid_feedback(self, client: TestClient, auth_headers, test_books):
        """Should reject invalid feedback value."""
        book = test_books[0]

        response = client.post(
            f"/api/v1/recommendations/{book.id}/feedback?feedback=invalid",
            headers=auth_headers,
        )

        assert response.status_code == 422

    def test_submit_feedback_unauthenticated(self, client: TestClient, test_books):
        """Should reject unauthenticated feedback."""
        book = test_books[0]

        response = client.post(f"/api/v1/recommendations/{book.id}/feedback?feedback=interested")

        assert response.status_code == 401
