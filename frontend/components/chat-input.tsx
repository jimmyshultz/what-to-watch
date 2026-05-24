"use client";

import {
  forwardRef,
  type KeyboardEvent,
  useImperativeHandle,
  useRef,
  useState,
} from "react";
import { ArrowUp, Square } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { MAX_QUERY_LENGTH } from "@/lib/constants";

interface ChatInputProps {
  onSubmit: (query: string) => void;
  onCancel: () => void;
  busy: boolean;
  disabled?: boolean;
  disabledReason?: string;
}

export interface ChatInputHandle {
  setValue: (value: string) => void;
  focus: () => void;
}

export const ChatInput = forwardRef<ChatInputHandle, ChatInputProps>(
  function ChatInput(
    { onSubmit, onCancel, busy, disabled = false, disabledReason },
    ref,
  ) {
    const [value, setValue] = useState("");
    const textareaRef = useRef<HTMLTextAreaElement | null>(null);

    useImperativeHandle(ref, () => ({
      setValue: (next: string) => {
        setValue(next);
        textareaRef.current?.focus();
      },
      focus: () => textareaRef.current?.focus(),
    }));

    const submit = () => {
      const trimmed = value.trim();
      if (!trimmed || busy || disabled) return;
      onSubmit(trimmed);
      setValue("");
    };

    const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
      // Enter submits; Shift+Enter inserts a newline.
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        submit();
      }
    };

    const overLimit = value.length > MAX_QUERY_LENGTH;
    const canSubmit = !busy && !disabled && value.trim().length > 0 && !overLimit;

    return (
      <div className="border-t bg-background/95 supports-[backdrop-filter]:bg-background/60 backdrop-blur sticky bottom-0 p-3">
        <div className="mx-auto max-w-3xl space-y-1.5">
          <div className="flex items-end gap-2">
            <Textarea
              ref={textareaRef}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                disabled
                  ? (disabledReason ?? "Upload your Letterboxd data first.")
                  : "What kind of movie are you in the mood for?"
              }
              rows={1}
              maxLength={MAX_QUERY_LENGTH + 50} // soft over-limit; we still validate
              disabled={disabled}
              className="min-h-[44px] max-h-40 resize-none"
              aria-label="Movie recommendation prompt"
            />
            {busy ? (
              <Button
                type="button"
                variant="secondary"
                size="icon"
                onClick={onCancel}
                aria-label="Cancel request"
              >
                <Square className="h-4 w-4" aria-hidden />
              </Button>
            ) : (
              <Button
                type="button"
                size="icon"
                onClick={submit}
                disabled={!canSubmit}
                aria-label="Send"
              >
                <ArrowUp className="h-4 w-4" aria-hidden />
              </Button>
            )}
          </div>
          <div className="flex justify-between text-xs text-muted-foreground px-0.5">
            <span>Press Enter to send · Shift+Enter for newline</span>
            <span
              className={
                overLimit ? "text-destructive font-medium" : undefined
              }
            >
              {value.length}/{MAX_QUERY_LENGTH}
            </span>
          </div>
        </div>
      </div>
    );
  },
);
