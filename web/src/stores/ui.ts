"use client";

import { create } from "zustand";

import type { ChatMessage } from "@/lib/types";

// F4-S4 P075 — useUiStore (Danışman ChatboxPanel global state)
// Plan: docs/plans/F4_S4_advisor_chatbox.md §2.2
// Persistence YOK (MVP) — refresh thread sıfırlar (KD-30 Faz 2 persisted conversation)

export type ChatThreadMessage = ChatMessage & {
  id: string;
  timestamp: number;
};

export type ChatboxContext =
  | { kind: "page"; pageId: string; label: string }
  | { kind: "paper"; paperId: string; title: string }
  | {
      kind: "advisor";
      mode: string;
      pageState?: Record<string, unknown>;
      // DANISMAN_FRONTEND_KABLOLAMA_2026-08-19: incelenen makalenin hakem
      // raporunun job_id'si. Backend bunu (report_id) sahip-kapsamlı çekip
      // (review_service.get_report) prompt'a enjekte eder — pageState'ten
      // AYRI, tipli bir kanal (istemciden gelen sahtelenebilir veri değil).
      reportId?: string;
    }
  | null;

type UiState = {
  chatbox: {
    open: boolean;
    context: ChatboxContext;
    thread: ChatThreadMessage[];
  };
};

type UiActions = {
  openChatbox: (ctx?: ChatboxContext) => void;
  closeChatbox: () => void;
  appendMessage: (msg: ChatThreadMessage) => void;
  resetThread: () => void;
  /** DANISMAN_CHAT_BAGLAM_SENKRONU_2026-08-19: panel AÇIK olsun ya da olmasın
   * context'i günceller (openChatbox'ın aksine `open`'a dokunmaz). Rapor
   * sayfası mount olunca çağırır — kullanıcı butona TEKRAR tıklamasa bile
   * panel doğru rapora işaret eder. reportId GERÇEKTEN değiştiyse (ikisi de
   * tanımlıysa ve farklıysa) thread SIFIRLANIR — farklı bir makale hakkındaki
   * eski Q&A ekranda kalıp kafa karıştırmasın. */
  setChatboxContext: (ctx: ChatboxContext) => void;
};

export const initialUiState: UiState = {
  chatbox: {
    open: false,
    context: null,
    thread: [],
  },
};

export const useUiStore = create<UiState & UiActions>((set) => ({
  ...initialUiState,
  openChatbox: (ctx) =>
    set((state) => ({
      chatbox: {
        ...state.chatbox,
        open: true,
        context: ctx ?? state.chatbox.context,
      },
    })),
  closeChatbox: () =>
    set((state) => ({ chatbox: { ...state.chatbox, open: false } })),
  appendMessage: (msg) => {
    // HK-4 runtime invariant: rol whitelist
    if (msg.role !== "user" && msg.role !== "assistant" && msg.role !== "system") {
      throw new Error(`useUiStore.appendMessage: invalid role "${msg.role}"`);
    }
    set((state) => ({
      chatbox: { ...state.chatbox, thread: [...state.chatbox.thread, msg] },
    }));
  },
  resetThread: () =>
    set((state) => ({ chatbox: { ...state.chatbox, thread: [] } })),
  setChatboxContext: (ctx) =>
    set((state) => {
      const prev = state.chatbox.context;
      const prevReportId = prev?.kind === "advisor" ? prev.reportId : undefined;
      const nextReportId = ctx?.kind === "advisor" ? ctx.reportId : undefined;
      const reportChanged =
        prevReportId !== undefined &&
        nextReportId !== undefined &&
        prevReportId !== nextReportId;
      return {
        chatbox: {
          ...state.chatbox,
          context: ctx,
          thread: reportChanged ? [] : state.chatbox.thread,
        },
      };
    }),
}));

// Selector hooks — atomic refs (yeni nesne döndüren composite selector infinite loop sebep,
// her action ayrı stable ref olarak seçilir).
export const useChatboxOpen = () => useUiStore((s) => s.chatbox.open);
export const useChatboxContext = () => useUiStore((s) => s.chatbox.context);
export const useChatboxThread = () => useUiStore((s) => s.chatbox.thread);
export const useOpenChatbox = () => useUiStore((s) => s.openChatbox);
export const useCloseChatbox = () => useUiStore((s) => s.closeChatbox);
export const useAppendMessage = () => useUiStore((s) => s.appendMessage);
export const useResetThread = () => useUiStore((s) => s.resetThread);
export const useSetChatboxContext = () => useUiStore((s) => s.setChatboxContext);
