/**
 * Letterboxd CSV → typed payload mapping.
 *
 * Letterboxd exports columns: Date, Name, Year, Letterboxd URI, Rating, Review.
 * We only consume Name, Year, Rating, Review. See sample_user_data/ for examples.
 *
 * Each parser is a pure function so it can be unit-tested without a DOM.
 */

import Papa from "papaparse";
import type {
  RatedMovie,
  ReviewedMovie,
  UserData,
  WatchedMovie,
} from "./types";
import { MAX_ENTRIES_PER_LIST } from "./constants";

export type CsvKind = "watched" | "ratings" | "reviews";

export interface ParseResult<T> {
  rows: T[];
  /** Rows we couldn't parse — typically missing Name or Year. */
  skipped: number;
}

interface RawRow {
  Name?: string;
  Year?: string;
  Rating?: string;
  Review?: string;
}

const REQUIRED_HEADERS: Record<CsvKind, readonly string[]> = {
  watched: ["Name", "Year"],
  ratings: ["Name", "Year", "Rating"],
  reviews: ["Name", "Year"],
};

/** Throws if the CSV is missing required Letterboxd columns. */
export function assertHeaders(kind: CsvKind, headers: string[]): void {
  const required = REQUIRED_HEADERS[kind];
  const missing = required.filter((h) => !headers.includes(h));
  if (missing.length > 0) {
    throw new Error(
      `${kind}.csv is missing required column(s): ${missing.join(", ")}. ` +
        `Make sure you exported the data from Letterboxd → Settings → Data.`,
    );
  }
}

function cleanName(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function toYear(value: unknown): number {
  const n = typeof value === "string" ? parseInt(value, 10) : NaN;
  return Number.isFinite(n) ? n : 0;
}

function toRating(value: unknown): number {
  const n = typeof value === "string" ? parseFloat(value) : NaN;
  if (!Number.isFinite(n)) return 0;
  // Clamp to backend's accepted range [0, 5]
  return Math.max(0, Math.min(5, n));
}

function cleanReview(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

export function mapWatchedRows(rows: RawRow[]): ParseResult<WatchedMovie> {
  const out: WatchedMovie[] = [];
  let skipped = 0;
  for (const row of rows) {
    const name = cleanName(row.Name);
    const year = toYear(row.Year);
    if (!name) {
      skipped++;
      continue;
    }
    out.push({ name, year });
    if (out.length >= MAX_ENTRIES_PER_LIST) break;
  }
  return { rows: out, skipped };
}

export function mapRatingsRows(rows: RawRow[]): ParseResult<RatedMovie> {
  const out: RatedMovie[] = [];
  let skipped = 0;
  for (const row of rows) {
    const name = cleanName(row.Name);
    const year = toYear(row.Year);
    const rating = toRating(row.Rating);
    if (!name) {
      skipped++;
      continue;
    }
    out.push({ name, year, rating });
    if (out.length >= MAX_ENTRIES_PER_LIST) break;
  }
  return { rows: out, skipped };
}

export function mapReviewsRows(rows: RawRow[]): ParseResult<ReviewedMovie> {
  const out: ReviewedMovie[] = [];
  let skipped = 0;
  for (const row of rows) {
    const name = cleanName(row.Name);
    const year = toYear(row.Year);
    const rating = toRating(row.Rating);
    const review = cleanReview(row.Review);
    if (!name) {
      skipped++;
      continue;
    }
    // Skip rows with no review text — they add no signal and waste payload size
    if (!review) {
      skipped++;
      continue;
    }
    out.push({ name, year, rating, review });
    if (out.length >= MAX_ENTRIES_PER_LIST) break;
  }
  return { rows: out, skipped };
}

/**
 * Parse a single CSV File via PapaParse. Resolves with both the mapped
 * typed rows and the count of rows that couldn't be parsed.
 */
export function parseCsvFile<T>(
  file: File,
  kind: CsvKind,
  mapper: (rows: RawRow[]) => ParseResult<T>,
): Promise<ParseResult<T>> {
  return new Promise((resolve, reject) => {
    Papa.parse<RawRow>(file, {
      header: true,
      skipEmptyLines: true,
      complete: (results) => {
        try {
          assertHeaders(kind, results.meta.fields ?? []);
          resolve(mapper(results.data));
        } catch (err) {
          reject(err);
        }
      },
      error: (err) => reject(err),
    });
  });
}

/** Convenience helpers wired to the right mapper per kind. */
export const parseWatchedCsv = (file: File) =>
  parseCsvFile(file, "watched", mapWatchedRows);
export const parseRatingsCsv = (file: File) =>
  parseCsvFile(file, "ratings", mapRatingsRows);
export const parseReviewsCsv = (file: File) =>
  parseCsvFile(file, "reviews", mapReviewsRows);

/** Build an empty UserData (used as a sensible initial state). */
export function emptyUserData(): UserData {
  return { watched: [], ratings: [], reviews: [] };
}
