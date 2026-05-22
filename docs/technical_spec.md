Technical Specification: Letterboxd RAG Movie Recommender
1. Architecture & Tech Stack

Goal: Build a mobile-friendly React web application powered by a serverless Google Cloud backend, utilizing RAG to recommend movies based on a user's Letterboxd data and the TMDB API. Cost must remain strictly under $5/month.

    Frontend: React (Next.js App Router, Tailwind CSS for mobile-first styling).

    Backend/API: A serverless Python architecture (FastAPI) to handle native data processing capabilities (Pandas) needed for CSV parsing and vector embeddings.

    Hosting: * Frontend: Vercel (Hobby Tier - Free).

        Backend: Google Cloud Run (Free tier allows 2 million requests/month; scales to zero to cost nothing when idle).

    Vector Database: Firestore Native Vector Search (GCP-native, free Spark tier: 1GB storage, 50K reads/day, 20K writes/day). Eliminates the need for a third-party vector DB.

    External Data: TMDB API (Free for non-commercial).

    LLM & Embeddings: Google Gemini API (Free tier offers 15 requests per minute). The backend must enforce per-user rate limiting and daily quotas to ensure usage stays within free tier limits.

2. Implementation Phases
Phase 1: Local Setup & Data Ingestion (The Knowledge Base)

Objective: Build the external pool of movies the chatbot will recommend from.

    TMDB Script: Write a standalone Python script to fetch the top 10,000 most popular movies from the TMDB API. Extract: TMDB ID, Title, Overview (plot summary), Genres, Director, and Poster URL.

    Generate Embeddings: Concatenate the Title, Overview, and Genres into a single text string for each movie. Pass this string to the Gemini text-embedding-004 model to generate a vector embedding.

    Populate Vector DB: Write these embeddings along with the associated metadata (Title, ID, Poster URL) into a Firestore collection, using Firestore's native vector search capability.

Phase 2: Backend Development (Cloud Run API)

Objective: Build the serverless API that processes the user's personal data and handles the RAG logic.

    Initialize FastAPI App: Create a lightweight Python API with an endpoint /api/recommend.

    Letterboxd Parsing Logic: Implement a utility to accept the parsed user data.

        Accept the watched.csv data to create an exclusion list.

        Accept the ratings.csv and reviews.csv data to identify the user's top-rated movies to establish their baseline taste profile.

    The RAG Pipeline: When a user submits a query (e.g., "Give me a dark sci-fi thriller"):

        Generate a vector embedding of the user's query.

        Query Firestore vector search to retrieve the top 20 semantically similar movies.

        Cross-reference the retrieved movies against the watched exclusion list and drop any matches.

    LLM Generation: Pass the remaining top 5 unwatched movies to the Gemini 2.5 Flash LLM. Instruct the LLM via system prompt to act as an expert film critic. The prompt must inject the user's top-rated movies as context, instructing the model to pick the best fit from the 5 unwatched options and explain why it matches their specific taste.

    Security & Guardrails (implement during Phase 2):

        Prompt Injection Protection: Sanitize and validate all user input before injecting into LLM prompts. Use a strict system prompt that instructs the model to refuse non-movie-related queries.

        Rate Limiting: Enforce per-session rate limits on the /api/recommend endpoint (e.g., max 10 requests per session, max 50 per day per IP) to prevent abuse and keep Gemini API usage within the free tier.

        Input Validation: Reject excessively long queries, non-text input, and any attempts to override the system prompt.

        Content Filtering: Leverage Gemini's built-in safety filters and add server-side validation to block harmful or off-topic responses.

Phase 3: Frontend Development (Next.js on Vercel)

Objective: Build the user interface.

    Initialization: Scaffold a Next.js app optimized for mobile viewports using Tailwind CSS.

    Data Upload Component: Create a drag-and-drop or file selection zone where the user can upload their Letterboxd .csv files.

    Chat Interface: Build a standard chat UI with message bubbles for the user's prompt and the bot's response. Manage state using standard React hooks.

    Movie Cards: When the bot recommends a movie, render a visually appealing card displaying the TMDB Poster, Title, Year, and the LLM's personalized explanation of why it was chosen.

Phase 4: Deployment & Cloud Configuration

Objective: Push to production.

    Backend Deployment: Containerize the Python FastAPI backend using Docker and deploy it to Google Cloud Run. Set it to allow unauthenticated invocations and scale down to 0 instances to prevent idle billing. Set up CORS to accept requests exclusively from your Vercel production domain.

    Frontend Deployment: Push the Next.js repository to GitHub. Connect the repository to Vercel via the Vercel dashboard. Vercel will automatically detect the Next.js framework, build the app, and deploy it to a live URL on every push to the main branch.

    Secrets Management: * Store Backend API Keys (Gemini, TMDB) securely in Google Cloud Secret Manager and expose them as environment variables to the Cloud Run instance.

        Store Frontend variables (like the Cloud Run API URL) securely in the Vercel dashboard's Environment Variables settings.