from pydantic import BaseModel


class BookSearchResult(BaseModel):
    id: int
    title: str
    author: str
    cover_url: str | None
    publication_year: int | None
    is_romantasy: bool
    series_name: str | None
    series_position: float | None

    class Config:
        from_attributes = True


class BookTag(BaseModel):
    id: int
    name: str
    slug: str
    category: str

    class Config:
        from_attributes = True


class BookResponse(BaseModel):
    id: int
    title: str
    author: str
    description: str | None
    cover_url: str | None
    page_count: int | None
    publication_year: int | None

    # Series
    series_name: str | None
    series_position: float | None

    # Romantasy metadata
    is_romantasy: bool
    spice_level: int | None
    is_ya: bool | None
    tags: list[BookTag]

    # External links
    isbn_13: str | None
    open_library_id: str | None

    class Config:
        from_attributes = True
