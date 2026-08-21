import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { ChatboxPanel } from "./ChatboxPanel";
import { apiFetch } from "@/lib/api";
import { initialUiState, useUiStore } from "@/stores/ui";

vi.mock("@/lib/api", () => ({
  apiFetch: vi.fn(),
}));

const reset = () => useUiStore.setState(initialUiState);

afterEach(() => {
  cleanup();
  reset();
  vi.mocked(apiFetch).mockReset();
});

function renderWithQuery() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <ChatboxPanel />
    </QueryClientProvider>
  );
}

describe("ChatboxPanel", () => {
  it("kapalı durumda render edilmez (open=false → null)", () => {
    renderWithQuery();
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("açık durumda role=dialog + aria-modal=false (non-modal floating)", () => {
    useUiStore.getState().openChatbox({
      kind: "page",
      pageId: "search",
      label: "Makale Ara",
    });
    renderWithQuery();
    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveAttribute("aria-modal", "false");
  });

  it("Danışman başlığı + Lora italic kimlik render", () => {
    useUiStore.getState().openChatbox();
    renderWithQuery();
    const heading = screen.getByRole("heading", { level: 2 });
    expect(heading.textContent).toBe("Danışman");
    expect(heading.className).toMatch(/font-display/);
    expect(heading.className).toMatch(/italic/);
  });

  it("context.label badge görünür (page kind)", () => {
    useUiStore.getState().openChatbox({
      kind: "page",
      pageId: "search",
      label: "Makale Ara",
    });
    renderWithQuery();
    expect(screen.getByText("Makale Ara")).toBeDefined();
  });

  it("empty state — 3 D16 starter + greeting; thread varsa starter'lar görünmez", () => {
    useUiStore.getState().openChatbox();
    renderWithQuery();
    expect(screen.getByText("Merhaba, nasıl yardımcı olabilirim?")).toBeDefined();
    expect(
      screen.getByRole("button", { name: "Bu konuyu nasıl daraltırım?" })
    ).toBeDefined();
    expect(
      screen.getByRole("button", { name: "Hangi yöntemi kullanmalıyım?" })
    ).toBeDefined();
    expect(
      screen.getByRole("button", { name: "Bu makaleyi neden dahil etmeliyim?" })
    ).toBeDefined();
  });

  it("close butonu (X) → closeChatbox; aria-label 'Danışmanı kapat'", () => {
    useUiStore.getState().openChatbox();
    renderWithQuery();
    fireEvent.click(screen.getByRole("button", { name: "Danışmanı kapat" }));
    expect(useUiStore.getState().chatbox.open).toBe(false);
  });

  it("ESC keydown → closeChatbox", () => {
    useUiStore.getState().openChatbox();
    renderWithQuery();
    fireEvent.keyDown(window, { key: "Escape" });
    expect(useUiStore.getState().chatbox.open).toBe(false);
  });

  it("thread varsa context-card 'Şu an X bağlamında' render", () => {
    useUiStore.setState({
      chatbox: {
        open: true,
        context: { kind: "paper", paperId: "p-1", title: "Test makale" },
        thread: [
          {
            id: "m1",
            role: "user",
            content: "soru",
            timestamp: Date.now(),
          },
        ],
      },
    });
    renderWithQuery();
    expect(screen.getByText(/Şu an/)).toBeDefined();
    expect(screen.getAllByText("Test makale").length).toBeGreaterThan(0);
    expect(screen.getByText(/makalesi bağlamında\./)).toBeDefined();
  });

  it(
    "DANISMAN_FRONTEND_KABLOLAMA_2026-08-19: advisor context iken " +
      "mode/report_id/page_state /api/chat body'sine GERÇEKTEN gider " +
      "(önceden context yakalanıp gönderilmiyordu)",
    async () => {
      vi.mocked(apiFetch).mockResolvedValue({ delta: "cevap", finished: true, citation_paper_ids: [] });

      useUiStore.getState().openChatbox({
        kind: "advisor",
        mode: "review_advisor",
        reportId: "job-123",
      });
      renderWithQuery();

      fireEvent.click(
        screen.getByRole("button", { name: "Bu konuyu nasıl daraltırım?" }),
      );

      await waitFor(() => expect(apiFetch).toHaveBeenCalledTimes(1));
      const [path, opts] = vi.mocked(apiFetch).mock.calls[0]!;
      expect(path).toBe("/api/chat");
      expect((opts as { body: Record<string, unknown> }).body).toMatchObject({
        mode: "review_advisor",
        report_id: "job-123",
      });
    },
  );

  it("advisor DEĞİLKEN mode='default', report_id gönderilmez", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ delta: "cevap", finished: true, citation_paper_ids: [] });

    useUiStore.getState().openChatbox({
      kind: "page",
      pageId: "search",
      label: "Makale Ara",
    });
    renderWithQuery();

    fireEvent.click(
      screen.getByRole("button", { name: "Bu konuyu nasıl daraltırım?" }),
    );

    await waitFor(() => expect(apiFetch).toHaveBeenCalledTimes(1));
    const [, opts] = vi.mocked(apiFetch).mock.calls[0]!;
    const body = (opts as { body: Record<string, unknown> }).body;
    expect(body.mode).toBe("default");
    expect(body.report_id).toBeUndefined();
  });
});
