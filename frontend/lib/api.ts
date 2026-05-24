/** Thin client for the FastAPI backend's /api/recommend endpoint. */

import type { RecommendRequest, RecommendResponse } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

/**
 * Error subclass that carries the HTTP status so the UI can render a
 * specific message for 400 / 429 / 5xx without parsing strings.
 */
export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

export async function fetchRecommendations(
  request: RecommendRequest,
  signal?: AbortSignal,
): Promise<RecommendResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/recommend`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
      signal,
    });
  } catch (err) {
    // Network failure, CORS rejection, or abort
    if ((err as Error).name === "AbortError") throw err;
    throw new ApiError(
      0,
      "Couldn't reach the recommendation service. Is the backend running?",
    );
  }

  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      // Body wasn't JSON — keep the default detail
    }
    throw new ApiError(response.status, detail);
  }

  return (await response.json()) as RecommendResponse;
}
