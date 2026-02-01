from pydantic import BaseModel, Field


class RecommendationFilters(BaseModel):
    spice_min: int | None = Field(None, ge=0, le=5)
    spice_max: int | None = Field(None, ge=0, le=5)
    is_ya: bool | None = None
    include_tropes: list[str] | None = None
    exclude_tropes: list[str] | None = None


class RecommendationExplanation(BaseModel):
    similar_user_count: int
    average_neighbor_rating: float
    top_shared_books: list[str]  # Titles of books you have in common with recommenders
    sample_explanation: str  # Human-readable explanation


class RecommendationResponse(BaseModel):
    book_id: int
    title: str
    author: str
    cover_url: str | None
    publication_year: int | None

    # Series info
    series_name: str | None
    series_position: float | None

    # Romantasy metadata
    spice_level: int | None
    is_ya: bool | None
    tags: list[str]  # Just tag names for display

    # Recommendation data
    predicted_rating: float  # Predicted rating for this user
    confidence: float  # How confident we are (based on overlap)
    explanation: RecommendationExplanation

    class Config:
        from_attributes = True
