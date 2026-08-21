// kaynak: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S11.2
// OriginalityPage RTL — GET /api/workshop/originality binding.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { OriginalityPage } from "./OriginalityPage";

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

const disruptionStub = {
  type: "disruption" as const,
  papers: [
    {
      paper_id: "W1",
      title: "TOPSIS limitations under correlated criteria",
      year: 2020,
      venue: "Expert Sys",
      cd_5: 0.78,
      n_a: 25,
      n_i: 5,
      n_j: 70,
      total_window_papers: 100,
      b: null,
      t_m: null,
      c_max: null,
      total_cites: null,
    },
    {
      paper_id: "W2",
      title: "Causal MCDM in education",
      year: 2023,
      venue: "JEdu",
      cd_5: 0.52,
      n_a: 10,
      n_i: 8,
      n_j: 82,
      total_window_papers: 100,
      b: null,
      t_m: null,
      c_max: null,
      total_cites: null,
    },
  ],
  threshold_used: 0.5,
  threshold_source: "calibrated",
  pool_size: 250,
};

const beautyStub = {
  type: "sleeping_beauty" as const,
  papers: [
    {
      paper_id: "W3",
      title: "Latent factor MCDM model",
      year: 2008,
      venue: "Omega",
      cd_5: null,
      n_a: null,
      n_i: null,
      n_j: null,
      total_window_papers: null,
      b: 14.2,
      t_m: 14,
      c_max: 80,
      total_cites: 320,
    },
  ],
  threshold_used: 5.0,
  threshold_source: "calibrated",
  pool_size: 250,
};

beforeEach(() => {
  apiFetchMock.mockReset();
});

afterEach(() => cleanup());

describe("OriginalityPage", () => {
  it("mount → disruption tab fetch + 2 satır + pool/threshold render", async () => {
    apiFetchMock.mockResolvedValueOnce(disruptionStub);
    render(<OriginalityPage />);

    await waitFor(() => {
      expect(screen.getByText(/TOPSIS limitations/)).toBeTruthy();
      expect(screen.getByText(/Causal MCDM/)).toBeTruthy();
      expect(screen.getAllByTestId("originality-row")).toHaveLength(2);
      expect(screen.getByText(/250/)).toBeTruthy();
    });

    const call = apiFetchMock.mock.calls[0];
    expect(call?.[0]).toContain("/api/workshop/originality?");
    expect(call?.[0]).toContain(`project_id=${PROJECT_ID}`);
    expect(call?.[0]).toContain("type=disruption");
  });

  it("Uyuyan Güzel tab → type=sleeping_beauty fetch + B kolonu", async () => {
    apiFetchMock.mockResolvedValueOnce(disruptionStub);
    render(<OriginalityPage />);
    await screen.findByText(/TOPSIS limitations/);

    apiFetchMock.mockResolvedValueOnce(beautyStub);
    fireEvent.click(screen.getByRole("button", { name: /Uyuyan Güzel/i }));

    await waitFor(() => {
      expect(screen.getByText(/Latent factor MCDM/)).toBeTruthy();
      expect(screen.getByText(/14\.20/)).toBeTruthy();
    });

    const lastCall = apiFetchMock.mock.calls.at(-1);
    expect(lastCall?.[0]).toContain("type=sleeping_beauty");
  });

  it("filtre uygula → year_from + year_to query string'e eklenir", async () => {
    apiFetchMock.mockResolvedValueOnce(disruptionStub);
    render(<OriginalityPage />);
    await screen.findByText(/TOPSIS limitations/);

    fireEvent.change(screen.getByLabelText(/Yıl başlangıç/i), {
      target: { value: "2018" },
    });
    fireEvent.change(screen.getByLabelText(/Yıl bitiş/i), {
      target: { value: "2024" },
    });

    apiFetchMock.mockResolvedValueOnce(disruptionStub);
    fireEvent.click(screen.getByRole("button", { name: /Filtreyi uygula/i }));

    await waitFor(() => {
      const lastCall = apiFetchMock.mock.calls.at(-1);
      expect(lastCall?.[0]).toContain("year_from=2018");
      expect(lastCall?.[0]).toContain("year_to=2024");
    });
  });

  it("empty papers → boş mesaj render", async () => {
    apiFetchMock.mockResolvedValueOnce({
      type: "disruption",
      papers: [],
      threshold_used: 0.5,
      threshold_source: "calibrated",
      pool_size: 0,
    });
    render(<OriginalityPage />);

    await waitFor(() => {
      expect(
        screen.getByText(/Eşiğin üzerinde makale yok/i),
      ).toBeTruthy();
    });
  });
});
