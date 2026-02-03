"""
Pytest configuration and fixtures for backend tests.
"""

from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models.book import Book, BookTag
from app.models.rating import Rating
from app.models.user import User
from app.services.auth_service import create_access_token, get_password_hash

# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """Create a fresh database session for each test."""
    # Create all tables
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    """Create a test client with database override."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db: Session) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash("testpassword123"),
        display_name="Test User",
        is_public=False,
        spice_preference=3,
        prefers_ya=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_user_token(test_user: User) -> str:
    """Create an access token for the test user."""
    return create_access_token(data={"sub": test_user.email})


@pytest.fixture
def auth_headers(test_user_token: str) -> dict:
    """Create authorization headers."""
    return {"Authorization": f"Bearer {test_user_token}"}


@pytest.fixture
def test_books(db: Session) -> list[Book]:
    """Create test books."""
    books = [
        Book(
            title="A Court of Thorns and Roses",
            author="Sarah J. Maas",
            isbn_13="9781619634442",
            is_romantasy=True,
            spice_level=3,
            is_ya=False,
            series_name="A Court of Thorns and Roses",
            series_position=1,
            publication_year=2015,
        ),
        Book(
            title="Fourth Wing",
            author="Rebecca Yarros",
            isbn_13="9781649374042",
            is_romantasy=True,
            spice_level=4,
            is_ya=False,
            series_name="The Empyrean",
            series_position=1,
            publication_year=2023,
        ),
        Book(
            title="The Cruel Prince",
            author="Holly Black",
            isbn_13="9780316310277",
            is_romantasy=True,
            spice_level=1,
            is_ya=True,
            series_name="The Folk of the Air",
            series_position=1,
            publication_year=2018,
        ),
    ]

    for book in books:
        db.add(book)

    db.commit()

    for book in books:
        db.refresh(book)

    return books


@pytest.fixture
def test_ratings(db: Session, test_user: User, test_books: list[Book]) -> list[Rating]:
    """Create test ratings for the test user."""
    ratings = [
        Rating(user_id=test_user.id, book_id=test_books[0].id, rating=5),
        Rating(user_id=test_user.id, book_id=test_books[1].id, rating=4),
    ]

    for rating in ratings:
        db.add(rating)

    db.commit()

    for rating in ratings:
        db.refresh(rating)

    return ratings


@pytest.fixture
def test_tags(db: Session) -> list[BookTag]:
    """Create test book tags."""
    tags = [
        BookTag(name="Enemies to Lovers", slug="enemies-to-lovers", category="trope"),
        BookTag(name="Fae", slug="fae", category="genre"),
        BookTag(name="Slow Burn", slug="slow-burn", category="trope"),
        BookTag(name="Forced Proximity", slug="forced-proximity", category="trope"),
    ]

    for tag in tags:
        db.add(tag)

    db.commit()

    for tag in tags:
        db.refresh(tag)

    return tags


# Sample CSV data for import tests
SAMPLE_GOODREADS_CSV = b"""Book Id,Title,Author,Author l-f,Additional Authors,ISBN,ISBN13,My Rating,Average Rating,Publisher,Binding,Number of Pages,Year Published,Original Publication Year,Date Read,Date Added,Bookshelves,Bookshelves with positions,Exclusive Shelf,My Review,Spoiler,Private Notes
12345,A Court of Thorns and Roses (A Court of Thorns and Roses #1),Sarah J. Maas,"Maas, Sarah J.",,="1619634449",="9781619634442",5,4.25,Bloomsbury Publishing,Paperback,432,2015,2015,2024/01/15,2023/12/01,"romantasy, fae, favorites","romantasy (#1), fae (#2), favorites (#3)",read,Great book!,false,
67890,Fourth Wing (The Empyrean #1),Rebecca Yarros,"Yarros, Rebecca",,="1649374046",="9781649374042",4,4.56,Red Tower Books,Hardcover,528,2023,2023,2024/02/20,2024/01/10,romantasy,romantasy (#1),read,,false,
"""


@pytest.fixture
def sample_csv() -> bytes:
    """Return sample Goodreads CSV data."""
    return SAMPLE_GOODREADS_CSV
