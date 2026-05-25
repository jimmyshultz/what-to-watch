"""FastAPI application entry point for the Letterboxd RAG Movie Recommender."""

import logging

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from middleware.rate_limiter import RateLimiterMiddleware
from routers.recommend import router as recommend_router

# Configure logging for Cloud Run
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(name)s - %(message)s")

# Load .env in local development (ignored in Cloud Run where env vars are set directly)
load_dotenv()

app = FastAPI(
    title="What to Watch — Movie Recommender API",
    description="RAG-powered movie recommendation engine using Letterboxd data and Gemini.",
    version="0.1.0",
)

# CORS — Vercel production + local dev only. Preview deployments are
# intentionally excluded; test previews against a local backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://what-to-watch-jimmyshultz-jimmy-shultzs-projects.vercel.app",
        "http://localhost:3000",  # Next.js dev server
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
app.add_middleware(RateLimiterMiddleware)

# Routers
app.include_router(recommend_router, prefix="/api")


@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run and monitoring."""
    return {"status": "ok"}
