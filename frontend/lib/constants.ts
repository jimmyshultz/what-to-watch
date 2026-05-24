/** Shared constants — keep in sync with backend limits. */

/** Backend caps each array at 10,000 entries (RecommendRequest schema). */
export const MAX_ENTRIES_PER_LIST = 10_000;

/** Backend caps query at 500 chars (RecommendRequest.query). */
export const MAX_QUERY_LENGTH = 500;

/** Per-file upload cap — defensive client-side check. */
export const MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024; // 5MB

/** localStorage key for the parsed Letterboxd data. */
export const USER_DATA_STORAGE_KEY = "wtw:userdata:v1";

/** Example prompts shown in the empty chat state. */
export const EXAMPLE_PROMPTS = [
  "A dark sci-fi thriller",
  "Something funny like Superbad",
  "A slow burn with stunning cinematography",
];
