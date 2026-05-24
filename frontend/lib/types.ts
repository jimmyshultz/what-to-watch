/**
 * TypeScript mirrors of the backend Pydantic schemas
 * (see backend/models/schemas.py).
 *
 * Keep these in sync with the backend. The /api/recommend contract is:
 *   POST { query, watched, ratings, reviews } -> { query, recommendations[] }
 */

export interface WatchedMovie {
  name: string;
  year: number;
}

export interface RatedMovie {
  name: string;
  year: number;
  rating: number; // 0–5
}

export interface ReviewedMovie {
  name: string;
  year: number;
  rating: number; // 0–5
  review: string;
}

export interface RecommendRequest {
  query: string;
  watched: WatchedMovie[];
  ratings: RatedMovie[];
  reviews: ReviewedMovie[];
}

export interface MovieRecommendation {
  title: string;
  tmdb_id: number;
  release_year: number;
  genres: string;
  director: string;
  poster_url: string;
  explanation: string;
}

export interface RecommendResponse {
  recommendations: MovieRecommendation[];
  query: string;
}

/** Parsed Letterboxd CSV data ready to be sent to the API. */
export interface UserData {
  watched: WatchedMovie[];
  ratings: RatedMovie[];
  reviews: ReviewedMovie[];
}

/** Chat message kinds rendered in the conversation. */
export type ChatMessage =
  | { id: string; role: "user"; content: string }
  | {
      id: string;
      role: "assistant";
      content: string; // optional intro / error text
      recommendations: MovieRecommendation[];
    }
  | { id: string; role: "error"; content: string };
