"""Gemini API client wrapper for embeddings and text generation."""

import logging
import os

from google import genai
from google.genai import types


logger = logging.getLogger(__name__)

# Models
EMBEDDING_MODEL = "gemini-embedding-001"
GENERATION_MODEL = "gemini-2.5-flash"
EMBEDDING_DIMENSION = 768


def _get_client() -> genai.Client:
    """Create a Gemini client using the API key from environment."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable not set")
    return genai.Client(api_key=api_key)


def embed_query(text: str) -> list[float]:
    """Generate a 768-dimensional embedding for a text query.

    Args:
        text: The query text to embed.

    Returns:
        A list of 768 floats representing the embedding vector.
    """
    client = _get_client()
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIMENSION),
    )
    return list(result.embeddings[0].values)


def generate_recommendation(system_prompt: str, user_prompt: str) -> str:
    """Generate a movie recommendation using Gemini 2.5 Flash.

    Args:
        system_prompt: Instructions for the LLM (film critic role, constraints).
        user_prompt: The user's taste profile, candidate movies, and query.

    Returns:
        The LLM's generated recommendation text.
    """
    client = _get_client()
    response = client.models.generate_content(
        model=GENERATION_MODEL,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.7,
            max_output_tokens=2048,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )

    # Extract text from response, handling potential issues
    text = ""
    try:
        text = response.text or ""
    except Exception as e:
        logger.error("Error accessing response.text: %s", str(e))
        # Try to extract from parts directly
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, "text") and part.text:
                    text += part.text

    logger.info("Gemini response length: %d chars", len(text))
    logger.info("Gemini response full text: %s", text[:1000])

    return text

