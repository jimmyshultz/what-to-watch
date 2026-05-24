import { describe, expect, it } from "vitest";
import {
  assertHeaders,
  mapRatingsRows,
  mapReviewsRows,
  mapWatchedRows,
} from "./csv-parser";

describe("assertHeaders", () => {
  it("passes when all required Letterboxd columns are present", () => {
    expect(() =>
      assertHeaders("watched", ["Date", "Name", "Year", "Letterboxd URI"]),
    ).not.toThrow();
    expect(() =>
      assertHeaders("ratings", [
        "Date",
        "Name",
        "Year",
        "Letterboxd URI",
        "Rating",
      ]),
    ).not.toThrow();
  });

  it("throws when required columns are missing", () => {
    expect(() => assertHeaders("watched", ["Date", "Letterboxd URI"]))
      .toThrowError(/Name, Year/);
    expect(() => assertHeaders("ratings", ["Name", "Year"]))
      .toThrowError(/Rating/);
  });
});

describe("mapWatchedRows", () => {
  it("maps Name + Year and trims whitespace", () => {
    const result = mapWatchedRows([
      { Name: "  The Batman  ", Year: "2022" },
      { Name: "Inception", Year: "2010" },
    ]);
    expect(result.rows).toEqual([
      { name: "The Batman", year: 2022 },
      { name: "Inception", year: 2010 },
    ]);
    expect(result.skipped).toBe(0);
  });

  it("skips rows missing a name and reports the skip count", () => {
    const result = mapWatchedRows([
      { Name: "Inception", Year: "2010" },
      { Name: "", Year: "2020" },
      { Year: "2021" },
    ]);
    expect(result.rows).toHaveLength(1);
    expect(result.skipped).toBe(2);
  });

  it("defaults a missing/invalid Year to 0 rather than dropping the row", () => {
    const result = mapWatchedRows([
      { Name: "Mystery Movie", Year: "" },
      { Name: "Another One", Year: "not-a-year" },
    ]);
    expect(result.rows).toEqual([
      { name: "Mystery Movie", year: 0 },
      { name: "Another One", year: 0 },
    ]);
  });
});

describe("mapRatingsRows", () => {
  it("parses fractional Letterboxd ratings", () => {
    const result = mapRatingsRows([
      { Name: "Avatar: The Way of Water", Year: "2022", Rating: "3.5" },
      { Name: "Arrival", Year: "2016", Rating: "5" },
    ]);
    expect(result.rows).toEqual([
      { name: "Avatar: The Way of Water", year: 2022, rating: 3.5 },
      { name: "Arrival", year: 2016, rating: 5 },
    ]);
  });

  it("clamps ratings to the backend's [0, 5] range", () => {
    const result = mapRatingsRows([
      { Name: "Out of range high", Year: "2020", Rating: "9.0" },
      { Name: "Out of range low", Year: "2020", Rating: "-1" },
      { Name: "Bad input", Year: "2020", Rating: "abc" },
    ]);
    expect(result.rows.map((r) => r.rating)).toEqual([5, 0, 0]);
  });
});

describe("mapReviewsRows", () => {
  it("only keeps rows that have a review body", () => {
    const result = mapReviewsRows([
      {
        Name: "Small Things Like These",
        Year: "2024",
        Rating: "3",
        Review: "Excellent atmosphere; disjointed plot.",
      },
      { Name: "No review here", Year: "2024", Rating: "4", Review: "" },
      { Name: "Missing field", Year: "2024", Rating: "4" },
    ]);
    expect(result.rows).toEqual([
      {
        name: "Small Things Like These",
        year: 2024,
        rating: 3,
        review: "Excellent atmosphere; disjointed plot.",
      },
    ]);
    expect(result.skipped).toBe(2);
  });

  it("trims review whitespace", () => {
    const result = mapReviewsRows([
      {
        Name: "Foo",
        Year: "2020",
        Rating: "4",
        Review: "  loved it  ",
      },
    ]);
    expect(result.rows[0].review).toBe("loved it");
  });
});

describe("MAX_ENTRIES_PER_LIST cap", () => {
  it("does not exceed the backend's 10,000-entry array cap", async () => {
    const { MAX_ENTRIES_PER_LIST } = await import("./constants");
    const tooMany = Array.from({ length: MAX_ENTRIES_PER_LIST + 50 }, (_, i) => ({
      Name: `Movie ${i}`,
      Year: "2020",
    }));
    const result = mapWatchedRows(tooMany);
    expect(result.rows).toHaveLength(MAX_ENTRIES_PER_LIST);
  });
});
