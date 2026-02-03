"""Tests for authentication API endpoints."""

from fastapi.testclient import TestClient


class TestRegister:
    """Test user registration endpoint."""

    def test_register_success(self, client: TestClient):
        """Should register a new user successfully."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "securepassword123",
                "display_name": "New User",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["username"] == "newuser"
        assert "password" not in data
        assert "hashed_password" not in data

    def test_register_duplicate_email(self, client: TestClient, test_user):
        """Should reject registration with existing email."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",  # Same as test_user
                "username": "differentuser",
                "password": "securepassword123",
            },
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_register_duplicate_username(self, client: TestClient, test_user):
        """Should reject registration with existing username."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "different@example.com",
                "username": "testuser",  # Same as test_user
                "password": "securepassword123",
            },
        )

        assert response.status_code == 400
        assert "username" in response.json()["detail"].lower()

    def test_register_invalid_email(self, client: TestClient):
        """Should reject invalid email format."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "notanemail",
                "username": "newuser",
                "password": "securepassword123",
            },
        )

        assert response.status_code == 422  # Validation error

    def test_register_short_password(self, client: TestClient):
        """Should reject passwords that are too short."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "short",
            },
        )

        assert response.status_code == 422


class TestLogin:
    """Test login endpoint."""

    def test_login_success(self, client: TestClient, test_user):
        """Should login successfully with correct credentials."""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "test@example.com",
                "password": "testpassword123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client: TestClient, test_user):
        """Should reject wrong password."""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "test@example.com",
                "password": "wrongpassword",
            },
        )

        assert response.status_code == 401

    def test_login_nonexistent_user(self, client: TestClient):
        """Should reject login for non-existent user."""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "anypassword",
            },
        )

        assert response.status_code == 401


class TestCurrentUser:
    """Test current user endpoint."""

    def test_get_current_user(self, client: TestClient, auth_headers, test_user):
        """Should return current user info."""
        response = client.get("/api/v1/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["username"] == test_user.username

    def test_get_current_user_no_token(self, client: TestClient):
        """Should reject request without token."""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401

    def test_get_current_user_invalid_token(self, client: TestClient):
        """Should reject invalid token."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalidtoken"},
        )

        assert response.status_code == 401


class TestPasswordReset:
    """Test password reset endpoints."""

    def test_forgot_password_existing_user(self, client: TestClient, test_user):
        """Should accept forgot password request for existing user."""
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "test@example.com"},
        )

        # Should return 200 even if email exists (for security)
        assert response.status_code == 200

    def test_forgot_password_nonexistent_user(self, client: TestClient):
        """Should accept forgot password request even for non-existent user."""
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nonexistent@example.com"},
        )

        # Should return 200 to not reveal if email exists
        assert response.status_code == 200
