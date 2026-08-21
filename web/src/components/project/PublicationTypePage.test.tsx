import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { PublicationTypePage } from "./PublicationTypePage";

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

const maturityNotReadyStub = {
  project_id: PROJECT_ID,
  publication_type: "tez" as const,
  steps: [
    { step_id: "5.1", status: "completed" as const, required: true, completed_at: "2026-05-10T09:00:00Z" },
    { step_id: "5.2", status: "in_progress" as const, required: true, completed_at: null },
    { step_id: "5.3", status: "not_started" as const, required: false, completed_at: null },
  ],
  maturity_pct: 42.5,
  button_active: false,
  required_total: 2,
  required_completed: 1,
};

const maturityReadyStub = {
  ...maturityNotReadyStub,
  publication_type: "makale" as const,
  maturity_pct: 95.0,
  button_active: true,
  required_total: 2,
  required_completed: 2,
};

const summaryStub = {
  summary: "Bu çalışmada MCDM yöntemlerinin karşılaştırması yapılmıştır.\n\nYöntem TOPSIS + VIKOR.",
  publication_type: "makale" as const,
  step_count_used: 6,
  cache_hit: false,
};

beforeEach(() => {
  apiFetchMock.mockReset();
});

afterEach(() => cleanup());

describe("PublicationTypePage", () => {
  it("3 yayim turu karti render + ilk acilis fetch yok", () => {
    render(<PublicationTypePage />);
    expect(screen.getByText("Tez")).toBeTruthy();
    expect(screen.getByText("Makale")).toBeTruthy();
    expect(screen.getByText("Bildiri")).toBeTruthy();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("Tez sec → GET /maturity + checklist + buton disabled", async () => {
    apiFetchMock.mockResolvedValueOnce(maturityNotReadyStub);
    render(<PublicationTypePage />);
    fireEvent.click(screen.getAllByRole("button", { name: /^Sec$/i })[0]!);

    await waitFor(() => {
      expect(screen.getByText(/Olgunluk · tez/)).toBeTruthy();
    });
    expect(screen.getByText(/%43/)).toBeTruthy();
    expect(screen.getByText(/1\/2 zorunlu/)).toBeTruthy();

    const btn = screen.getByRole("button", { name: /Danışmana Gitmeden Evvel/i }) as HTMLButtonElement;
    expect(btn.disabled).toBe(true);

    const paths = apiFetchMock.mock.calls.map((c) => c[0] as string);
    expect(paths.some((p) => p.startsWith("/api/workshop/maturity"))).toBe(true);
    expect(paths.some((p) => p.includes("publication_type=tez"))).toBe(true);
  });

  it("Makale ready → POST /advisor-summary + ozet paragraf render", async () => {
    apiFetchMock.mockResolvedValueOnce(maturityReadyStub);
    render(<PublicationTypePage />);
    const secButtons = screen.getAllByRole("button", { name: /^Sec$/i });
    fireEvent.click(secButtons[1]!); // makale

    await waitFor(() => {
      expect(screen.getByText(/Olgunluk · makale/)).toBeTruthy();
    });

    apiFetchMock.mockResolvedValueOnce(summaryStub);
    fireEvent.click(screen.getByRole("button", { name: /Danışmana Gitmeden Evvel/i }));

    await waitFor(() => {
      expect(screen.getByText(/Bu çalışmada MCDM/)).toBeTruthy();
      expect(screen.getByText(/6 adım · yeni/)).toBeTruthy();
    });

    expect(apiFetchMock).toHaveBeenCalledWith(
      "/api/workshop/advisor-summary",
      expect.objectContaining({
        method: "POST",
        body: expect.objectContaining({
          project_id: PROJECT_ID,
          publication_type: "makale",
        }),
      }),
    );
  });
});
