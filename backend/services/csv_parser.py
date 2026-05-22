"""Letterboxd CSV data parsing utilities.

Processes pre-parsed user data (watched, ratings, reviews) into formats
suitable for the RAG pipeline.
"""

from models.schemas import WatchedMovie, RatedMovie, ReviewedMovie


def build_exclusion_set(watched: list[WatchedMovie]) -> set[str]:
    """Build a set of watched movie identifiers for exclusion filtering.

    Uses lowercase "title|year" as the key to handle remakes with the same
    title but different years.

    Args:
        watched: List of movies the user has already watched.

    Returns:
        A set of "title|year" strings for O(1) lookup.
    """
    return {f"{m.name.lower().strip()}|{m.year}" for m in watched}


def is_watched(title: str, year: int, exclusion_set: set[str]) -> bool:
    """Check if a movie is in the user's watched list.

    Args:
        title: Movie title from Firestore.
        year: Release year from Firestore.
        exclusion_set: The set built by build_exclusion_set().

    Returns:
        True if the movie has been watched.
    """
    return f"{title.lower().strip()}|{year}" in exclusion_set


def build_taste_profile(
    ratings: list[RatedMovie],
    reviews: list[ReviewedMovie] | None = None,
) -> str:
    """Build a text summary of the user's movie taste for the LLM prompt.

    Filters to movies rated >= 4.0 stars, sorts by rating, and takes
    the top 10. Includes review excerpts when available.

    Args:
        ratings: User's rated movies with scores.
        reviews: Optional user reviews with text.

    Returns:
        A formatted text string describing the user's taste, e.g.:
        "User's favorite movies: Good Will Hunting (5★), ..."
    """
    if not ratings:
        return "No taste profile available — user has not rated any movies."

    # Build a review lookup for enrichment
    review_map: dict[str, str] = {}
    if reviews:
        for r in reviews:
            if r.review:
                key = f"{r.name.lower().strip()}|{r.year}"
                review_map[key] = r.review[:200]  # truncate long reviews

    # Filter to high-rated movies and sort
    favorites = sorted(
        [r for r in ratings if r.rating >= 4.0],
        key=lambda r: r.rating,
        reverse=True,
    )[:10]

    if not favorites:
        # Fall back to top-rated even if below 4.0
        favorites = sorted(ratings, key=lambda r: r.rating, reverse=True)[:5]

    # Format the taste profile
    parts = []
    for movie in favorites:
        stars = f"{movie.rating}★"
        entry = f"{movie.name} ({movie.year}, {stars})"

        # Append review excerpt if available
        key = f"{movie.name.lower().strip()}|{movie.year}"
        if key in review_map:
            entry += f' — "{review_map[key]}"'

        parts.append(entry)

    profile = "User's favorite movies:\n" + "\n".join(f"  • {p}" for p in parts)
    return profile
