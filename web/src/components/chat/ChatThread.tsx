"use client";

import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { Send } from "lucide-react";

import { PenIcon } from "@/components/icons/pen";
import { cn } from "@/lib/cn";

import type { ChatThreadMessage } from "@/stores/ui";

// F4-S4 P076 — ChatThread shared sub-component
// Plan: docs/plans/F4_S4_advisor_chatbox.md §2.4
// Mockup: D16-Chatbox.html L152-252 (msgs + typing + suggestions + input)
// Hem ChatboxPanel hem /chat full-page'de reuse edilir (DRY).

export type ChatThreadProps = {
  messages: ChatThreadMessage[];
  onSend: (text: string) => void;
  isPending?: boolean;
  errorMessage?: string | null;
  suggestions?: readonly string[];
  contextCard?: React.ReactNode;
  emptyState?: React.ReactNode;
  userInitial?: string;
  variant?: "panel" | "page";
};

const TR_DAY = ["Pzr", "Pzt", "Sal", "Çar", "Per", "Cum", "Cmt"];

function formatSeparator(ts: number, today = new Date()): string {
  const d = new Date(ts);
  const sameDay = d.toDateString() === today.toDateString();
  if (sameDay) return "Bugün";
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);
  if (d.toDateString() === yesterday.toDateString()) return "Dün";
  return `${TR_DAY[d.getDay()]} ${d.getDate().toString().padStart(2, "0")}.${(d.getMonth() + 1)
    .toString()
    .padStart(2, "0")}`;
}

function shouldShowSeparator(prev: ChatThreadMessage | undefined, curr: ChatThreadMessage): boolean {
  if (!prev) return true;
  const prevDay = new Date(prev.timestamp).toDateString();
  const currDay = new Date(curr.timestamp).toDateString();
  return prevDay !== currDay;
}

