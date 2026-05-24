"use client";

import { useCallback, useState } from "react";
import { useDropzone, type FileRejection } from "react-dropzone";
import { CheckCircle2, FileWarning, Trash2, Upload } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { MAX_FILE_SIZE_BYTES } from "@/lib/constants";
import {
  parseRatingsCsv,
  parseReviewsCsv,
  parseWatchedCsv,
} from "@/lib/csv-parser";
import { useUserData } from "@/lib/use-user-data";
import { cn } from "@/lib/utils";

export function CsvUpload() {
  const { data, setData, clear } = useUserData();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFiles = useCallback(
    async (files: File[]) => {
      if (files.length === 0) return;
      setBusy(true);
      setError(null);
      try {
        let next = { ...data };
        for (const file of files) {
          const name = file.name.toLowerCase();
          if (name === "watched.csv") {
            const result = await parseWatchedCsv(file);
            next = { ...next, watched: result.rows };
          } else if (name === "ratings.csv") {
            const result = await parseRatingsCsv(file);
            next = { ...next, ratings: result.rows };
          } else if (name === "reviews.csv") {
            const result = await parseReviewsCsv(file);
            next = { ...next, reviews: result.rows };
          } else {
            throw new Error(
              `Unrecognized file "${file.name}". Expected watched.csv, ratings.csv, or reviews.csv.`,
            );
          }
        }
        setData(next);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to parse CSV.");
      } finally {
        setBusy(false);
      }
    },
    [data, setData],
  );

  const onDrop = useCallback(
    (accepted: File[], rejected: FileRejection[]) => {
      if (rejected.length > 0) {
        const first = rejected[0];
        const reason = first.errors[0]?.message ?? "File rejected.";
        setError(`${first.file.name}: ${reason}`);
        return;
      }
      void handleFiles(accepted);
    },
    [handleFiles],
  );

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    accept: { "text/csv": [".csv"] },
    maxSize: MAX_FILE_SIZE_BYTES,
    noClick: true,
    multiple: true,
  });

  const handleClear = () => {
    clear();
    setError(null);
  };

  const hasAnyData =
    data.watched.length > 0 ||
    data.ratings.length > 0 ||
    data.reviews.length > 0;

  return (
    <Card className="w-full">
      <CardContent className="space-y-4 p-5">
        <div
          {...getRootProps({
            className: cn(
              "flex flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed px-4 py-8 text-center transition-colors",
              "border-border bg-muted/30 hover:bg-muted/50",
              isDragActive && "border-primary bg-primary/5",
              busy && "opacity-60 pointer-events-none",
            ),
          })}
        >
          <input {...getInputProps()} aria-label="Letterboxd CSV files" />
          <Upload className="h-6 w-6 text-muted-foreground" aria-hidden />
          <div className="space-y-1">
            <p className="text-sm font-medium">
              Drop your Letterboxd CSVs here
            </p>
            <p className="text-xs text-muted-foreground">
              Expected files:{" "}
              <code className="font-mono">watched.csv</code>,{" "}
              <code className="font-mono">ratings.csv</code>,{" "}
              <code className="font-mono">reviews.csv</code>
            </p>
          </div>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={open}
            disabled={busy}
          >
            {busy ? "Parsing…" : "Choose files"}
          </Button>
          <p className="text-xs text-muted-foreground/80 pt-2">
            Export from{" "}
            <a
              className="underline underline-offset-2 hover:text-foreground"
              href="https://letterboxd.com/settings/data/"
              target="_blank"
              rel="noopener noreferrer"
            >
              Letterboxd → Settings → Data
            </a>
            .
          </p>
        </div>

        {error && (
          <div
            role="alert"
            className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive"
          >
            <FileWarning className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
            <span>{error}</span>
          </div>
        )}

        {hasAnyData ? (
          <div className="flex flex-wrap items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-600" aria-hidden />
            <Badge variant="secondary">
              {data.watched.length.toLocaleString()} watched
            </Badge>
            <Badge variant="secondary">
              {data.ratings.length.toLocaleString()} rated
            </Badge>
            <Badge variant="secondary">
              {data.reviews.length.toLocaleString()} reviewed
            </Badge>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              className="ml-auto text-muted-foreground"
              onClick={handleClear}
            >
              <Trash2 className="mr-1 h-3.5 w-3.5" aria-hidden />
              Clear
            </Button>
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">
            Tip: at minimum drop <code>watched.csv</code> so we don&apos;t
            recommend movies you&apos;ve already seen. Add{" "}
            <code>ratings.csv</code> and <code>reviews.csv</code> for taste
            personalization.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
