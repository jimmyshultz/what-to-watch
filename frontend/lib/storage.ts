/** localStorage helpers for persisting parsed Letterboxd data. */

import { USER_DATA_STORAGE_KEY } from "./constants";
import { emptyUserData } from "./csv-parser";
import type { UserData } from "./types";

export function loadUserData(): UserData {
  if (typeof window === "undefined") return emptyUserData();
  try {
    const raw = window.localStorage.getItem(USER_DATA_STORAGE_KEY);
    if (!raw) return emptyUserData();
    const parsed = JSON.parse(raw) as Partial<UserData>;
    return {
      watched: Array.isArray(parsed.watched) ? parsed.watched : [],
      ratings: Array.isArray(parsed.ratings) ? parsed.ratings : [],
      reviews: Array.isArray(parsed.reviews) ? parsed.reviews : [],
    };
  } catch {
    return emptyUserData();
  }
}

export function saveUserData(data: UserData): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(USER_DATA_STORAGE_KEY, JSON.stringify(data));
  } catch {
    // Quota exceeded or storage disabled — swallow; user will just re-upload next time
  }
}

export function clearUserData(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(USER_DATA_STORAGE_KEY);
  } catch {
    // Ignore
  }
}
