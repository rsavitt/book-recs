from pydantic import BaseModel, Field


class RecommendationFilters(BaseModel):
    spice_min: int | None = Field(None, ge=0, le=5)
    spice_max: int | None = Field(None, ge=0, le=5)
    is_ya: bool | None = None
    include_tropes: list[str] | None = None
    exclude_tropes: list[str] | None = None
    exclude_why_choose: bool | None = None  # True to filter out Why Choose/Reverse Harem books


class RecommendationExplanation(BaseModel):
    similar_user_count: int
    average_neighbor_rating: float
    top_shared_books: list[str]  # Titles of books you have in common with recommenders
    sample_explanation: str  # Human-readable explanation


class RecommendationResponse(BaseModel):
    book_id: int
    title: str
    author: str
    cover_url: str | None = None
    publication_year: int | None = None

    # Series info
    series_name: str | None = None
    series_position: float | None = None

    # Romantasy metadata
    spice_level: int | None = None
    is_ya: bool | None = None
    tags: list[str] = []  # Just tag names for display

    # Recommendation data (for personalized recs)
    predicted_rating: float | None = None  # Predicted rating for this user
    confidence: float | None = None  # How confident we are (based on overlap)
    explanation: RecommendationExplanation | None = None

    # For popular/quick recommendations
    score: float | None = None  # Match score (0-1)
    reason: str | None = None  # Why this was recommended

    class Config:
        from_attributes = True
