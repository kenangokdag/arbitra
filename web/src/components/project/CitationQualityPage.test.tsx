import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { CitationQualityPage } from "./CitationQualityPage";

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "11111111-1111-1111-1111-111111111111" }),
}));

const apiFetchMock = vi.fn();

vi.mock("@/lib/api", () => ({
  apiFetch: (path: string, opts?: unknown) => apiFetchMock(path, opts),
  ApiError: class ApiError extends Error {
    status = 0;
    detail: unknown = null;
  },
}));

const PROJECT_ID = "11111111-1111-1111-1111-111111111111";

const searchStub = {
  papers: [
    {
      paper_id: "s2_1234",
      title: "Fuzzy TOPSIS for supplier selection",
      authors: ["Chen", "Hwang"],
      year: 2020,
      venue: "Expert Systems w/ Apps",
      doi: "10.1/abc",
      citations_count: 120,
    },
    {
      paper_id: "s2_5678",
      title: "VIKOR sustainability review",
      authors: ["Opricovic"],
      year: 2018,
      venue: "Omega",
      doi: null,
      citations_count: 45,
    },
  ],
  synonyms_tried: ["fuzzy", "bulanık"],
  total_results: 2,
};

const verifyStub = {
  sentences: [
    {
      index: 0,
      text: "TOPSIS Chen 2000 tarafından geliştirilmiştir.",
      citations: [
        {
          raw: "(Chen 2000)",
          author_guess: "Chen",
          year_guess: 2000,
          matched_paper_id: "s2_1234",
        },
      ],
      status: "ok" as const,
    },
    {
      index: 1,
      text: "Bulanık MCDM yöntemleri yaygın değildir.",
      citations: [],
      status: "needs_citation" as const,
    },
    {
      index: 2,
      text: "Smith 2030 yılında AHP'yi keşfetmiştir.",
      citations: [
        {
          raw: "(Smith 2030)",
          author_guess: "Smith",
          year_guess: 2030,
          matched_paper_id: null,
        },
      ],
      status: "hallucinated" as const,
    },
  ],
  total_citations: 2,
  hallucinated_count: 1,
  topic_mismatch_count: 0,
  needs_citation_count: 1,
};

const formatStub = {
  paper_id: "s2_1234",
  style: "apa" as const,
  formatted_citation:
    "Chen, T., & Hwang, C. (2020). Fuzzy TOPSIS for supplier selection. Expert Systems w/ Apps.",
  bibtex_entry:
    "@article{chen2020fuzzy,\n  title={Fuzzy TOPSIS for supplier selection},\n  year={2020}\n}",
};

const balanceStub = {
  total: 10,
  old_count: 2,
  recent_count: 6,
  old_pct: 20.0,
  recent_pct: 60.0,
  suggested_papers: [
    {
      paper_id: "s2_9999",
      title: "Recent MCDM survey 2024",
      authors: ["Lee"],
      year: 2024,
      venue: "Omega",
      doi: null,
      citations_count: 12,
    },
  ],
  balance_advice: "Daha güncel kaynak ekle — eski oranı %20 ile makul ama yeni %60 sınırda.",
};

beforeEach(() => {
  apiFetchMock.mockReset();
});

afterEach(() => cleanup());

