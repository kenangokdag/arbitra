// kaynak: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S11.1
// LiteratureSummaryPage RTL — project papers fetch + synthesize binding.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { LiteratureSummaryPage } from "./LiteratureSummaryPage";

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

const papersStub = {
  project_id: PROJECT_ID,
  papers: [
    {
      paper_id: "W1",
      title: "Adaptive learning systems",
      abstract: "abs1",
      authors: ["Smith J"],
      year: 2024,
      venue: "JEdu",
      doi: null,
      citations_count: 12,
    },
    {
      paper_id: "W2",
      title: "Online platforms in higher education",
      abstract: "abs2",
      authors: ["Doe A"],
      year: 2023,
      venue: "Comput Edu",
      doi: null,
      citations_count: 5,
    },
  ],
  hydrated_count: 0,
};

const synthesizeStub = {
  synthesis_text: "Adaptif öğrenme sistemleri öğrenci başarısını artırır.\n\nİkinci paragraf.",
  sentences: [
    {
      text: "Adaptif öğrenme sistemleri öğrenci başarısını artırır.",
      citations: ["W1"],
      faithfulness_score: 0.72,
      flag: "green" as const,
    },
    {
      text: "İkinci paragraf.",
      citations: ["W2"],
      faithfulness_score: 0.45,
      flag: "yellow" as const,
    },
  ],
  references: [
    { index: 1, paper_id: "W1", citation: "Smith J. (2024). Adaptive..." },
    { index: 2, paper_id: "W2", citation: "Doe A. (2023). Online..." },
  ],
  total_faithfulness: 0.58,
  theme_warning: null,
  mode: "neutral" as const,
  lang: "tr" as const,
};

beforeEach(() => {
  apiFetchMock.mockReset();
});

afterEach(() => cleanup());

describe("LiteratureSummaryPage", () => {
  it("mount → GET /api/project/{id}/papers + 2 makale render", async () => {
    apiFetchMock.mockResolvedValueOnce(papersStub);
    render(<LiteratureSummaryPage />);

    await waitFor(() => {
      expect(screen.getByText(/Adaptive learning systems/)).toBeTruthy();
      expect(screen.getByText(/Online platforms/)).toBeTruthy();
    });

    expect(apiFetchMock).toHaveBeenCalledWith(
      `/api/project/${PROJECT_ID}/papers`,
      undefined,
    );
  });

  it("makale seçim + Sentezle → POST /workshop/synthesize body doğru", async () => {
    apiFetchMock.mockResolvedValueOnce(papersStub);
    render(<LiteratureSummaryPage />);

    const checkbox = await screen.findByLabelText(/Adaptive learning systems seç/i);
    fireEvent.click(checkbox);

    apiFetchMock.mockResolvedValueOnce(synthesizeStub);
    fireEvent.click(screen.getByRole("button", { name: /^Sentezle$/i }));

    await waitFor(() => {
      const synthCall = apiFetchMock.mock.calls.find(
        (c) => c[0] === "/api/workshop/synthesize",
      );
      expect(synthCall).toBeTruthy();
      expect(synthCall?.[1]).toMatchObject({
        method: "POST",
        body: {
          project_id: PROJECT_ID,
          paper_ids: ["W1"],
          mode: "neutral",
        },
      });
      // lang boşken body'de gönderilmemeli
      expect((synthCall?.[1] as { body: Record<string, unknown> })?.body?.lang).toBeUndefined();
    });
  });

  it("sentez sonucu → synthesis_text + faithfulness badges + references render", async () => {
    apiFetchMock.mockResolvedValueOnce(papersStub);
    render(<LiteratureSummaryPage />);

    const checkbox = await screen.findByLabelText(/Adaptive learning systems seç/i);
    fireEvent.click(checkbox);

    apiFetchMock.mockResolvedValueOnce(synthesizeStub);
    fireEvent.click(screen.getByRole("button", { name: /^Sentezle$/i }));

    await waitFor(() => {
      // synthesis paragraph + sentence row → 2 ayrı element
      const matches = screen.getAllByText(
        /Adaptif öğrenme sistemleri öğrenci başarısını artırır\./,
      );
      expect(matches.length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText(/Sadakat 58%/)).toBeTruthy();
      const rows = screen.getAllByTestId("synth-sentence");
      expect(rows).toHaveLength(2);
      expect(screen.getByText(/Smith J\. \(2024\)/)).toBeTruthy();
    });
  });

  it("mode toggle → critical seçilince body.mode='critical'", async () => {
    apiFetchMock.mockResolvedValueOnce(papersStub);
    render(<LiteratureSummaryPage />);

    fireEvent.click(await screen.findByLabelText(/Adaptive learning systems seç/i));
    fireEvent.click(screen.getByRole("button", { name: /^Eleştirel$/i }));

    apiFetchMock.mockResolvedValueOnce(synthesizeStub);
    fireEvent.click(screen.getByRole("button", { name: /^Sentezle$/i }));

    await waitFor(() => {
      const synthCall = apiFetchMock.mock.calls.find(
        (c) => c[0] === "/api/workshop/synthesize",
      );
      expect((synthCall?.[1] as { body: { mode: string } })?.body?.mode).toBe(
        "critical",
      );
    });
  });

  it("lang EN seçilirse body.lang='en'", async () => {
    apiFetchMock.mockResolvedValueOnce(papersStub);
    render(<LiteratureSummaryPage />);

    fireEvent.click(await screen.findByLabelText(/Adaptive learning systems seç/i));
    fireEvent.click(screen.getByRole("button", { name: /^EN$/ }));

    apiFetchMock.mockResolvedValueOnce(synthesizeStub);
    fireEvent.click(screen.getByRole("button", { name: /^Sentezle$/i }));

    await waitFor(() => {
      const synthCall = apiFetchMock.mock.calls.find(
        (c) => c[0] === "/api/workshop/synthesize",
      );
      expect((synthCall?.[1] as { body: { lang?: string } })?.body?.lang).toBe(
        "en",
      );
    });
  });

  it("0 seçim → Sentezle disabled", async () => {
    apiFetchMock.mockResolvedValueOnce(papersStub);
    render(<LiteratureSummaryPage />);

    await screen.findByText(/Adaptive learning systems/);
    const btn = screen.getByRole("button", { name: /^Sentezle$/i }) as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
  });
});
