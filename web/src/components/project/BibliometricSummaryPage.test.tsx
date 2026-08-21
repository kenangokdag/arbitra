// V1-S14 P006: live-wire render testleri (skeleton + header + warehouse-aligned
// metric set). Eski fixture testleri (Lotka, Top-10 yazar/dergi, N=240) düştü.

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { BibliometricSummaryPage } from "./BibliometricSummaryPage";

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "p1" }),
}));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function renderWithQuery() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <BibliometricSummaryPage />
    </QueryClientProvider>
  );
}

const SUMMARY = {
  total_papers: 12,
  median_year: 2022,
  mean_citations: 17.5,
  most_cited: { paper_id: "W1", pmid: "PM1", citations: 99 },
  publications_by_year: [{ year: 2022, count: 12 }],
  language_dist: [{ code: "en", count: 12 }],
  top_areas: [{ name: "Computer Science", count: 8 }],
  top_methods: [{ name: "Yöntem", count: 6 }],
};

describe("BibliometricSummaryPage", () => {
  it("ilk render'da skeleton gösterir (isLoading)", () => {
    vi.spyOn(global, "fetch").mockImplementation(
      () => new Promise(() => {})
    );
    const { container } = renderWithQuery();
    expect(container.querySelector("[aria-busy]")).toBeTruthy();
  });

  it("canlı veri gelince header + 4 metrik kart + warehouse alanlar render", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(SUMMARY), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );
    renderWithQuery();
    await waitFor(() => {
      expect(screen.getByText("Bibliyometrik panorama")).toBeTruthy();
    });
    expect(screen.getByText(/Havuz · N=12/)).toBeTruthy();
    expect(screen.getByText("Toplam makale")).toBeTruthy();
    expect(screen.getByText("Medyan yil")).toBeTruthy();
    expect(screen.getByText("Ortalama atif")).toBeTruthy();
    expect(screen.getByText("En cok atiflanan")).toBeTruthy();
    expect(screen.getByText(/Yil dagilimi/)).toBeTruthy();
    expect(screen.getByText(/Dil dagilimi/)).toBeTruthy();
    expect(screen.getByText(/Yontem dagilimi/)).toBeTruthy();
    expect(screen.getByText(/Top alan/)).toBeTruthy();
  });

  it("hata durumunda kullanici mesaji gosterilir", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response("boom", { status: 502 })
    );
    renderWithQuery();
    await waitFor(() => {
      expect(screen.getByText(/Bibliyometrik veri yuklenemedi/)).toBeTruthy();
    });
  });
});
