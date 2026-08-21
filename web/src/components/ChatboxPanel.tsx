"use client";

import { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useMutation } from "@tanstack/react-query";
import { X } from "lucide-react";

import { ChatThread } from "@/components/chat/ChatThread";
import { PenIcon } from "@/components/icons/pen";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/cn";
import type { ChatChunk } from "@/lib/types";
import {
  useAppendMessage,
  useChatboxContext,
  useChatboxOpen,
  useChatboxThread,
  useCloseChatbox,
} from "@/stores/ui";

import type { ChatThreadMessage } from "@/stores/ui";

// F4-S4 P077 — ChatboxPanel floating shell (D16 canonical)
// Plan: docs/plans/F4_S4_advisor_chatbox.md §2.5
// Mockup: D16-Chatbox.html L137-565 (3 state: empty + conversation + dark)
// 370x620 fixed bottom-right + slideIn 280ms + ESC close + portal mount + mobile full-width.

const STARTERS = [
  "Bu konuyu nasıl daraltırım?",
  "Hangi yöntemi kullanmalıyım?",
  "Bu makaleyi neden dahil etmeliyim?",
] as const;

const SUGGESTIONS = [
  "Daha derin açıkla",
  "Karşı argüman ne?",
  "Örnek ver",
] as const;

let messageCounter = 0;
const newId = () => `msg-${Date.now().toString(36)}-${(++messageCounter).toString(36)}`;

export type ChatboxPanelProps = {
  dark?: boolean;
};

