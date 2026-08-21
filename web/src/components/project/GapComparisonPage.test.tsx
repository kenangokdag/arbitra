import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { GapComparisonPage } from "./GapComparisonPage";

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

const compareStub = {
  gaps: [
    {
      cell: { matrix_id: "M1", axis_x: "TOPSIS", axis_y: "ESG" },
      axes: {
        risk: 0.34,
        disruption: 0.78,
        virgin: 0.62,
        sleeping_beauty: 0.41,
        publishability: 0.71,
      },
      weighted_score: 0.58,
      top_papers: [
        {
          paper_id: "p1",
          title: "Fuzzy TOPSIS for ESG performance",
          year: 2023,
          venue: "Expert Sys",
          q_weak: 0.6,
        },
      ],
    },
    {
      cell: { matrix_id: "M1", axis_x: "AHP", axis_y: "Sustainability" },
      axes: {
        risk: 0.52,
        disruption: 0.61,
        virgin: 0.45,
        sleeping_beauty: 0.30,
        publishability: 0.65,
      },
      weighted_score: 0.51,
      top_papers: [],
    },
  ],
  weights: {
    risk: 0.2,
    disruption: 0.2,
    virgin: 0.2,
    sleeping_beauty: 0.2,
    publishability: 0.2,
  },
  recommendation_text: "TOPSIS×ESG hücresi daha yüksek yıkıcılık + yayımlanabilirlik dengesi sunar.",
};

beforeEach(() => {
  apiFetchMock.mockReset();
});

afterEach(() => cleanup());

describe("GapComparisonPage", () => {
  it("ilk render: 2 bos hucre + Karsilastir disabled + fetch yok", () => {
    render(<GapComparisonPage />);
    expect(screen.getByText(/Karşılaştırılacak boşluklar/)).toBeTruthy();
    const btn = screen.getByRole("button", { name: /^Karşılaştır$/i }) as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("Hucre ekle → 3. hucre + 5. sonra disabled", () => {
    render(<GapComparisonPage />);
    const addBtn = screen.getByRole("button", { name: /Hücre ekle/i });
    fireEvent.click(addBtn);
    fireEvent.click(addBtn);
    fireEvent.click(addBtn);
    // 5 hücre olunca disabled
    const addBtnAfter = screen.getByRole("button", { name: /Hücre ekle/i }) as HTMLButtonElement;
    expect(addBtnAfter.disabled).toBe(true);
  });

  it("axes dolu → POST /compare + 2 kart + LLM oneri render", async () => {
    render(<GapComparisonPage />);
    const xInputs = screen.getAllByPlaceholderText(/axis_x/i);
    const yInputs = screen.getAllByPlaceholderText(/axis_y/i);
    fireEvent.change(xInputs[0]!, { target: { value: "TOPSIS" } });
    fireEvent.change(yInputs[0]!, { target: { value: "ESG" } });
    fireEvent.change(xInputs[1]!, { target: { value: "AHP" } });
    fireEvent.change(yInputs[1]!, { target: { value: "Sustainability" } });

    apiFetchMock.mockResolvedValueOnce(compareStub);
    fireEvent.click(screen.getByRole("button", { name: /^Karşılaştır$/i }));

    await waitFor(() => {
      expect(screen.getByText(/TOPSIS × ESG/)).toBeTruthy();
      expect(screen.getByText(/AHP × Sustainability/)).toBeTruthy();
      expect(screen.getByText(/Danışman önerisi/)).toBeTruthy();
      expect(screen.getByText(/TOPSIS×ESG hücresi daha yüksek/)).toBeTruthy();
    });

    expect(apiFetchMock).toHaveBeenCalledWith(
      "/api/workshop/compare",
      expect.objectContaining({
        method: "POST",
        body: expect.objectContaining({
          project_id: PROJECT_ID,
          gap_cells: [
            { matrix_id: "M1", axis_x: "TOPSIS", axis_y: "ESG" },
            { matrix_id: "M1", axis_x: "AHP", axis_y: "Sustainability" },
          ],
          weights: expect.objectContaining({
            risk: 0.2,
            disruption: 0.2,
            virgin: 0.2,
            sleeping_beauty: 0.2,
            publishability: 0.2,
          }),
        }),
      }),
    );
  });
});
