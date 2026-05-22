"""Recommendation endpoint: /api/recommend."""

import re

from fastapi import APIRouter, HTTPException

from models.schemas import RecommendRequest, RecommendResponse
from services.rag_pipeline import get_recommendations


router = APIRouter()

# Patterns that suggest prompt injection attempts
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"ignore\s+(all\s+)?above",
    r"disregard\s+(all\s+)?previous",
    r"forget\s+(all\s+)?previous",
    r"^system\s*:",
    r"^assistant\s*:",
    r"you\s+are\s+now",
    r"new\s+instructions",
    r"override\s+(all\s+)?instructions",
    r"reveal\s+(your\s+)?(system\s+)?prompt",
]

_compiled_patterns = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


def _check_injection(query: str) -> bool:
    """Check if a query contains prompt injection patterns."""
    for pattern in _compiled_patterns:
        if pattern.search(query):
            return True
    return False


@router.post("/recommend", response_model=RecommendResponse)
async def recommend(request: RecommendRequest) -> RecommendResponse:
    """Get personalized movie recommendations.

    Accepts the user's natural language query along with their Letterboxd
    watched/ratings/reviews data and returns AI-powered recommendations.
    """
    # Input validation
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    if len(query) > 500:
        raise HTTPException(status_code=400, detail="Query must be 500 characters or less.")

    # Prompt injection check
    if _check_injection(query):
        raise HTTPException(
            status_code=400,
            detail="Your query was flagged as potentially harmful. Please ask a movie-related question.",
        )

    try:
        response = await get_recommendations(request)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while generating recommendations: {str(e)}",
        )
