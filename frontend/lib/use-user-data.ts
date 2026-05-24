"use client";

import { useCallback, useSyncExternalStore } from "react";

import { USER_DATA_STORAGE_KEY } from "./constants";
import { emptyUserData } from "./csv-parser";
import { loadUserData, saveUserData, clearUserData } from "./storage";
import type { UserData } from "./types";

/**
 * `useSyncExternalStore`-backed hook that reads/writes the user's parsed
 * Letterboxd data in localStorage and stays in sync across components.
 *
 * Uses a single cached snapshot so identical reads return reference-equal
 * values (required by useSyncExternalStore to avoid render loops).
 */

const SSR_SNAPSHOT: UserData = emptyUserData();
let cachedSnapshot: UserData | null = null;

function snapshot(): UserData {
  if (cachedSnapshot === null) cachedSnapshot = loadUserData();
  return cachedSnapshot;
}

function invalidate(): void {
  cachedSnapshot = null;
  listeners.forEach((l) => l());
}

const listeners = new Set<() => void>();

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  const onStorage = (e: StorageEvent) => {
    if (e.key === USER_DATA_STORAGE_KEY) invalidate();
  };
  if (typeof window !== "undefined") {
    window.addEventListener("storage", onStorage);
  }
  return () => {
    listeners.delete(listener);
    if (typeof window !== "undefined") {
      window.removeEventListener("storage", onStorage);
    }
  };
}

export function useUserData(): {
  data: UserData;
  setData: (next: UserData) => void;
  clear: () => void;
} {
  const data = useSyncExternalStore(subscribe, snapshot, () => SSR_SNAPSHOT);

  const setData = useCallback((next: UserData) => {
    saveUserData(next);
    invalidate();
  }, []);

  const clear = useCallback(() => {
    clearUserData();
    invalidate();
  }, []);

  return { data, setData, clear };
}
