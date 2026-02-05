from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.book import BookResponse, BookSearchResult
from app.services import book_service

router = APIRouter()


@router.get("/", response_model=list[BookSearchResult])
async def search_books(
    q: str = Query(..., min_length=2, description="Search query"),
    romantasy_only: bool = Query(False, description="Only return Romantasy books"),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
):
    """Search books by title or author."""
    return book_service.search_books(db, q, romantasy_only=romantasy_only, limit=limit)


@router.get("/romantasy", response_model=list[BookSearchResult])
async def list_romantasy_books(
    spice_level: int | None = Query(None, ge=0, le=5),
    is_ya: bool | None = Query(None),
    tropes: list[str] | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: Session = Depends(get_db),
):
    """List Romantasy books with filters."""
    return book_service.list_romantasy_books(
        db,
        spice_level=spice_level,
        is_ya=is_ya,
        tropes=tropes,
        limit=limit,
        offset=offset,
    )


@router.get("/tags")
async def list_tags(
    category: str | None = Query(
        None, description="Filter by category: genre, trope, theme, setting"
    ),
    db: Session = Depends(get_db),
):
    """List available book tags/tropes."""
    return book_service.list_tags(db, category=category)


@router.get("/{book_id}", response_model=BookResponse)
async def get_book(
    book_id: int,
    db: Session = Depends(get_db),
):
    """Get book details by ID."""
    book = book_service.get_book(db, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book
