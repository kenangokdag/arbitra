import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { JurySimulationPage } from "./JurySimulationPage";

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
const longManuscript = "X".repeat(200);

const sessionStub = {
  id: SESSION_ID,
  project_id: "11111111-1111-1111-1111-111111111111",
  session_type: "tez",
  jury_size: 5,
  title: "Tez Savunması",
  field: "Genel",
  preferred_lang: "tr",
};

const manuscriptStub = (text: string) => ({
  project_id: "11111111-1111-1111-1111-111111111111",
  sections: [
    { section_type: "intro", content: text, word_count: text.length },
  ],
});

const juryQuestionStub = {
  session_id: SESSION_ID,
  questions: [
    { persona: "canli", idx: 0, text: "Tezin özü nedir?", depth: 1, parent_idx: null, anchor: null },
    { persona: "anti_tez", idx: 1, text: "Karşı argüman nedir?", depth: 1, parent_idx: null, anchor: null },
  ],
  active_idx: 0,
  timer_seconds: 60,
};

const hydeStub = {
  hyde_hypotheticals: ["ideal cevap"],
  rerank_top: [
    { paper_id: "p1", chunk_idx: 0, sentence: "kanıt cümle", score: 0.8 },
  ],
  missing_concepts: ["X"],
  fanout_used: true,
  rerank_used: true,
};

const scoreStub = (idx: number) => ({
  session_id: SESSION_ID,
  question_idx: idx,
  evidence_coverage: 0.7,
  depth_score: 0.6,
  clarity_score: 0.8,
  weighted_score: 0.7,
  jury_reaction: "satisfied" as const,
  missing_concepts: [],
  follow_up_triggered: false,
});

const consistencyStub = {
  session_id: SESSION_ID,
  conflicts: [],
  summary: "Tüm cevaplar tutarlı.",
};

const decisionStub = {
  session_id: SESSION_ID,
  prediction: "minor_revision" as const,
  confidence: 0.72,
  score_summary: { mean: 0.7 },
  advice: "Yöntem bölümünü genişletin.",
};

function defaultRoute(path: string): Promise<unknown> {
  if (path.startsWith("/api/workshop/defense/session")) return Promise.resolve(sessionStub);
  if (path.startsWith("/api/workshop/manuscript")) return Promise.resolve(manuscriptStub(longManuscript));
  if (path.startsWith("/api/workshop/defense/jury-question")) return Promise.resolve(juryQuestionStub);
  if (path.startsWith("/api/workshop/defense/hyde-fanout-rerank")) return Promise.resolve(hydeStub);
  if (path.startsWith("/api/workshop/defense/consistency-check")) return Promise.resolve(consistencyStub);
  if (path.startsWith("/api/workshop/defense/jury-decision-band")) return Promise.resolve(decisionStub);
  return Promise.reject(new Error(`unmocked path: ${path}`));
}

beforeEach(() => {
  apiFetchMock.mockReset();
});

afterEach(() => cleanup());

describe("JurySimulationPage", () => {
  it("renders idle state with Simülasyonu Başlat button", () => {
    render(<JurySimulationPage />);
    expect(screen.getByRole("button", { name: /Simülasyonu Başlat/i })).toBeTruthy();
    expect(screen.getByText(/5 jüri persona/i)).toBeTruthy();
  });

  it("blocks start when manuscript is shorter than 100 chars", async () => {
    apiFetchMock.mockImplementation((path: string) => {
      if (path.startsWith("/api/workshop/manuscript")) {
        return Promise.resolve(manuscriptStub("kısa"));
      }
      return defaultRoute(path);
    });
    render(<JurySimulationPage />);
    fireEvent.click(screen.getByRole("button", { name: /Simülasyonu Başlat/i }));
    await waitFor(() => {
      expect(screen.getByText(/en az 100 karakter/i)).toBeTruthy();
    });
    expect(apiFetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/workshop/defense/session"),
      expect.any(Object),
    );
  });

  it("runs full happy path: question → answer → verdict", async () => {
    let scoreCalls = 0;
    apiFetchMock.mockImplementation((path: string) => {
      if (path.startsWith("/api/workshop/defense/answer-score")) {
        const r = scoreStub(scoreCalls);
        scoreCalls += 1;
        return Promise.resolve(r);
      }
      return defaultRoute(path);
    });

    render(<JurySimulationPage />);
    fireEvent.click(screen.getByRole("button", { name: /Simülasyonu Başlat/i }));

    // First question rendered
    await waitFor(() => {
      expect(screen.getByText(/Tezin özü nedir\?/)).toBeTruthy();
    });

    // Answer Q1
    fireEvent.change(screen.getByPlaceholderText(/Yanıtınızı/i), {
      target: { value: "Yanıt 1" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^Yanıtla$/ }));

    // Q2 rendered
    await waitFor(() => {
      expect(screen.getByText(/Karşı argüman nedir\?/)).toBeTruthy();
    });
    fireEvent.change(screen.getByPlaceholderText(/Yanıtınızı/i), {
      target: { value: "Yanıt 2" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^Yanıtla$/ }));

    // Final verdict rendered
    await waitFor(() => {
      expect(screen.getByText(/Küçük Düzeltme/)).toBeTruthy();
      expect(screen.getByText(/Yöntem bölümünü genişletin/)).toBeTruthy();
      expect(screen.getByText(/Çelişki bulunamadı/)).toBeTruthy();
    });

    // Verify all 5 jury endpoints were called
    const paths = apiFetchMock.mock.calls.map((c) => c[0] as string);
    expect(paths.some((p) => p.startsWith("/api/workshop/defense/jury-question"))).toBe(true);
    expect(paths.some((p) => p.startsWith("/api/workshop/defense/hyde-fanout-rerank"))).toBe(true);
    expect(paths.some((p) => p.startsWith("/api/workshop/defense/answer-score"))).toBe(true);
    expect(paths.some((p) => p.startsWith("/api/workshop/defense/consistency-check"))).toBe(true);
    expect(paths.some((p) => p.startsWith("/api/workshop/defense/jury-decision-band"))).toBe(true);
  });

  it("shows error banner when jury-question API fails", async () => {
    apiFetchMock.mockImplementation((path: string) => {
      if (path.startsWith("/api/workshop/defense/jury-question")) {
        return Promise.reject(new Error("API 503: llm_unavailable"));
      }
      return defaultRoute(path);
    });

    render(<JurySimulationPage />);
    fireEvent.click(screen.getByRole("button", { name: /Simülasyonu Başlat/i }));

    await waitFor(() => {
      expect(screen.getByText(/Hata/)).toBeTruthy();
      expect(screen.getByRole("button", { name: /Tekrar Dene/i })).toBeTruthy();
    });
  });

  // satisfy unused import guard
  it("re-renders after act with no errors", () => {
    act(() => {
      render(<JurySimulationPage />);
    });
    expect(screen.getByRole("button", { name: /Simülasyonu Başlat/i })).toBeTruthy();
  });
});
