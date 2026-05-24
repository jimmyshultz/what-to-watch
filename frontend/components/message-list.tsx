"use client";

import { useEffect, useRef } from "react";
import { AlertTriangle, Sparkles } from "lucide-react";

import { EXAMPLE_PROMPTS } from "@/lib/constants";
import type { ChatMessage } from "@/lib/types";
import { cn } from "@/lib/utils";
import { MovieCard, MovieCardSkeleton } from "./movie-card";

interface MessageListProps {
  messages: ChatMessage[];
  busy: boolean;
  onExampleClick: (prompt: string) => void;
  hasUserData: boolean;
}

export function MessageList({
  messages,
  busy,
  onExampleClick,
  hasUserData,
}: MessageListProps) {
  const endRef = useRef<HTMLDivElement | null>(null);

  // Auto-scroll to the latest message
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, busy]);

  if (messages.length === 0 && !busy) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-6 px-4 py-12 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
          <Sparkles className="h-5 w-5 text-muted-foreground" aria-hidden />
        </div>
        <div className="space-y-1.5 max-w-md">
          <h2 className="text-lg font-medium">
            {hasUserData
              ? "What are you in the mood for?"
              : "Upload your Letterboxd data to get started"}
          </h2>
          <p className="text-sm text-muted-foreground">
            {hasUserData
              ? "Try one of these to see what we can do:"
              : "Drop your CSVs above, then ask for a recommendation."}
          </p>
        </div>
        {hasUserData && (
          <div className="flex flex-wrap justify-center gap-2 max-w-lg">
            {EXAMPLE_PROMPTS.map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => onExampleClick(p)}
                className="rounded-full border bg-background px-3 py-1.5 text-sm hover:bg-accent transition-colors"
              >
                {p}
              </button>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div
      className="flex-1 overflow-y-auto px-4 py-4"
      aria-live="polite"
      aria-busy={busy}
    >
      <div className="mx-auto max-w-3xl space-y-6">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        {busy && (
          <div className="space-y-3" aria-label="Loading recommendations">
            <MovieCardSkeleton />
            <MovieCardSkeleton />
          </div>
        )}
        <div ref={endRef} />
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-br-md bg-primary text-primary-foreground px-4 py-2.5 text-sm">
          {message.content}
        </div>
      </div>
    );
  }

  if (message.role === "error") {
    return (
      <div
        role="alert"
        className="flex items-start gap-2 rounded-lg border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive"
      >
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
        <span>{message.content}</span>
      </div>
    );
  }

  // assistant
  return (
    <div className="space-y-3">
      {message.content && (
        <p className={cn("text-sm text-muted-foreground")}>{message.content}</p>
      )}
      {message.recommendations.length === 0 ? (
        <p className="text-sm text-muted-foreground italic">
          No recommendations matched — try a different query.
        </p>
      ) : (
        message.recommendations.map((rec) => (
          <MovieCard key={rec.tmdb_id} movie={rec} />
        ))
      )}
    </div>
  );
}
