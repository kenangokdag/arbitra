// DANISMAN_CHAT_TOPBAR_KONTEKST_KORUMA_2026-08-19: kalem ikonu (Danışman aç)
// rapor sayfasındayken mevcut context'i (kind:"advisor") KOŞULSUZ olarak
// {kind:"page"} ile eziyordu — gerçek hata, kullanıcı raporu inceledikten
// sonra bu ikona tıklayınca Danışman rapor bağlamını kaybediyordu. Bu dosya
// Topbar.tsx'in rota-farkında koruma mantığını doğrular.

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

let mockPathname = "/search";
vi.mock("next/navigation", () => ({
  usePathname: () => mockPathname,
}));

vi.mock("@/lib/navigation-context", () => ({
  useNavigation: () => ({
    breadcrumb: ["Makale Ara"],
    setMobileOpen: vi.fn(),
  }),
}));

import { Topbar } from "./Topbar";
import { initialUiState, useUiStore } from "@/stores/ui";

const reset = () => {
  useUiStore.setState(initialUiState);
  mockPathname = "/search";
};

afterEach(() => {
  cleanup();
  reset();
});

const clickPen = () => fireEvent.click(screen.getByLabelText("Danışmana sor (Cmd+J)"));

describe("Topbar — Danışman toggle context koruma", () => {
  it("rapor DIŞI rotada, context yokken → generic page context set edilir (eski davranış)", () => {
    mockPathname = "/search";
    render(<Topbar />);
    clickPen();
    const s = useUiStore.getState();
    expect(s.chatbox.open).toBe(true);
    expect(s.chatbox.context).toEqual({ kind: "page", pageId: "Makale Ara", label: "Makale Ara" });
  });

  it("rapor rotasında, mevcut advisor context VARKEN → korunur, ezilmez (bulunan hata)", () => {
    mockPathname = "/review/job-1";
    useUiStore.setState({
      chatbox: {
        ...initialUiState.chatbox,
        context: { kind: "advisor", mode: "review_advisor", reportId: "job-1" },
      },
    });
    render(<Topbar />);
    clickPen();
    const s = useUiStore.getState();
    expect(s.chatbox.open).toBe(true);
    expect(s.chatbox.context).toEqual({
      kind: "advisor",
      mode: "review_advisor",
      reportId: "job-1",
    });
  });

  it("rapor rotasında ama context henüz set edilmemişse (null) → generic page context'e düşer", () => {
    mockPathname = "/review/job-1";
    render(<Topbar />);
    clickPen();
    const s = useUiStore.getState();
    expect(s.chatbox.open).toBe(true);
    expect(s.chatbox.context).toEqual({ kind: "page", pageId: "Makale Ara", label: "Makale Ara" });
  });

  it("açıkken tıklama → kapatır (context'e dokunmaz)", () => {
    mockPathname = "/search";
    useUiStore.setState({
      chatbox: {
        ...initialUiState.chatbox,
        open: true,
        context: { kind: "page", pageId: "X", label: "X" },
      },
    });
    render(<Topbar />);
    clickPen();
    const s = useUiStore.getState();
    expect(s.chatbox.open).toBe(false);
    expect(s.chatbox.context).toEqual({ kind: "page", pageId: "X", label: "X" });
  });
});
