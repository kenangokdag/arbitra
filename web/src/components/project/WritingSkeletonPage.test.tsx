import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { WritingSkeletonPage } from "./WritingSkeletonPage";

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

const proposalsStub = {
  proposals: [
    {
      title: "Bulanık TOPSIS ile tedarikçi seçimi",
      sub_questions: {
        cautious: "Bulanık TOPSIS hangi kriterleri içerir?",
        balanced: "Bulanık TOPSIS klasik TOPSIS'e göre nasıl?",
        bold: "Bulanık TOPSIS kararı tek başına yeter mi?",
      },
      top_3_refs: ["Chen 2000", "Hwang 1981", "Zadeh 1965"],
      method_suggestion: "Bulanık TOPSIS + duyarlılık analizi",
      evidence_chain: {
        gap_summary: "M1 boşluğunda bulanık varyantlar az",
        method_summary: "TOPSIS dominant ama bulanık tap az",
        synthesis_summary: "Sentez metnine göre yöntem boşluğu net",
      },
    },
    {
      title: "VIKOR ile sürdürülebilir seçim",
      sub_questions: { cautious: "c2", balanced: "b2", bold: "bo2" },
      top_3_refs: ["Opricovic 1998"],
      method_suggestion: "VIKOR",
      evidence_chain: {
        gap_summary: "g2 summary",
        method_summary: "m2 summary",
        synthesis_summary: "s2 summary",
      },
    },
    {
      title: "AHP karşılaştırma yaklaşımı",
      sub_questions: { cautious: "c3", balanced: "b3", bold: "bo3" },
      top_3_refs: ["Saaty 1980"],
      method_suggestion: "AHP",
      evidence_chain: {
        gap_summary: "g3 summary",
        method_summary: "m3 summary",
        synthesis_summary: "s3 summary",
      },
    },
  ],
  generation_count: 1,
  daily_quota_remaining: 4,
  lang: "tr" as const,
};

const skeletonStub = {
  sections: [
    {
      name: "intro" as const,
      draft_paragraph: "Giriş paragrafı: bulanık MCDM araştırması.",
      why_explanation: "M1 boşluğu konusu net.",
      top_5_papers: [
        {
          paper_id: "p1",
          title: "Fuzzy TOPSIS Review",
          year: 2020,
          authors_short: "Chen et al.",
          citations_count: 120,
        },
      ],
    },
    {
      name: "methods" as const,
      draft_paragraph: "Yöntem paragrafı.",
      why_explanation: "TOPSIS gerekçesi.",
      top_5_papers: [],
    },
    {
      name: "findings" as const,
      draft_paragraph: "Bulgular paragrafı.",
      why_explanation: "Veri sunumu.",
      top_5_papers: [],
    },
    {
      name: "discussion" as const,
      draft_paragraph: "Tartışma paragrafı.",
      why_explanation: "Sonuç yorumu.",
      top_5_papers: [],
    },
  ],
  lang: "tr" as const,
};

beforeEach(() => {
  apiFetchMock.mockReset();
});

afterEach(() => cleanup());

describe("WritingSkeletonPage", () => {
  it("Eksen bos iken '3 konu oner' butonu disabled", () => {
    render(<WritingSkeletonPage />);
    const btn = screen.getByRole("button", { name: /3 konu öner/i }) as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
  });

  it("eksen + buton → POST /topic-proposals + 3 kart + kota gosterimi", async () => {
    render(<WritingSkeletonPage />);
    fireEvent.change(screen.getByPlaceholderText(/bulanık ortam/i), {
      target: { value: "bulanık" },
    });
    fireEvent.change(screen.getByPlaceholderText(/Örn: TOPSIS/i), {
      target: { value: "TOPSIS" },
    });

    apiFetchMock.mockResolvedValueOnce(proposalsStub);
    fireEvent.click(screen.getByRole("button", { name: /3 konu öner/i }));

    await waitFor(() => {
      expect(screen.getByText(/Bulanık TOPSIS ile tedarikçi seçimi/)).toBeTruthy();
      expect(screen.getByText(/VIKOR ile sürdürülebilir/)).toBeTruthy();
      expect(screen.getByText(/AHP karşılaştırma/)).toBeTruthy();
      expect(screen.getByText(/Üretim 1 · kota 4/)).toBeTruthy();
    });

    expect(apiFetchMock).toHaveBeenCalledWith(
      "/api/workshop/topic-proposals",
      expect.objectContaining({
        method: "POST",
        body: expect.objectContaining({
          project_id: PROJECT_ID,
          gap_matrix_id: "M1",
          gap_axis_x: "bulanık",
          gap_axis_y: "TOPSIS",
          lang: "tr",
        }),
      }),
    );
  });

  it("kart sec → İskeleti olustur → POST /draft-skeleton + IMRaD render", async () => {
    render(<WritingSkeletonPage />);
    fireEvent.change(screen.getByPlaceholderText(/bulanık ortam/i), {
      target: { value: "x" },
    });
    fireEvent.change(screen.getByPlaceholderText(/Örn: TOPSIS/i), {
      target: { value: "y" },
    });

    apiFetchMock.mockResolvedValueOnce(proposalsStub);
    fireEvent.click(screen.getByRole("button", { name: /3 konu öner/i }));

    await waitFor(() => {
      expect(screen.getByText(/Bulanık TOPSIS ile tedarikçi/)).toBeTruthy();
    });

    fireEvent.click(screen.getAllByRole("button", { name: /Bu konuyu seç/i })[0]!);

    apiFetchMock.mockResolvedValueOnce(skeletonStub);
    fireEvent.click(screen.getByRole("button", { name: /İskeleti oluştur/i }));

    await waitFor(() => {
      expect(screen.getByText(/IMRaD İskeleti/)).toBeTruthy();
      expect(screen.getByText(/Giriş paragrafı: bulanık MCDM/)).toBeTruthy();
      expect(screen.getByText(/Fuzzy TOPSIS Review/)).toBeTruthy();
    });

    expect(apiFetchMock).toHaveBeenCalledWith(
      "/api/workshop/draft-skeleton",
      expect.objectContaining({
        method: "POST",
        body: expect.objectContaining({
          project_id: PROJECT_ID,
          selected_topic: expect.objectContaining({
            title: "Bulanık TOPSIS ile tedarikçi seçimi",
          }),
        }),
      }),
    );
  });
});
