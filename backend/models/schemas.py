"""Pydantic models for request/response schemas."""

from pydantic import BaseModel, Field


class WatchedMovie(BaseModel):
    """A movie from the user's watched list."""
    name: str
    year: int = 0


class RatedMovie(BaseModel):
    """A movie from the user's ratings list."""
    name: str
    year: int = 0
    rating: float = Field(ge=0, le=5)


class ReviewedMovie(BaseModel):
    """A movie from the user's reviews list."""
    name: str
    year: int = 0
    rating: float = Field(ge=0, le=5, default=0)
    review: str = ""


class RecommendRequest(BaseModel):
    """Request body for /api/recommend."""
    query: str = Field(min_length=1, max_length=500)
    watched: list[WatchedMovie] = Field(default_factory=list, max_length=10000)
    ratings: list[RatedMovie] = Field(default_factory=list, max_length=10000)
    reviews: list[ReviewedMovie] = Field(default_factory=list, max_length=10000)


class MovieRecommendation(BaseModel):
    """A single movie recommendation with LLM explanation."""
    title: str
    tmdb_id: int
    release_year: int
    genres: str
    director: str
    poster_url: str
    explanation: str


class RecommendResponse(BaseModel):
    """Response body for /api/recommend."""
    recommendations: list[MovieRecommendation]
    query: str
