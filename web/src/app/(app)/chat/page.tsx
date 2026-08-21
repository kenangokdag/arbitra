"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { ChatThread } from "@/components/chat/ChatThread";
import { PageHeader } from "@/components/PageHeader";
import { apiFetch } from "@/lib/api";
import type { ChatChunk } from "@/lib/types";
import type { ChatThreadMessage } from "@/stores/ui";

// F4-S4 P079 — /chat full-page refactored to reuse ChatThread (D16 canonical).
// V1-S14 P002 — fixtureReply → POST /api/chat (Gemini Flash + K11 fallback).
// Plan: docs/plans/F4_S4_advisor_chatbox.md §2.8 + docs/plans/V1_S14_mock_to_live.md §6 P002
// Panel <640px'te full-width açılır; /chat URL'si direct erişim için kalır.

let messageCounter = 0;
const newId = () => `chat-${Date.now().toString(36)}-${(++messageCounter).toString(36)}`;

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatThreadMessage[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [sessionId] = useState(() => `chat-${crypto.randomUUID()}`);

  const chatMutation = useMutation({
    mutationFn: async (text: string): Promise<ChatChunk> => {
      const history = messages.map(({ role, content }) => ({ role, content }));
      return apiFetch<ChatChunk>("/api/chat", {
        method: "POST",
        body: {
          session_id: sessionId,
          messages: [...history, { role: "user", content: text }],
          language: "tr",
          paper_context_ids: [],
        },
      });
    },
    onMutate: (text: string) => {
      setMessages((prev) => [
        ...prev,
        { id: newId(), role: "user", content: text, timestamp: Date.now() },
      ]);
      setErrorMessage(null);
    },
    onSuccess: (chunk) => {
      setMessages((prev) => [
        ...prev,
        { id: newId(), role: "assistant", content: chunk.delta, timestamp: Date.now() },
      ]);
    },
    onError: (err) => {
      setErrorMessage(err instanceof Error ? err.message : "Bağlantı hatası");
    },
  });

  return (
    <div className="flex h-[calc(100vh-64px)] flex-col">
      <PageHeader
        title="Makaleyle Sohbet"
        lede="Bağlamdaki makaleler hakkında sorular sorun. Cevaplar kaynak alıntılarıyla gelir."
      />

      <div className="flex-1 min-h-0">
        <ChatThread
          messages={messages}
          onSend={(t) => chatMutation.mutate(t)}
          isPending={chatMutation.isPending}
          errorMessage={errorMessage}
          variant="page"
          emptyState={
            <p className="text-[14px] text-ink-mute">
              Soru sorarak sohbeti başlatın.
            </p>
          }
        />
      </div>
    </div>
  );
}