export function ChatThread({
  messages,
  onSend,
  isPending = false,
  errorMessage = null,
  suggestions,
  contextCard,
  emptyState,
  userInitial = "S",
  variant = "panel",
}: ChatThreadProps) {
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (el && typeof el.scrollTo === "function") {
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    }
  }, [messages.length, isPending]);

  // Auto-resize textarea (D16 L246: 38px min → 96px max)
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(96, Math.max(38, ta.scrollHeight))}px`;
  }, [input]);

  function handleSend(text: string) {
    const trimmed = text.trim();
    if (!trimmed || isPending) return;
    onSend(trimmed);
    setInput("");
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    handleSend(input);
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend(input);
    }
  }

  const isEmpty = messages.length === 0 && !isPending;
  const showSuggestions = suggestions && suggestions.length > 0;

  return (
    <div
      className={cn(
        "flex h-full min-h-0 flex-col",
        variant === "page" && "mx-auto w-full max-w-2xl"
      )}
    >
      {contextCard ? <div className="shrink-0">{contextCard}</div> : null}

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-3.5 py-3"
        role="log"
        aria-live="polite"
        aria-label="Sohbet mesajları"
      >
        {isEmpty && emptyState ? (
          <div className="flex h-full items-center justify-center">{emptyState}</div>
        ) : null}

        <ul className="flex flex-col gap-2.5">
          {messages.map((msg, i) => {
            const prev = messages[i - 1];
            const showDate = shouldShowSeparator(prev, msg);
            const isUser = msg.role === "user";
            return (
              <li key={msg.id} className="flex flex-col">
                {showDate ? (
                  <div className="my-2 self-center font-mono text-[10px] uppercase tracking-wider text-ink-faint">
                    {formatSeparator(msg.timestamp)}
                  </div>
                ) : null}
                <div
                  className={cn(
                    "flex items-end gap-2",
                    isUser ? "self-end flex-row-reverse" : "self-start"
                  )}
                >
                  <span
                    aria-hidden="true"
                    className={cn(
                      "flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold",
                      isUser
                        ? "bg-bg-card font-display italic text-ink"
                        : "border text-ink-mute"
                    )}
                    style={
                      isUser
                        ? undefined
                        : {
                            backgroundColor: "var(--chat-surface)",
                            borderColor: "var(--chat-border)",
                          }
                    }
                  >
                    {isUser ? userInitial : <PenIcon className="h-3 w-3" />}
                  </span>
                  <div
                    className={cn(
                      "max-w-[78%] px-3 py-2 text-[13.5px] leading-relaxed",
                      isUser
                        ? "rounded-[11px] rounded-br-[3px] text-white"
                        : "rounded-[11px] rounded-bl-[3px] font-display italic text-ink"
                    )}
                    style={{
                      backgroundColor: isUser
                        ? "var(--chat-user-bg)"
                        : "var(--chat-adviser)",
                    }}
                  >
                    {msg.content}
                  </div>
                </div>
              </li>
            );
          })}

          {isPending ? (
            <li className="flex items-end gap-2 self-start">
              <span
                aria-hidden="true"
                className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-ink-mute"
                style={{
                  backgroundColor: "var(--chat-surface)",
                  borderColor: "var(--chat-border)",
                }}
              >
                <PenIcon className="h-3 w-3" />
              </span>
              <div
                role="status"
                aria-label="Danışman yazıyor"
                className="rounded-[11px] rounded-bl-[3px] px-3 py-2.5"
                style={{ backgroundColor: "var(--chat-adviser)" }}
              >
                <span className="flex gap-1">
                  <span
                    className="h-1.5 w-1.5 rounded-full bg-ink-mute"
                    style={{ animation: "chatbox-typing-dot 1.2s infinite", animationDelay: "0s" }}
                  />
                  <span
                    className="h-1.5 w-1.5 rounded-full bg-ink-mute"
                    style={{ animation: "chatbox-typing-dot 1.2s infinite", animationDelay: "0.18s" }}
                  />
                  <span
                    className="h-1.5 w-1.5 rounded-full bg-ink-mute"
                    style={{ animation: "chatbox-typing-dot 1.2s infinite", animationDelay: "0.36s" }}
                  />
                </span>
              </div>
            </li>
          ) : null}

          {errorMessage ? (
            <li
              role="alert"
              className="self-stretch rounded-[10px] border border-red-200 bg-red-50 px-3 py-2 text-[12.5px] text-red-700"
            >
              {errorMessage}
            </li>
          ) : null}
        </ul>
      </div>

      {showSuggestions ? (
        <div
          className="flex shrink-0 flex-wrap gap-1.5 border-t px-3.5 py-2"
          style={{ borderColor: "var(--chat-border)" }}
        >
          {suggestions.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => handleSend(s)}
              disabled={isPending}
              className="font-display rounded-full border px-3 py-1 text-[12px] italic text-ink transition-colors duration-150 hover:bg-bg-soft disabled:opacity-50"
              style={{
                backgroundColor: "var(--chat-surface)",
                borderColor: "var(--chat-border)",
              }}
            >
              {s}
            </button>
          ))}
        </div>
      ) : null}

      <form
        onSubmit={handleSubmit}
        className="shrink-0 border-t px-3 py-2.5"
        style={{ borderColor: "var(--chat-border)", backgroundColor: "var(--chat-bg)" }}
      >
        <div className="flex items-end gap-2">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            placeholder="Danışmana sor…"
            aria-label="Danışmana mesaj yaz"
            disabled={isPending}
            className="min-h-[38px] flex-1 resize-none rounded-[10px] border px-3 py-2 text-[13.5px] text-ink outline-none placeholder:text-ink-faint focus:border-ink/40 disabled:opacity-50"
            style={{
              backgroundColor: "var(--chat-surface)",
              borderColor: "var(--chat-border)",
            }}
          />
          <button
            type="submit"
            disabled={isPending || !input.trim()}
            aria-label="Gönder"
            className="flex h-[38px] w-[38px] shrink-0 items-center justify-center rounded-[10px] text-white transition-opacity duration-150 hover:opacity-85 disabled:opacity-40"
            style={{ backgroundColor: "var(--chat-user-bg)" }}
          >
            <Send className="h-3.5 w-3.5" />
          </button>
        </div>
      </form>
    </div>
  );
}
