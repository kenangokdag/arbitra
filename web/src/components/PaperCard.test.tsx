import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { PaperCard } from "./PaperCard";
import type { PaperCard as PaperCardData } from "@/lib/types";

afterEach(cleanup);

function makePaper(overrides: Partial<PaperCardData> = {}): PaperCardData {
  return {
    paper_id: "W123",
    pmid: "test-pmid",
    title: "Sample paper title",
    authors: ["Alice", "Bob"],
    year: 2024,
    year_verified: true,
    doi: null,
    abstract_excerpt: "Bu calismanin ozeti uzun bir paragraftir.",
    journal: "Test Journal",
    n_cited: 42,
    signals_13: {
      Q_weak: 1.9,
      MQ_Tier1: 1.7,
      CD5: 1.0,
      sentence_role_RES: 1.7,
    },
    citations_lvr: [],
    decision_band: "canon",
    gate_warnings: [],
    is_ghost: false,
    language: "tr",
    is_open_access: true,
    ...overrides,
  };
}

function renderCard(props: Parameters<typeof PaperCard>[0]) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <PaperCard {...props} />
    </QueryClientProvider>
  );
}

describe("PaperCard", () => {
  it("T1: full default render abstract DOM'da", () => {
    renderCard({ paper: makePaper() });
    expect(
      screen.getByText(/Bu calismanin ozeti uzun bir paragraftir/)
    ).toBeInTheDocument();
  });

  it("T2: compact=true → abstract YOK · aksiyon 3 (Detay/Listeme/Sohbet)", () => {
    renderCard({ paper: makePaper(), compact: true });
    expect(
      screen.queryByText(/Bu calismanin ozeti uzun bir paragraftir/)
    ).toBeNull();
    expect(screen.getByText("Detay")).toBeInTheDocument();
    expect(screen.getByText("Listeme")).toBeInTheDocument();
    expect(screen.getByText("Sohbet")).toBeInTheDocument();
    expect(screen.queryByText(/Ozetle/)).toBeNull();
    expect(screen.queryByText(/Nota ekle/)).toBeNull();
    expect(screen.queryByText(/Danismana sor/)).toBeNull();
  });

  it("T3: EstraChips strip 4 chip (Q/M/Δ5/R) render", () => {
    const { container } = renderCard({ paper: makePaper() });
    const strip = container.querySelector('[data-testid="estra-chips"]');
    expect(strip).not.toBeNull();
    expect(strip?.children.length).toBe(4);
    expect(strip?.textContent).toContain("Q 1.9");
    expect(strip?.textContent).toContain("M 1.7");
    expect(strip?.textContent).toContain("Δ5 1.0");
    expect(strip?.textContent).toContain("R 1.7");
  });

  it("T4: Threshold rengi — Q_weak 1.92 emerald, Q_weak 0.5 stone", () => {
    const { container: highC } = renderCard({
      paper: makePaper({ signals_13: { Q_weak: 1.92, MQ_Tier1: 0, CD5: 0, sentence_role_RES: 0 } }),
    });
    const highStrip = highC.querySelector('[data-testid="estra-chips"]');
    expect(highStrip?.children[0]?.className).toContain("emerald");

    cleanup();

    const { container: lowC } = renderCard({
      paper: makePaper({ signals_13: { Q_weak: 0.5, MQ_Tier1: 0, CD5: 0, sentence_role_RES: 0 } }),
    });
    const lowStrip = lowC.querySelector('[data-testid="estra-chips"]');
    expect(lowStrip?.children[0]?.className).toContain("stone");
  });

  it("T5: signals_13 boş obje → strip render etmez", () => {
    const { container } = renderCard({
      paper: makePaper({ signals_13: {} }),
    });
    expect(
      container.querySelector('[data-testid="estra-chips"]')
    ).toBeNull();
  });

  it("T6: isGhost + compact → 'Klasik kaynak' rozeti hala DOM'da", () => {
    renderCard({ paper: makePaper(), isGhost: true, compact: true });
    expect(screen.getByText("Klasik kaynak")).toBeInTheDocument();
  });
});
