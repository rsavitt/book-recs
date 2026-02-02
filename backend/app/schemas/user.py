from datetime import datetime
from pydantic import BaseModel, Field


class UserPreferencesUpdate(BaseModel):
    spice_preference: int | None = Field(None, ge=0, le=5)
    prefers_ya: bool | None = None
    exclude_why_choose: bool | None = None  # Filter out Why Choose/Reverse Harem books
    is_public: bool | None = None
    allow_data_for_recs: bool | None = None
    display_name: str | None = Field(None, max_length=100)
    bio: str | None = Field(None, max_length=500)


class RatingStats(BaseModel):
    total_books: int
    total_rated: int
    average_rating: float
    rating_distribution: dict[int, int]  # {1: count, 2: count, ...}


class UserProfile(BaseModel):
    id: int
    username: str
    display_name: str | None
    bio: str | None
    is_public: bool
    created_at: datetime
    last_import_at: datetime | None
    stats: RatingStats
    top_shelves: list[str]
    spice_preference: int | None
    prefers_ya: bool | None
    exclude_why_choose: bool

    class Config:
        from_attributes = True


class SimilarUser(BaseModel):
    username: str
    display_name: str | None
    similarity_score: float
    overlap_count: int
    shared_favorites: list[str]  # List of book titles

    class Config:
        from_attributes = True
