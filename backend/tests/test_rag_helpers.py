"""Unit tests for the pure helpers inside services.rag_pipeline."""

from services.rag_pipeline import (
    _build_user_prompt,
    _extract_json_array,
    _parse_llm_response,
)


def _sample_candidates() -> list[dict]:
    return [
        {
            "title": "Fight Club",
            "tmdb_id": 550,
            "release_year": 1999,
            "genres": "Drama",
            "director": "David Fincher",
            "poster_url": "https://example.com/fc.jpg",
            "overview": "An insomniac office worker forms an underground club...",
        },
        {
            "title": "Arrival",
            "tmdb_id": 329865,
            "release_year": 2016,
            "genres": "Sci-Fi, Drama",
            "director": "Denis Villeneuve",
            "poster_url": "https://example.com/arr.jpg",
            "overview": "A linguist works with the military to communicate with aliens...",
        },
    ]


# ---------------------------------------------------------------------------
# _extract_json_array
# ---------------------------------------------------------------------------


def test_extract_json_array_clean():
    text = '[{"tmdb_id": 550, "explanation": "Great pick"}]'
    result = _extract_json_array(text)
    assert result == [{"tmdb_id": 550, "explanation": "Great pick"}]


def test_extract_json_array_markdown_wrapped():
    text = '```json\n[{"tmdb_id": 550, "explanation": "Great pick"}]\n```'
    result = _extract_json_array(text)
    assert len(result) == 1
    assert result[0]["tmdb_id"] == 550


def test_extract_json_array_plain_markdown_fence():
    text = '```\n[{"tmdb_id": 1, "explanation": "x"}]\n```'
    assert _extract_json_array(text) == [{"tmdb_id": 1, "explanation": "x"}]


def test_extract_json_array_with_surrounding_prose():
    text = (
        "Sure thing! Here are my picks:\n"
        '[{"tmdb_id": 550, "explanation": "x"}]\n'
        "Hope that helps."
    )
    result = _extract_json_array(text)
    assert result == [{"tmdb_id": 550, "explanation": "x"}]


def test_extract_json_array_malformed_returns_empty():
    assert _extract_json_array("not json at all") == []
    assert _extract_json_array("") == []
    assert _extract_json_array("[oops not valid json]") == []


def test_extract_json_array_object_not_array_returns_empty():
    # The contract is "array of picks" — a top-level object isn't valid.
    assert _extract_json_array('{"tmdb_id": 550}') == []


# ---------------------------------------------------------------------------
# _parse_llm_response
# ---------------------------------------------------------------------------


def test_parse_llm_response_maps_picks_to_candidate_metadata():
    candidates = _sample_candidates()
    response = (
        '[{"tmdb_id": 550, "explanation": "Dark and twisty, matches your taste."}]'
    )
    recs = _parse_llm_response(response, candidates)
    assert len(recs) == 1
    rec = recs[0]
    assert rec.tmdb_id == 550
    assert rec.title == "Fight Club"
    assert rec.director == "David Fincher"
    assert rec.poster_url == "https://example.com/fc.jpg"
    assert rec.explanation == "Dark and twisty, matches your taste."


def test_parse_llm_response_drops_unknown_tmdb_ids():
    """An LLM hallucinating a tmdb_id not in the candidate set is silently dropped."""
    candidates = _sample_candidates()
    response = (
        '[{"tmdb_id": 999999, "explanation": "hallucinated"},'
        ' {"tmdb_id": 550, "explanation": "real"}]'
    )
    recs = _parse_llm_response(response, candidates)
    assert len(recs) == 1
    assert recs[0].tmdb_id == 550


def test_parse_llm_response_falls_back_when_llm_returns_garbage():
    """If JSON parsing fails entirely, we return up to 3 candidates with a
    generic explanation rather than an empty list."""
    candidates = _sample_candidates()
    recs = _parse_llm_response("complete nonsense, no json", candidates)
    assert 1 <= len(recs) <= 3
    assert all(r.explanation for r in recs)


def test_parse_llm_response_empty_input_and_no_candidates():
    assert _parse_llm_response("", []) == []


def test_parse_llm_response_empty_llm_with_candidates_uses_fallback():
    candidates = _sample_candidates()
    recs = _parse_llm_response("", candidates)
    # Fallback path still produces recommendations from the candidates.
    assert len(recs) >= 1
    assert recs[0].title in {"Fight Club", "Arrival"}


# ---------------------------------------------------------------------------
# _build_user_prompt
# ---------------------------------------------------------------------------


def test_build_user_prompt_includes_query_taste_and_candidates():
    candidates = _sample_candidates()
    prompt = _build_user_prompt(
        query="something cerebral",
        taste_profile="User's favorite movies:\n  • Arrival (2016, 5★)",
        candidates=candidates,
    )
    assert "something cerebral" in prompt
    assert "Arrival (2016, 5★)" in prompt
    assert "tmdb_id=550" in prompt
    assert "Fight Club" in prompt
    # Director should be mentioned for at least one candidate
    assert "David Fincher" in prompt
