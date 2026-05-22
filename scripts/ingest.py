#!/usr/bin/env python3
"""
Phase 1: TMDB Data Ingestion Script

Fetches the top 10,000 most popular movies from TMDB, generates vector embeddings
with Gemini gemini-embedding-001, and writes them to Firestore for native vector search.

Usage:
    python scripts/ingest.py            # Full ingestion pipeline
    python scripts/ingest.py --test     # Run a test vector search query after ingestion
    python scripts/ingest.py --resume   # Skip TMDB fetch if cache exists, resume from embeddings
"""

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.cloud import firestore
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from google.cloud.firestore_v1.vector import Vector
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_POSTER_BASE = "https://image.tmdb.org/t/p/w500"
TMDB_TOTAL_PAGES = 500  # 500 pages × 20 results = 10,000 movies
TMDB_DELAY = 0.25  # seconds between TMDB requests (rate limit ~40 req/10s)

GEMINI_EMBEDDING_MODEL = "gemini-embedding-001"
GEMINI_BATCH_SIZE = 100  # texts per embedding API call
GEMINI_RPM_LIMIT = 15  # requests per minute (free tier)

FIRESTORE_COLLECTION = "movies"
FIRESTORE_BATCH_SIZE = 500  # max docs per Firestore batch commit

CACHE_DIR = Path("data")
CACHE_FILE = CACHE_DIR / "tmdb_movies.json"
EMBEDDINGS_CACHE_FILE = CACHE_DIR / "embeddings.json"

DIRECTOR_WORKERS = 4  # threads for parallel director fetching


# ---------------------------------------------------------------------------
# Stage 1: Fetch movies from TMDB
# ---------------------------------------------------------------------------

def fetch_genre_map(api_key: str) -> dict[int, str]:
    """Fetch TMDB genre ID -> name mapping."""
    url = f"{TMDB_BASE_URL}/genre/movie/list"
    resp = requests.get(url, params={"api_key": api_key, "language": "en-US"})
    resp.raise_for_status()
    return {g["id"]: g["name"] for g in resp.json()["genres"]}


def fetch_director(api_key: str, movie_id: int) -> str:
    """Fetch the director name for a given movie ID from TMDB credits."""
    url = f"{TMDB_BASE_URL}/movie/{movie_id}/credits"
    try:
        resp = requests.get(url, params={"api_key": api_key})
        resp.raise_for_status()
        crew = resp.json().get("crew", [])
        for member in crew:
            if member.get("job") == "Director":
                return member.get("name", "Unknown")
    except Exception:
        pass
    return "Unknown"


def fetch_movies_from_tmdb(api_key: str) -> list[dict]:
    """Fetch top 10,000 movies from TMDB /discover/movie endpoint."""
    print("\n📥 Stage 1: Fetching movies from TMDB...")

    # Step 1: Genre map
    genre_map = fetch_genre_map(api_key)
    print(f"  Loaded {len(genre_map)} genres")

    # Step 2: Discover movies (paginated)
    movies = []
    seen_ids = set()

    for page in tqdm(range(1, TMDB_TOTAL_PAGES + 1), desc="  Fetching pages"):
        url = f"{TMDB_BASE_URL}/discover/movie"
        params = {
            "api_key": api_key,
            "sort_by": "popularity.desc",
            "language": "en-US",
            "page": page,
            "include_adult": "false",
        }
        try:
            resp = requests.get(url, params=params)
            resp.raise_for_status()
            results = resp.json().get("results", [])
        except Exception as e:
            print(f"\n  ⚠️  Error on page {page}: {e}")
            time.sleep(1)
            continue

        for movie in results:
            tmdb_id = movie.get("id")
            if not tmdb_id or tmdb_id in seen_ids:
                continue
            seen_ids.add(tmdb_id)

            # Extract release year
            release_date = movie.get("release_date", "")
            release_year = int(release_date[:4]) if release_date and len(release_date) >= 4 else 0

            # Map genre IDs to names
            genre_ids = movie.get("genre_ids", [])
            genres = ", ".join(genre_map.get(gid, "") for gid in genre_ids if gid in genre_map)

            # Build poster URL
            poster_path = movie.get("poster_path", "")
            poster_url = f"{TMDB_POSTER_BASE}{poster_path}" if poster_path else ""

            movies.append({
                "tmdb_id": tmdb_id,
                "title": movie.get("title", "Unknown"),
                "overview": movie.get("overview", ""),
                "genres": genres,
                "director": "",  # populated in next step
                "poster_url": poster_url,
                "release_year": release_year,
            })

        time.sleep(TMDB_DELAY)

    print(f"  Fetched {len(movies)} unique movies")

    # Step 3: Fetch directors in parallel
    print(f"  Fetching directors with {DIRECTOR_WORKERS} threads...")
    with ThreadPoolExecutor(max_workers=DIRECTOR_WORKERS) as executor:
        future_to_idx = {}
        for i, movie in enumerate(movies):
            future = executor.submit(fetch_director, api_key, movie["tmdb_id"])
            future_to_idx[future] = i

        for future in tqdm(as_completed(future_to_idx), total=len(future_to_idx), desc="  Directors"):
            idx = future_to_idx[future]
            try:
                movies[idx]["director"] = future.result()
            except Exception:
                movies[idx]["director"] = "Unknown"

    return movies


