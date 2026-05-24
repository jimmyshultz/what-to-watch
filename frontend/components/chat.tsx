"use client";

import { useCallback, useRef, useState } from "react";

import { ApiError, fetchRecommendations } from "@/lib/api";
import type { ChatMessage } from "@/lib/types";
import { useUserData } from "@/lib/use-user-data";
import { ChatInput, type ChatInputHandle } from "./chat-input";
import { CsvUpload } from "./csv-upload";
import { MessageList } from "./message-list";

let messageCounter = 0;
const nextId = () => `m-${++messageCounter}-${Date.now()}`;

export function Chat() {
  const { data: userData } = useUserData();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const inputRef = useRef<ChatInputHandle | null>(null);

  const hasUserData =
    userData.watched.length > 0 ||
    userData.ratings.length > 0 ||
    userData.reviews.length > 0;

  const handleSubmit = useCallback(
    async (query: string) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      const userMsg: ChatMessage = {
        id: nextId(),
        role: "user",
        content: query,
      };
      setMessages((m) => [...m, userMsg]);
      setBusy(true);

      try {
        const response = await fetchRecommendations(
          {
            query,
            watched: userData.watched,
            ratings: userData.ratings,
            reviews: userData.reviews,
          },
          controller.signal,
        );
        setMessages((m) => [
          ...m,
          {
            id: nextId(),
            role: "assistant",
            content: "",
            recommendations: response.recommendations,
          },
        ]);
      } catch (err) {
        if ((err as Error).name === "AbortError") {
          // Silent — user cancelled
        } else {
          setMessages((m) => [
            ...m,
            { id: nextId(), role: "error", content: errorMessageFor(err) },
          ]);
        }
      } finally {
        if (abortRef.current === controller) {
          abortRef.current = null;
          setBusy(false);
        }
      }
    },
    [userData],
  );

  const handleCancel = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setBusy(false);
  }, []);

  const handleExampleClick = useCallback((prompt: string) => {
    inputRef.current?.setValue(prompt);
  }, []);

  return (
    <div className="flex flex-1 flex-col">
      <header className="border-b">
        <div className="mx-auto max-w-3xl px-4 py-4 space-y-3">
          <div>
            <h1 className="text-xl font-semibold tracking-tight">
              What to Watch
            </h1>
            <p className="text-xs text-muted-foreground">
              Personalized picks from your Letterboxd taste.
            </p>
          </div>
          <CsvUpload />
        </div>
      </header>
      <MessageList
        messages={messages}
        busy={busy}
        onExampleClick={handleExampleClick}
        hasUserData={hasUserData}
      />
      <ChatInput
        ref={inputRef}
        onSubmit={handleSubmit}
        onCancel={handleCancel}
        busy={busy}
        disabled={!hasUserData}
        disabledReason="Upload your Letterboxd data first."
      />
    </div>
  );
}

function errorMessageFor(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 429) {
      return "You've hit the rate limit. Try again in a few minutes.";
    }
    if (err.status === 400) {
      return err.message;
    }
    if (err.status === 0) {
      return err.message;
    }
    return "Something went wrong on the server. Try again.";
  }
  return "Unexpected error. Try again.";
}