export function ChatboxPanel({ dark = false }: ChatboxPanelProps) {
  const titleId = useId();
  const open = useChatboxOpen();
  const context = useChatboxContext();
  const thread = useChatboxThread();
  const closeChatbox = useCloseChatbox();
  const appendMessage = useAppendMessage();
  const [mounted, setMounted] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [sessionId] = useState(() => `chatbox-${crypto.randomUUID()}`);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => setMounted(true), []);

  // ESC kapanma — aktif element textarea olsa bile global listener
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        closeChatbox();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, closeChatbox]);

  // textarea autoFocus — slide-in (280ms) tamamlandıktan sonra
  // Konsey 2026-05-01: panelRef-scoped query (önceki global document.querySelector
  // birden fazla [data-chatbox-panel] portal'ı durumunda yanlış focus verirdi).
  useEffect(() => {
    if (!open) return;
    const t = setTimeout(() => {
      panelRef.current?.querySelector<HTMLTextAreaElement>("textarea")?.focus();
    }, 280);
    return () => clearTimeout(t);
  }, [open]);

  const sendMutation = useMutation({
    mutationFn: async (text: string): Promise<ChatChunk> => {
      // V1-S14 P002 — POST /api/chat (Gemini Flash + K11 fallback). SSE streaming
      // F2 sonrası eklenir (KD-18 Cosmos handoff).
      // DANISMAN_FRONTEND_KABLOLAMA_2026-08-19: context artık GERÇEKTEN
      // gönderiliyor — önceden context yakalanıp SADECE başlıkta gösteriliyordu,
      // /api/chat'e hiç gitmiyordu (backend mode/report_id'yi hiç görmüyordu).
      const history = thread.map(({ role, content }) => ({ role, content }));
      const isAdvisor = context?.kind === "advisor";
      return apiFetch<ChatChunk>("/api/chat", {
        method: "POST",
        body: {
          session_id: sessionId,
          messages: [...history, { role: "user", content: text }],
          language: "tr",
          paper_context_ids: [],
          mode: isAdvisor ? context.mode : "default",
          report_id: isAdvisor ? context.reportId : undefined,
          page_state: isAdvisor ? context.pageState : undefined,
        },
      });
    },
    onMutate: (text: string) => {
      const userMsg: ChatThreadMessage = {
        id: newId(),
        role: "user",
        content: text,
        timestamp: Date.now(),
      };
      appendMessage(userMsg);
      setErrorMessage(null);
    },
    onSuccess: (chunk) => {
      const aiMsg: ChatThreadMessage = {
        id: newId(),
        role: "assistant",
        content: chunk.delta,
        timestamp: Date.now(),
      };
      appendMessage(aiMsg);
    },
    onError: (err) => {
      setErrorMessage(err instanceof Error ? err.message : "Bağlantı hatası");
    },
  });

  if (!mounted || !open) return null;

  const contextLabel =
    context?.kind === "page"
      ? context.label
      : context?.kind === "paper"
        ? context.title
        : null;

  const hasThread = thread.length > 0;

  const panel = (
    <div
      ref={panelRef}
      data-chatbox-panel="true"
      role="dialog"
      aria-modal="false"
      aria-labelledby={titleId}
      className={cn(
        "fixed z-50 flex flex-col overflow-hidden bg-white shadow-[0_24px_48px_-12px_rgba(15,23,42,0.20),0_8px_16px_-6px_rgba(15,23,42,0.12),0_0_0_1px_rgba(15,23,42,0.04)]",
        // mobile <640px → bottom drawer full-width
        "inset-x-0 bottom-0 top-16 sm:inset-auto sm:bottom-6 sm:right-6 sm:top-auto sm:h-[620px] sm:w-[370px]",
        "sm:rounded-[16px]",
        dark && "chatbox-dark"
      )}
      style={{
        backgroundColor: "var(--chat-bg)",
        borderColor: "var(--chat-border)",
        animation: "chatbox-slide-in 280ms cubic-bezier(.16,1,.3,1) both",
      }}
    >
      {/* Header — D16 L141-160 ink bg + Pen avatar + Lora name + status dot + ctx badge + close */}
      <header
        className="flex shrink-0 items-center gap-2.5 px-3.5 py-2.5"
        style={{ backgroundColor: "var(--chat-header)" }}
      >
        <span
          aria-hidden="true"
          className="flex h-7 w-7 items-center justify-center rounded-full text-white"
          style={{
            backgroundColor: "rgba(255,255,255,0.06)",
            boxShadow: "inset 0 0 0 1px rgba(255,255,255,0.18)",
          }}
        >
          <PenIcon className="h-3.5 w-3.5" />
        </span>
        <div className="flex flex-1 items-center gap-1.5 text-white">
          <h2
            id={titleId}
            className="font-display text-[14.5px] italic leading-none"
          >
            Danışman
          </h2>
          <span
            aria-hidden="true"
            className="h-1.5 w-1.5 rounded-full"
            style={{ backgroundColor: "var(--chat-status)" }}
          />
        </div>
        {contextLabel ? (
          <span
            className="max-w-[140px] truncate rounded-full px-2 py-0.5 text-[9.5px] uppercase tracking-wide text-white/80"
            style={{
              fontFamily: "var(--font-mono)",
              backgroundColor: "rgba(255,255,255,0.08)",
            }}
            title={contextLabel}
          >
            {contextLabel}
          </span>
        ) : null}
        <button
          type="button"
          onClick={closeChatbox}
          aria-label="Danışmanı kapat"
          className="flex h-7 w-7 items-center justify-center rounded-full text-white/70 transition-colors duration-150 hover:bg-white/10 hover:text-white"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </header>

      {/* Context card — D16 L137-150 conversation state'te header altında */}
      {hasThread && context ? (
        <div
          className="shrink-0 border-b px-3.5 py-2 text-[11.5px] text-ink-mute"
          style={{
            borderColor: "var(--chat-border)",
            backgroundColor: "var(--chat-surface)",
          }}
        >
          Şu an{" "}
          <span className="font-display italic text-ink">{contextLabel}</span>{" "}
          {context.kind === "paper" ? "makalesi" : "sayfası"} bağlamında.
        </div>
      ) : null}

      {/* Body — ChatThread her state'te (empty greeting'i emptyState prop'unda) */}
      <div className="flex min-h-0 flex-1 flex-col">
        <ChatThread
          messages={thread}
          onSend={(t) => sendMutation.mutate(t)}
          isPending={sendMutation.isPending}
          errorMessage={errorMessage}
          suggestions={hasThread ? SUGGESTIONS : undefined}
          emptyState={
            <div className="flex flex-col items-center gap-4 px-2 text-center">
              <span
                aria-hidden="true"
                className="flex h-12 w-12 items-center justify-center rounded-full"
                style={{
                  backgroundColor: "var(--chat-surface)",
                  boxShadow: "inset 0 0 0 1px var(--chat-border)",
                }}
              >
                <PenIcon className="h-5 w-5 text-ink" />
              </span>
              <div className="flex flex-col gap-1">
                <p className="font-display text-[15px] italic text-ink">
                  Merhaba, nasıl yardımcı olabilirim?
                </p>
                <p className="text-[12px] text-ink-mute">
                  Aşağıdaki sorulardan biriyle başla, ya da kendi sorunu yaz.
                </p>
              </div>
              <div className="flex w-full flex-col gap-2">
                {STARTERS.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => sendMutation.mutate(s)}
                    disabled={sendMutation.isPending}
                    className="font-display rounded-[10px] border px-3 py-2 text-left text-[13px] italic text-ink transition-colors duration-150 hover:bg-bg-soft disabled:opacity-50"
                    style={{
                      backgroundColor: "var(--chat-surface)",
                      borderColor: "var(--chat-border)",
                    }}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          }
          variant="panel"
        />
      </div>
    </div>
  );

  return createPortal(panel, document.body);
}
