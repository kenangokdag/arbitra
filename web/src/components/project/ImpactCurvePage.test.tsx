// kaynak: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S11.3
// ImpactCurvePage RTL — GET /api/workshop/impact-curve binding.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { ImpactCurvePage } from "./ImpactCurvePage";

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

const impactStub = {
  dimension: "topic" as const,
  value: "T1234",
  academic_series: [
    { year: 2018, value: 10 },
    { year: 2019, value: 14 },
    { year: 2020, value: 22 },
    { year: 2021, value: 28 },
  ],
  trends_series: [],
  trends_available: false,
  stars: [
    {
      paper_id: "W1",
      title: "Disruptive TOPSIS paper",
      year: 2020,
      cd_5: 0.78,
    },
  ],
  beauties: [
    {
      paper_id: "W2",
      title: "Latent factor MCDM",
      publication_year: 2010,
      awakening_year: 2021,
      b: 14.2,
    },
  ],
  academic_slope_pct: 18.5,
  trends_slope: null,
  momentum_color: "green" as const,
  llm_comment: "Bu konuda son 4 yılda yıllık %18 büyüme görülüyor.",
};

beforeEach(() => {
  apiFetchMock.mockReset();
});

afterEach(() => cleanup());

describe("ImpactCurvePage", () => {
  it("ilk render → form var, fetch yok, sonuç boş", () => {
    render(<ImpactCurvePage />);
    expect(screen.getByLabelText(/Boyut/i)).toBeTruthy();
    expect(screen.getByLabelText(/Değer/i)).toBeTruthy();
    const btn = screen.getByRole("button", { name: /Eğriyi getir/i }) as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("değer + Eğriyi getir → impact-curve fetch + chart render", async () => {
    render(<ImpactCurvePage />);

    fireEvent.change(screen.getByLabelText(/Değer/i), { target: { value: "T1234" } });
    apiFetchMock.mockResolvedValueOnce(impactStub);
    fireEvent.click(screen.getByRole("button", { name: /Eğriyi getir/i }));

    await waitFor(() => {
      expect(screen.getByText(/Disruptive TOPSIS paper/)).toBeTruthy();
      expect(screen.getByText(/Latent factor MCDM/)).toBeTruthy();
      expect(screen.getByTestId("momentum-badge")).toBeTruthy();
      expect(screen.getByText(/18\.5%\/yıl/)).toBeTruthy();
      expect(screen.getByText(/Bu konuda son 4 yılda/)).toBeTruthy();
    });

    const call = apiFetchMock.mock.calls[0];
    expect(call?.[0]).toContain("/api/workshop/impact-curve?");
    expect(call?.[0]).toContain(`project_id=${PROJECT_ID}`);
    expect(call?.[0]).toContain("dimension=topic");
    expect(call?.[0]).toContain("value=T1234");
    expect(call?.[0]).toContain("years=10");
  });

  it("boyut method → dimension=method query'de", async () => {
    render(<ImpactCurvePage />);

    fireEvent.change(screen.getByLabelText(/Boyut/i), { target: { value: "method" } });
    fireEvent.change(screen.getByLabelText(/Değer/i), { target: { value: "M5" } });
    apiFetchMock.mockResolvedValueOnce({
      ...impactStub,
      dimension: "method" as const,
      value: "M5",
    });
    fireEvent.click(screen.getByRole("button", { name: /Eğriyi getir/i }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalled();
    });
    const call = apiFetchMock.mock.calls.at(-1);
    expect(call?.[0]).toContain("dimension=method");
    expect(call?.[0]).toContain("value=M5");
  });

  it("trends_available=false → 'trend verisi yok' rozeti", async () => {
    render(<ImpactCurvePage />);
    fireEvent.change(screen.getByLabelText(/Değer/i), { target: { value: "T1" } });
    apiFetchMock.mockResolvedValueOnce(impactStub);
    fireEvent.click(screen.getByRole("button", { name: /Eğriyi getir/i }));

    await waitFor(() => {
      expect(screen.getByText(/trend verisi yok/i)).toBeTruthy();
    });
  });

  it("yıllar değişimi → years query'de", async () => {
    render(<ImpactCurvePage />);
    fireEvent.change(screen.getByLabelText(/Değer/i), { target: { value: "T1" } });
    fireEvent.change(screen.getByLabelText(/Yıl penceresi/i), { target: { value: "5" } });
    apiFetchMock.mockResolvedValueOnce(impactStub);
    fireEvent.click(screen.getByRole("button", { name: /Eğriyi getir/i }));

    await waitFor(() => {
      const call = apiFetchMock.mock.calls.at(-1);
      expect(call?.[0]).toContain("years=5");
    });
  });
});
