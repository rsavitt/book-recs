from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.book import Book, BookTag
from app.schemas.book import BookResponse, BookSearchResult


def search_books(
    db: Session,
    query: str,
    romantasy_only: bool = False,
    limit: int = 20,
) -> list[BookSearchResult]:
    """Search books by title or author."""
    search_term = f"%{query.lower()}%"

    q = db.query(Book).filter(
        or_(
            Book.title.ilike(search_term),
            Book.author.ilike(search_term),
        )
    )

    if romantasy_only:
        q = q.filter(Book.is_romantasy)

    books = q.order_by(Book.title).limit(limit).all()

    return [
        BookSearchResult(
            id=book.id,
            title=book.title,
            author=book.author,
            cover_url=book.cover_url,
            publication_year=book.publication_year,
            is_romantasy=book.is_romantasy,
            series_name=book.series_name,
            series_position=book.series_position,
        )
        for book in books
    ]


def list_romantasy_books(
    db: Session,
    spice_level: int | None = None,
    is_ya: bool | None = None,
    tropes: list[str] | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[BookSearchResult]:
    """List Romantasy books with filters."""
    q = db.query(Book).filter(Book.is_romantasy)

    if spice_level is not None:
        q = q.filter(Book.spice_level == spice_level)

    if is_ya is not None:
        q = q.filter(Book.is_ya == is_ya)

    if tropes:
        # Filter by tags
        q = q.join(Book.tags).filter(BookTag.slug.in_([t.lower() for t in tropes]))

    books = q.order_by(Book.title).offset(offset).limit(limit).all()

    return [
        BookSearchResult(
            id=book.id,
            title=book.title,
            author=book.author,
            cover_url=book.cover_url,
            publication_year=book.publication_year,
            is_romantasy=book.is_romantasy,
            series_name=book.series_name,
            series_position=book.series_position,
        )
        for book in books
    ]


def list_tags(db: Session, category: str | None = None) -> list[dict]:
    """List available book tags/tropes."""
    q = db.query(BookTag)

    if category:
        q = q.filter(BookTag.category == category)

    tags = q.order_by(BookTag.name).all()

    return [
        {
            "id": tag.id,
            "name": tag.name,
            "slug": tag.slug,
            "category": tag.category,
            "is_romantasy_indicator": tag.is_romantasy_indicator,
        }
        for tag in tags
    ]


def get_book(db: Session, book_id: int) -> BookResponse | None:
    """Get book details by ID."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        return None

    return BookResponse(
        id=book.id,
        title=book.title,
        author=book.author,
        description=book.description,
        cover_url=book.cover_url,
        page_count=book.page_count,
        publication_year=book.publication_year,
        series_name=book.series_name,
        series_position=book.series_position,
        is_romantasy=book.is_romantasy,
        spice_level=book.spice_level,
        is_ya=book.is_ya,
        tags=[
            {
                "id": tag.id,
                "name": tag.name,
                "slug": tag.slug,
                "category": tag.category,
            }
            for tag in book.tags
        ],
        isbn_13=book.isbn_13,
        open_library_id=book.open_library_id,
    )
