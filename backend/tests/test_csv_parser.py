"""Unit tests for services.csv_parser."""

from models.schemas import RatedMovie, ReviewedMovie, WatchedMovie
from services.csv_parser import build_exclusion_set, build_taste_profile, is_watched


# ---------------------------------------------------------------------------
# build_exclusion_set / is_watched
# ---------------------------------------------------------------------------


def test_build_exclusion_set_basic():
    watched = [
        WatchedMovie(name="Fight Club", year=1999),
        WatchedMovie(name="Arrival", year=2016),
    ]
    result = build_exclusion_set(watched)
    assert result == {"fight club|1999", "arrival|2016"}


def test_build_exclusion_set_empty():
    assert build_exclusion_set([]) == set()


def test_is_watched_case_and_whitespace_insensitive():
    excl = build_exclusion_set([WatchedMovie(name="  Fight Club  ", year=1999)])
    assert is_watched("fight club", 1999, excl)
    assert is_watched("FIGHT CLUB", 1999, excl)
    assert is_watched("  Fight Club ", 1999, excl)


def test_is_watched_year_must_match():
    """Two films with the same title but different years should NOT collide."""
    excl = build_exclusion_set([WatchedMovie(name="Dune", year=1984)])
    assert is_watched("Dune", 1984, excl)
    assert not is_watched("Dune", 2021, excl)


def test_is_watched_miss():
    excl = build_exclusion_set([WatchedMovie(name="Fight Club", year=1999)])
    assert not is_watched("Arrival", 2016, excl)


# ---------------------------------------------------------------------------
# build_taste_profile
# ---------------------------------------------------------------------------


def test_taste_profile_no_ratings_returns_placeholder():
    profile = build_taste_profile([])
    assert "No taste profile" in profile


def test_taste_profile_filters_to_high_rated_and_sorts_desc():
    ratings = [
        RatedMovie(name="Mid Movie", year=2010, rating=3.0),
        RatedMovie(name="Great Movie", year=2015, rating=5.0),
        RatedMovie(name="Good Movie", year=2018, rating=4.0),
        RatedMovie(name="Solid Movie", year=2020, rating=4.5),
    ]
    profile = build_taste_profile(ratings)
    # Mid Movie (< 4.0) should be excluded
    assert "Mid Movie" not in profile
    # The high-rated three should appear in descending order
    idx_great = profile.index("Great Movie")
    idx_solid = profile.index("Solid Movie")
    idx_good = profile.index("Good Movie")
    assert idx_great < idx_solid < idx_good


def test_taste_profile_caps_at_top_10():
    ratings = [
        RatedMovie(name=f"Movie {i}", year=2000 + i, rating=5.0) for i in range(15)
    ]
    profile = build_taste_profile(ratings)
    # 10 bullet points, not 15
    assert profile.count("•") == 10


def test_taste_profile_fallback_when_no_high_ratings():
    """If nothing is rated >= 4.0, fall back to the top 5 by rating."""
    ratings = [
        RatedMovie(name=f"Movie {i}", year=2000 + i, rating=2.0 + i * 0.1)
        for i in range(8)
    ]
    profile = build_taste_profile(ratings)
    assert profile.count("•") == 5
    # Highest-rated of the fallback set should be included
    assert "Movie 7" in profile


def test_taste_profile_includes_review_excerpt():
    ratings = [RatedMovie(name="Arrival", year=2016, rating=5.0)]
    reviews = [
        ReviewedMovie(
            name="Arrival",
            year=2016,
            rating=5.0,
            review="A meditation on language and time.",
        )
    ]
    profile = build_taste_profile(ratings, reviews)
    assert "Arrival" in profile
    assert "meditation on language" in profile


def test_taste_profile_truncates_long_review():
    long_review = "x" * 500
    ratings = [RatedMovie(name="Foo", year=2020, rating=5.0)]
    reviews = [ReviewedMovie(name="Foo", year=2020, rating=5.0, review=long_review)]
    profile = build_taste_profile(ratings, reviews)
    # Reviews are truncated to 200 chars
    assert "x" * 200 in profile
    assert "x" * 201 not in profile


def test_taste_profile_review_matching_is_case_insensitive():
    ratings = [RatedMovie(name="Arrival", year=2016, rating=5.0)]
    reviews = [
        ReviewedMovie(
            name="  ARRIVAL  ", year=2016, rating=5.0, review="Linguistics, time, loss."
        )
    ]
    profile = build_taste_profile(ratings, reviews)
    assert "Linguistics" in profile
