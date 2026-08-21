import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { JournalSimulationPage } from "./JournalSimulationPage";

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

const SESSION_ID = "22222222-2222-2222-2222-222222222222";
const PROJECT_ID = "11111111-1111-1111-1111-111111111111";
const STORAGE_KEY = `defense_session:${PROJECT_ID}`;
const longManuscript = "X".repeat(200);

const manuscriptStub = {
  project_id: PROJECT_ID,
  sections: [
    { section_type: "intro", content: longManuscript, word_count: longManuscript.length },
  ],
};

const reviewersStub = {
  session_id: SESSION_ID,
  skeptik: {
    questions: [
      { text: "Hipotezin altı boş.", depth: 1, follow_up: null, anchor: null },
    ],
  },
  sempatik: {
    questions: [
      { text: "Yöntem güçlü, ama örneklem dar.", depth: 1, follow_up: null, anchor: null },
    ],
  },
  yontemci: {
    questions: [
      { text: "Levene testi raporlanmamış.", depth: 1, follow_up: "Eklenmeli mi?", anchor: null },
    ],
  },
};

const statcheckStub = {
  session_id: SESSION_ID,
  results: [
    {
      test_type: "t" as const,
      reported: { t: 2.4, df: 30 },
      reported_p: 0.02,
      computed_p: 0.022,
      diff: 0.002,
      status: "green" as const,
      match_text: "t(30) = 2.4, p = .02",
    },
    {
      test_type: "F" as const,
      reported: { F: 5.1, df1: 2, df2: 50 },
      reported_p: 0.01,
      computed_p: 0.04,
      diff: 0.03,
      status: "red" as const,
      match_text: "F(2,50) = 5.1, p = .01",
    },
  ],
  summary: { total: 2, green: 1, yellow: 0, red: 1 },
};

const calibrationStub = {
  journal_id: "j-or",
  journal_name: "JORS",
  distribution: {
    window_size: 40,
    accept_pct: 0.1,
    minor_pct: 0.3,
    major_pct: 0.4,
    reject_pct: 0.2,
    source: "manual" as const,
  },
  prediction: "minor" as const,
  confidence: 0.68,
  fallback_used: false,
};

beforeEach(() => {
  apiFetchMock.mockReset();
  window.localStorage.clear();
});

afterEach(() => cleanup());

describe("JournalSimulationPage", () => {
  it("manuscript GET'i mount'ta cagirir + bolum sayisi gosterir", async () => {
    apiFetchMock.mockResolvedValueOnce(manuscriptStub);
    render(<JournalSimulationPage />);

    await waitFor(() => {
      expect(screen.getByText(/1 bölüm/)).toBeTruthy();
    });

    const paths = apiFetchMock.mock.calls.map((c) => c[0] as string);
    expect(paths.some((p) => p.startsWith("/api/workshop/manuscript"))).toBe(true);
  });

  it("session yokken hakem butonu disabled", async () => {
    apiFetchMock.mockResolvedValueOnce(manuscriptStub);
    render(<JournalSimulationPage />);
    await waitFor(() => expect(screen.getByText(/1 bölüm/)).toBeTruthy());

    const btn = screen.getByRole("button", { name: /Hakem çalıştır/i }) as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
    expect(screen.getByText(/5\.1 Savunma Formatı/)).toBeTruthy();
  });

  it("3-persona endpoint cagrisi ve 3 persona render", async () => {
    window.localStorage.setItem(STORAGE_KEY, SESSION_ID);
    apiFetchMock.mockResolvedValueOnce(manuscriptStub);
    render(<JournalSimulationPage />);
    await waitFor(() => expect(screen.getByText(/1 bölüm/)).toBeTruthy());

    apiFetchMock.mockResolvedValueOnce(reviewersStub);
    fireEvent.click(screen.getByRole("button", { name: /Hakem çalıştır/i }));

    await waitFor(() => {
      expect(screen.getByText(/Hipotezin altı boş/)).toBeTruthy();
      expect(screen.getByText(/Yöntem güçlü/)).toBeTruthy();
      expect(screen.getByText(/Levene testi raporlanmamış/)).toBeTruthy();
    });

    expect(apiFetchMock).toHaveBeenCalledWith(
      "/api/workshop/defense/reviewer-3persona",
      expect.objectContaining({
        method: "POST",
        body: expect.objectContaining({
          session_id: SESSION_ID,
          manuscript_text: longManuscript,
          lang: "tr",
        }),
      }),
    );
  });

  it("statcheck endpoint + green/yellow/red chip + result rows", async () => {
    window.localStorage.setItem(STORAGE_KEY, SESSION_ID);
    apiFetchMock.mockResolvedValueOnce(manuscriptStub);
    render(<JournalSimulationPage />);
    await waitFor(() => expect(screen.getByText(/1 bölüm/)).toBeTruthy());

    apiFetchMock.mockResolvedValueOnce(statcheckStub);
    fireEvent.click(screen.getByRole("button", { name: /Statcheck çalıştır/i }));

    await waitFor(() => {
      expect(screen.getByText(/Toplam: 2/)).toBeTruthy();
      expect(screen.getByText(/Green: 1/)).toBeTruthy();
      expect(screen.getByText(/Red: 1/)).toBeTruthy();
      expect(screen.getByText(/t\(30\) = 2.4/)).toBeTruthy();
      expect(screen.getByText(/F\(2,50\) = 5.1/)).toBeTruthy();
    });

    expect(apiFetchMock).toHaveBeenCalledWith(
      "/api/workshop/defense/statcheck",
      expect.objectContaining({
        method: "POST",
        body: expect.objectContaining({
          session_id: SESSION_ID,
          manuscript_text: longManuscript,
        }),
      }),
    );
  });

  it("calibration endpoint + verdict + distribution render", async () => {
    window.localStorage.setItem(STORAGE_KEY, SESSION_ID);
    apiFetchMock.mockResolvedValueOnce(manuscriptStub);
    render(<JournalSimulationPage />);
    await waitFor(() => expect(screen.getByText(/1 bölüm/)).toBeTruthy());

    fireEvent.change(screen.getByPlaceholderText(/Dergi ID/i), {
      target: { value: "j-or" },
    });

    apiFetchMock.mockResolvedValueOnce(calibrationStub);
    fireEvent.click(screen.getByRole("button", { name: /Kalibrasyonu çalıştır/i }));

    await waitFor(() => {
      expect(screen.getByText("JORS")).toBeTruthy();
      expect(screen.getByText(/Küçük Revizyon · güven 68%/)).toBeTruthy();
    });

    const paths = apiFetchMock.mock.calls.map((c) => c[0] as string);
    expect(paths.some((p) => p.startsWith("/api/workshop/defense/journal-calibration"))).toBe(true);
    expect(paths.some((p) => p.includes(`session_id=${SESSION_ID}`))).toBe(true);
    expect(paths.some((p) => p.includes("journal_id=j-or"))).toBe(true);
  });

  it("kisa manuscript hakem butonunu disable eder", async () => {
    apiFetchMock.mockResolvedValueOnce({
      project_id: PROJECT_ID,
      sections: [{ section_type: "intro", content: "kısa", word_count: 4 }],
    });
    window.localStorage.setItem(STORAGE_KEY, SESSION_ID);
    render(<JournalSimulationPage />);
    await waitFor(() => expect(screen.getByText(/en az 100 karakter/i)).toBeTruthy());
    const btn = screen.getByRole("button", { name: /Hakem çalıştır/i }) as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
  });
});