describe("CitationQualityPage", () => {
  it("4 panel ilk render + butonlar bos input ile disabled", () => {
    render(<CitationQualityPage />);
    expect(screen.getByText(/Havuzdan ara/)).toBeTruthy();
    expect(screen.getByText(/Metni doğrula/)).toBeTruthy();
    expect(screen.getByText(/Tek atıfı formatla/)).toBeTruthy();
    expect(screen.getByText(/Eski-yeni denge/)).toBeTruthy();

    const araBtn = screen.getByRole("button", { name: /^Ara$/i }) as HTMLButtonElement;
    const dogrulaBtn = screen.getByRole("button", { name: /^Doğrula$/i }) as HTMLButtonElement;
    const formatBtn = screen.getByRole("button", { name: /^Formatla$/i }) as HTMLButtonElement;
    const dengeBtn = screen.getByRole("button", { name: /^Dengele$/i }) as HTMLButtonElement;
    expect(araBtn.disabled).toBe(true);
    expect(dogrulaBtn.disabled).toBe(true);
    expect(formatBtn.disabled).toBe(true);
    expect(dengeBtn.disabled).toBe(true);

    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("Search → GET /citation-search + paper kartlari + synonyms render", async () => {
    render(<CitationQualityPage />);
    fireEvent.change(screen.getByPlaceholderText(/Anahtar kelime/i), {
      target: { value: "fuzzy topsis" },
    });

    apiFetchMock.mockResolvedValueOnce(searchStub);
    fireEvent.click(screen.getByRole("button", { name: /^Ara$/i }));

    await waitFor(() => {
      expect(screen.getByText(/Fuzzy TOPSIS for supplier selection/)).toBeTruthy();
      expect(screen.getByText(/VIKOR sustainability review/)).toBeTruthy();
      expect(screen.getByText(/es anlamlilar: fuzzy, bulanık/)).toBeTruthy();
    });

    const paths = apiFetchMock.mock.calls.map((c) => c[0] as string);
    expect(paths.some((p) => p.startsWith("/api/workshop/citation-search"))).toBe(true);
    expect(paths.some((p) => p.includes("query=fuzzy%20topsis"))).toBe(true);
    expect(paths.some((p) => p.includes("lang=tr"))).toBe(true);
  });

  it("Verify → POST /citation-verify + cumle statu rozetleri + sayilar", async () => {
    render(<CitationQualityPage />);
    fireEvent.change(screen.getByPlaceholderText(/Metni buraya yapıştır/i), {
      target: { value: "Bir cümle. İkinci cümle. Üçüncü." },
    });

    apiFetchMock.mockResolvedValueOnce(verifyStub);
    fireEvent.click(screen.getByRole("button", { name: /^Doğrula$/i }));

    await waitFor(() => {
      expect(screen.getByText(/TOPSIS Chen 2000/)).toBeTruthy();
      expect(screen.getByText(/Smith 2030 yılında/)).toBeTruthy();
      // status badges
      expect(screen.getAllByText(/Hayalet/).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/Atıf gerek/).length).toBeGreaterThan(0);
    });

    expect(apiFetchMock).toHaveBeenCalledWith(
      "/api/workshop/citation-verify",
      expect.objectContaining({
        method: "POST",
        body: expect.objectContaining({
          project_id: PROJECT_ID,
          document_text: "Bir cümle. İkinci cümle. Üçüncü.",
          citation_style: "apa",
        }),
      }),
    );
  });

  it("Format → GET /format-citation + APA satiri + bibtex render", async () => {
    render(<CitationQualityPage />);
    fireEvent.change(screen.getByPlaceholderText(/paper_id \(örn/i), {
      target: { value: "s2_1234" },
    });

    apiFetchMock.mockResolvedValueOnce(formatStub);
    fireEvent.click(screen.getByRole("button", { name: /^Formatla$/i }));

    await waitFor(() => {
      expect(screen.getByText(/Chen, T\., & Hwang/)).toBeTruthy();
      expect(screen.getByText(/@article\{chen2020fuzzy/)).toBeTruthy();
    });

    const paths = apiFetchMock.mock.calls.map((c) => c[0] as string);
    expect(paths.some((p) => p.startsWith("/api/workshop/format-citation"))).toBe(true);
    expect(paths.some((p) => p.includes("paper_id=s2_1234"))).toBe(true);
    expect(paths.some((p) => p.includes("style=apa"))).toBe(true);
  });

  it("Balance → POST /citation-balance + advice + onerilen makale render", async () => {
    render(<CitationQualityPage />);
    fireEvent.change(screen.getByPlaceholderText(/paper_id listesi/i), {
      target: { value: "s2_1234, s2_5678" },
    });

    apiFetchMock.mockResolvedValueOnce(balanceStub);
    fireEvent.click(screen.getByRole("button", { name: /^Dengele$/i }));

    await waitFor(() => {
      expect(screen.getByText(/Daha güncel kaynak ekle/)).toBeTruthy();
      expect(screen.getByText(/Recent MCDM survey 2024/)).toBeTruthy();
    });

    expect(apiFetchMock).toHaveBeenCalledWith(
      "/api/workshop/citation-balance",
      expect.objectContaining({
        method: "POST",
        body: expect.objectContaining({
          project_id: PROJECT_ID,
          citation_paper_ids: ["s2_1234", "s2_5678"],
        }),
      }),
    );
  });
});