def save_cache(movies: list[dict]) -> None:
    """Save movies to local JSON cache."""
    CACHE_DIR.mkdir(exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(movies, f)
    print(f"  💾 Cached {len(movies)} movies to {CACHE_FILE}")


def load_cache() -> list[dict] | None:
    """Load movies from local JSON cache if it exists."""
    if CACHE_FILE.exists():
        with open(CACHE_FILE, "r") as f:
            movies = json.load(f)
        print(f"  📂 Loaded {len(movies)} movies from cache ({CACHE_FILE})")
        return movies
    return None


# ---------------------------------------------------------------------------
# Stage 2: Generate embeddings with Gemini
# ---------------------------------------------------------------------------

def format_embedding_text(movie: dict) -> str:
    """Format a movie into a single text string for embedding."""
    title = movie["title"]
    year = movie["release_year"] if movie["release_year"] else "Unknown year"
    director = movie["director"] if movie["director"] else "Unknown"
    genres = movie["genres"] if movie["genres"] else "Unknown genre"
    overview = movie["overview"] if movie["overview"] else ""

    return f"{title} ({year}). Directed by {director}. Genres: {genres}. {overview}"


def generate_embeddings(movies: list[dict], api_key: str) -> list[list[float]]:
    """Generate embeddings for all movies using Gemini text-embedding-004."""
    print(f"\n🧠 Stage 2: Generating embeddings with {GEMINI_EMBEDDING_MODEL}...")

    client = genai.Client(api_key=api_key)

    # Prepare all texts
    texts = [format_embedding_text(m) for m in movies]

    all_embeddings = []
    total_batches = (len(texts) + GEMINI_BATCH_SIZE - 1) // GEMINI_BATCH_SIZE
    request_times = []  # track timestamps for rate limiting

    for i in tqdm(range(0, len(texts), GEMINI_BATCH_SIZE), total=total_batches, desc="  Embedding batches"):
        batch = texts[i : i + GEMINI_BATCH_SIZE]

        # Rate limiting: ensure we don't exceed GEMINI_RPM_LIMIT requests per 60s
        now = time.time()
        request_times = [t for t in request_times if now - t < 60]
        if len(request_times) >= GEMINI_RPM_LIMIT:
            wait_time = 60 - (now - request_times[0]) + 1
            print(f"\n  ⏳ Rate limit reached, waiting {wait_time:.0f}s...")
            time.sleep(wait_time)

        try:
            result = client.models.embed_content(
                model=GEMINI_EMBEDDING_MODEL,
                contents=batch,
                config=types.EmbedContentConfig(output_dimensionality=768),
            )
            request_times.append(time.time())

            for embedding in result.embeddings:
                all_embeddings.append(list(embedding.values))

        except Exception as e:
            print(f"\n  ⚠️  Embedding error at batch {i // GEMINI_BATCH_SIZE}: {e}")
            print("  Retrying in 60s...")
            time.sleep(60)
            # Retry once
            try:
                result = client.models.embed_content(
                    model=GEMINI_EMBEDDING_MODEL,
                    contents=batch,
                    config=types.EmbedContentConfig(output_dimensionality=768),
                )
                request_times.append(time.time())
                for embedding in result.embeddings:
                    all_embeddings.append(list(embedding.values))
            except Exception as e2:
                print(f"\n  ❌ Retry failed: {e2}")
                # Fill with empty embeddings to maintain alignment
                for _ in batch:
                    all_embeddings.append([])

    print(f"  Generated {len(all_embeddings)} embeddings")

    # Validation
    valid_count = sum(1 for e in all_embeddings if len(e) == 768)
    print(f"  ✅ {valid_count}/{len(all_embeddings)} embeddings have correct dimension (768)")

    return all_embeddings


def save_embeddings_cache(embeddings: list[list[float]]) -> None:
    """Save embeddings to local JSON cache."""
    CACHE_DIR.mkdir(exist_ok=True)
    with open(EMBEDDINGS_CACHE_FILE, "w") as f:
        json.dump(embeddings, f)
    print(f"  💾 Cached {len(embeddings)} embeddings to {EMBEDDINGS_CACHE_FILE}")


def load_embeddings_cache() -> list[list[float]] | None:
    """Load embeddings from local JSON cache if it exists."""
    if EMBEDDINGS_CACHE_FILE.exists():
        with open(EMBEDDINGS_CACHE_FILE, "r") as f:
            embeddings = json.load(f)
        print(f"  📂 Loaded {len(embeddings)} embeddings from cache ({EMBEDDINGS_CACHE_FILE})")
        return embeddings
    return None


# ---------------------------------------------------------------------------
# Stage 3: Write to Firestore
# ---------------------------------------------------------------------------

def write_to_firestore(movies: list[dict], embeddings: list[list[float]], project_id: str) -> None:
    """Write movies with embeddings to Firestore collection."""
    print(f"\n🔥 Stage 3: Writing to Firestore (project: {project_id})...")

    db = firestore.Client(project=project_id)
    collection_ref = db.collection(FIRESTORE_COLLECTION)

    # Filter out movies with invalid embeddings
    valid_pairs = [
        (movie, emb) for movie, emb in zip(movies, embeddings) if len(emb) == 768
    ]
    print(f"  Writing {len(valid_pairs)} documents (skipped {len(movies) - len(valid_pairs)} with bad embeddings)")

    # Batch write
    written = 0
    for i in tqdm(range(0, len(valid_pairs), FIRESTORE_BATCH_SIZE), desc="  Batch writes"):
        batch = db.batch()
        chunk = valid_pairs[i : i + FIRESTORE_BATCH_SIZE]

        for movie, embedding in chunk:
            doc_id = f"tmdb_{movie['tmdb_id']}"
            doc_ref = collection_ref.document(doc_id)

            doc_data = {
                "title": movie["title"],
                "tmdb_id": movie["tmdb_id"],
                "release_year": movie["release_year"],
                "genres": movie["genres"],
                "director": movie["director"],
                "poster_url": movie["poster_url"],
                "overview": movie["overview"],
                "embedding": Vector(embedding),
            }

            batch.set(doc_ref, doc_data)

        batch.commit()
        written += len(chunk)

    print(f"  ✅ Wrote {written} documents to Firestore collection '{FIRESTORE_COLLECTION}'")


# ---------------------------------------------------------------------------
# Test: Vector search sanity check
# ---------------------------------------------------------------------------

def run_test_query(project_id: str, gemini_api_key: str) -> None:
    """Run a test vector search query to verify the pipeline."""
    print("\n🔍 Running test vector search...")

    test_query = "dark psychological thriller"
    print(f"  Query: \"{test_query}\"")

    # Generate query embedding
    client = genai.Client(api_key=gemini_api_key)
    result = client.models.embed_content(
        model=GEMINI_EMBEDDING_MODEL,
        contents=test_query,
        config=types.EmbedContentConfig(output_dimensionality=768),
    )
    query_vector = list(result.embeddings[0].values)
    print(f"  Query embedding dimension: {len(query_vector)}")

    # Query Firestore
    db = firestore.Client(project=project_id)
    collection_ref = db.collection(FIRESTORE_COLLECTION)

    vector_query = collection_ref.find_nearest(
        vector_field="embedding",
        query_vector=Vector(query_vector),
        distance_measure=DistanceMeasure.COSINE,
        limit=5,
    )

    docs = vector_query.get()

    print(f"\n  Top 5 results for \"{test_query}\":")
    print(f"  {'─' * 60}")
    for i, doc in enumerate(docs, 1):
        data = doc.to_dict()
        title = data.get("title", "?")
        year = data.get("release_year", "?")
        genres = data.get("genres", "?")
        director = data.get("director", "?")
        print(f"  {i}. {title} ({year})")
        print(f"     Director: {director} | Genres: {genres}")

    # Spot-check random document metadata
    print(f"\n  📋 Spot-checking 3 random documents...")
    import random
    all_docs = list(collection_ref.limit(100).stream())
    samples = random.sample(all_docs, min(3, len(all_docs)))
    for doc in samples:
        data = doc.to_dict()
        has_embedding = "embedding" in data
        print(f"  • {data.get('title', '?')} ({data.get('release_year', '?')}) "
              f"- Director: {data.get('director', '?')} "
              f"- Poster: {'✓' if data.get('poster_url') else '✗'} "
              f"- Embedding: {'✓' if has_embedding else '✗'}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="TMDB Movie Ingestion for Letterboxd RAG Recommender")
    parser.add_argument("--test", action="store_true", help="Run a test vector search after ingestion")
    parser.add_argument("--resume", action="store_true", help="Resume from cached TMDB data if available")
    parser.add_argument("--test-only", action="store_true", help="Only run the test query (skip ingestion)")
    args = parser.parse_args()

    # Load environment
    load_dotenv()
    tmdb_key = os.getenv("TMDB_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    project_id = os.getenv("GCP_PROJECT_ID")

    if not tmdb_key:
        print("❌ TMDB_API_KEY not set in .env")
        sys.exit(1)
    if not gemini_key:
        print("❌ GEMINI_API_KEY not set in .env")
        sys.exit(1)
    if not project_id:
        print("❌ GCP_PROJECT_ID not set in .env")
        sys.exit(1)

    print("=" * 60)
    print("🎬 Letterboxd RAG Movie Recommender — Data Ingestion")
    print("=" * 60)
    print(f"  Project: {project_id}")
    print(f"  Embedding model: {GEMINI_EMBEDDING_MODEL}")
    print(f"  Target: ~{TMDB_TOTAL_PAGES * 20:,} movies")

    if args.test_only:
        run_test_query(project_id, gemini_key)
        return

    # Stage 1: Fetch from TMDB (or load cache)
    movies = None
    if args.resume:
        movies = load_cache()

    if movies is None:
        movies = fetch_movies_from_tmdb(tmdb_key)
        save_cache(movies)

    # Validation
    assert len(movies) >= 9500, f"Expected ≥9,500 movies, got {len(movies)}"
    print(f"\n  ✅ TMDB fetch complete: {len(movies)} movies")

    # Stage 2: Generate embeddings (or load cache)
    embeddings = None
    if args.resume:
        embeddings = load_embeddings_cache()

    if embeddings is None:
        embeddings = generate_embeddings(movies, gemini_key)
        save_embeddings_cache(embeddings)

    # Stage 3: Write to Firestore
    write_to_firestore(movies, embeddings, project_id)

    # Summary
    print("\n" + "=" * 60)
    print("✅ Ingestion complete!")
    print(f"  Movies fetched: {len(movies)}")
    valid_embeddings = sum(1 for e in embeddings if len(e) == 768)
    print(f"  Valid embeddings: {valid_embeddings}")
    print(f"  Firestore collection: {FIRESTORE_COLLECTION}")
    print("=" * 60)

    # Optional test
    if args.test:
        run_test_query(project_id, gemini_key)

    print("\n⚠️  Don't forget to create the vector index! Run:")
    print(f'  gcloud firestore indexes composite create \\')
    print(f'    --collection-group={FIRESTORE_COLLECTION} \\')
    print(f'    --query-scope=COLLECTION \\')
    print(f'    --field-config=vector-config=\'{{"dimension":"768","flat": {{}}}}\',field-path=embedding')


if __name__ == "__main__":
    main()
