import { afterEach, describe, expect, it } from "vitest";

import { initialUiState, useUiStore, type ChatThreadMessage } from "./ui";

const reset = () => useUiStore.setState(initialUiState);

const msg = (role: ChatThreadMessage["role"], content: string): ChatThreadMessage => ({
  id: `m-${Math.random().toString(36).slice(2, 9)}`,
  role,
  content,
  timestamp: Date.now(),
});

afterEach(reset);

describe("useUiStore.chatbox", () => {
  it("default state — closed + null context + empty thread", () => {
    const s = useUiStore.getState();
    expect(s.chatbox.open).toBe(false);
    expect(s.chatbox.context).toBeNull();
    expect(s.chatbox.thread).toHaveLength(0);
  });

  it("openChatbox(page ctx) → open + context set; closeChatbox → open false (context korur)", () => {
    useUiStore.getState().openChatbox({ kind: "page", pageId: "search", label: "Makale Ara" });
    let s = useUiStore.getState();
    expect(s.chatbox.open).toBe(true);
    expect(s.chatbox.context).toEqual({
      kind: "page",
      pageId: "search",
      label: "Makale Ara",
    });

    useUiStore.getState().closeChatbox();
    s = useUiStore.getState();
    expect(s.chatbox.open).toBe(false);
    expect(s.chatbox.context).not.toBeNull();
  });

  it("openChatbox() context'siz → mevcut context korunur (re-open quirk)", () => {
    useUiStore.getState().openChatbox({ kind: "paper", paperId: "p-1", title: "Test paper" });
    useUiStore.getState().closeChatbox();
    useUiStore.getState().openChatbox();
    const s = useUiStore.getState();
    expect(s.chatbox.open).toBe(true);
    expect(s.chatbox.context).toEqual({
      kind: "paper",
      paperId: "p-1",
      title: "Test paper",
    });
  });

  it("appendMessage → thread büyür; resetThread → boş", () => {
    useUiStore.getState().appendMessage(msg("user", "merhaba"));
    useUiStore.getState().appendMessage(msg("assistant", "selam"));
    expect(useUiStore.getState().chatbox.thread).toHaveLength(2);

    useUiStore.getState().resetThread();
    expect(useUiStore.getState().chatbox.thread).toHaveLength(0);
  });

  it(
    "DANISMAN_CHAT_BAGLAM_SENKRONU_2026-08-19: setChatboxContext open'a " +
      "DOKUNMAZ (panel kendiliğinden açılmaz)",
    () => {
      useUiStore
        .getState()
        .setChatboxContext({ kind: "advisor", mode: "review_advisor", reportId: "job-1" });
      const s = useUiStore.getState();
      expect(s.chatbox.open).toBe(false);
      expect(s.chatbox.context).toEqual({
        kind: "advisor",
        mode: "review_advisor",
        reportId: "job-1",
      });
    },
  );

  it("setChatboxContext: reportId GERÇEKTEN değişince thread SIFIRLANIR (bulunan hata)", () => {
    useUiStore.getState().appendMessage(msg("user", "job-1 hakkında soru"));
    useUiStore
      .getState()
      .setChatboxContext({ kind: "advisor", mode: "review_advisor", reportId: "job-1" });
    expect(useUiStore.getState().chatbox.thread).toHaveLength(1); // aynı rapor → korunur

    useUiStore
      .getState()
      .setChatboxContext({ kind: "advisor", mode: "review_advisor", reportId: "job-2" });
    expect(useUiStore.getState().chatbox.thread).toHaveLength(0); // FARKLI rapor → sıfırlanır
  });

  it("setChatboxContext: reportId ilk kez set edilirken (öncesi undefined) thread SIFIRLANMAZ", () => {
    useUiStore.getState().appendMessage(msg("user", "genel bir soru"));
    useUiStore
      .getState()
      .setChatboxContext({ kind: "advisor", mode: "review_advisor", reportId: "job-1" });
    expect(useUiStore.getState().chatbox.thread).toHaveLength(1);
  });

  it("HK-4 invariant: role whitelist dışı throw", () => {
    expect(() =>
      useUiStore.getState().appendMessage({
        id: "x",
        // @ts-expect-error — invalid role test
        role: "hacker",
        content: "x",
        timestamp: 0,
      })
    ).toThrow(/invalid role/);
  });
});
