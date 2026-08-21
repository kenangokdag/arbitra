// V1-S17 P004 — ThematicAnalysisPage gap-heatmap'e project_id geçirir.
// Plan: docs/plans/V1_S17_cascade_5rc.md §4 C004.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

import { ThematicAnalysisPage } from "./ThematicAnalysisPage";

const apiFetchMock = vi.fn();

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "prj-xyz" }),
}));

vi.mock("@/lib/api", () => ({
  apiFetch: (path: string, opts?: unknown) => apiFetchMock(path, opts),
}));

const heatmapStub = {
  methods: [{ id: "topsis", label: "Topsis", family: "Reference-based" }],
  topics: [{ id: "T_med", label: "Tıp", group: "Health" }],
  cells: [
    { method_id: "topsis", topic_id: "T_med", n_papers: 10, gap_score: 0.8, depth_norm: 0.4, is_gold: true },
  ],
  total_cells: 1,
  matrix_id: "M1",
};

function withQuery(ui: ReactNode): ReactNode {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{ui}</QueryClientProvider>;
}

beforeEach(() => {
  apiFetchMock.mockReset();
});

afterEach(() => cleanup());

describe("ThematicAnalysisPage — V1-S17 P004", () => {
  it("projectId varken /api/gap-heatmap'e project_id query param geçirir", async () => {
    apiFetchMock.mockResolvedValue(heatmapStub);
    render(withQuery(<ThematicAnalysisPage />));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledTimes(1);
    });
    const [calledPath] = apiFetchMock.mock.calls[0]!;
    expect(calledPath).toContain("top_methods=14");
    expect(calledPath).toContain("top_topics=30");
    expect(calledPath).toContain("project_id=prj-xyz");
  });

  it("yanıt geldikten sonra spinner kalkıp tema gruplari paneli render olur", async () => {
    apiFetchMock.mockResolvedValue(heatmapStub);
    const { findByText, queryByText } = render(withQuery(<ThematicAnalysisPage />));

    expect(await findByText(/Tema Gruplari/)).toBeTruthy();
    expect(queryByText(/Tema verileri yukleniyor/i)).toBeNull();
  });
});
