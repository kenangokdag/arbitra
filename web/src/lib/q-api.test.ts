// kaynak: docs/plans/V1_S8_q_wire.md §5
// V1-S8-01 adapter unit: authorsLabel + abstract truncate + snake_case body kontratı.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { fetchQ } from "./q-api";

const ENV_KEY = "NEXT_PUBLIC_API_URL";

beforeEach(() => {
  // jsdom localStorage temiz (auth getToken null döner)
  globalThis.localStorage?.clear?.();
});

afterEach(() => {
  vi.restoreAllMocks();
});

function backendPaper(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    openalex_id: "W1",
    doi: null,
    title: "Sample paper",
    abstract: null,
    year: 2024,
    venue: "Sample Venue",
    authors: [],
    cited_by_count: 0,
    mini_summary: null,
    ...overrides,
  };
}

function mockFetchOk(body: Record<string, unknown>) {
  return vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(body), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

describe("fetchQ adapter", () => {
  it("authors ≤3 → '; '-join", async () => {
    mockFetchOk({
      papers: [backendPaper({ authors: ["A", "B", "C"] })],
      quota_remaining: 4,
      quota_reset: "2026-05-10T00:00:00+00:00",
    });
    const res = await fetchQ({ query: "x" });
    expect(res.papers[0]!.authorsLabel).toBe("A; B; C");
  });

  it("authors 4+ → 'X et al.'", async () => {
    mockFetchOk({
      papers: [backendPaper({ authors: ["Vaswani, A.", "B", "C", "D", "E"] })],
      quota_remaining: 4,
      quota_reset: "2026-05-10T00:00:00+00:00",
    });
    const res = await fetchQ({ query: "x" });
    expect(res.papers[0]!.authorsLabel).toBe("Vaswani, A. et al.");
  });

  it("authors boş → '—'", async () => {
    mockFetchOk({
      papers: [backendPaper({ authors: [] })],
      quota_remaining: 4,
      quota_reset: "2026-05-10T00:00:00+00:00",
    });
    const res = await fetchQ({ query: "x" });
    expect(res.papers[0]!.authorsLabel).toBe("—");
  });

  it("abstract>220 char → truncate '…'", async () => {
    const longAbstract = "a".repeat(300);
    mockFetchOk({
      papers: [backendPaper({ abstract: longAbstract })],
      quota_remaining: 4,
      quota_reset: "2026-05-10T00:00:00+00:00",
    });
    const res = await fetchQ({ query: "x" });
    expect(res.papers[0]!.abstract?.endsWith("…")).toBe(true);
    expect(res.papers[0]!.abstract?.length).toBeLessThanOrEqual(220);
  });

  it("translation passthrough — snake→camel + null geçer (KD-V1-S11-04)", async () => {
    mockFetchOk({
      papers: [],
      translation: {
        original: "transformer dikkat",
        detected_lang: "tr",
        english_query: "transformer attention",
      },
      quota_remaining: 4,
      quota_reset: "2026-05-10T00:00:00+00:00",
    });
    const res = await fetchQ({ query: "transformer dikkat" });
    expect(res.translation).toEqual({
      original: "transformer dikkat",
      detectedLang: "tr",
      englishQuery: "transformer attention",
    });
  });

  it("translation null (translate skip/fail) → null geçer", async () => {
    mockFetchOk({
      papers: [],
      translation: null,
      quota_remaining: 4,
      quota_reset: "2026-05-10T00:00:00+00:00",
    });
    const res = await fetchQ({ query: "x" });
    expect(res.translation).toBeNull();
  });

  it("translation field tamamen yok (eski backend) → null", async () => {
    mockFetchOk({
      papers: [],
      quota_remaining: 4,
      quota_reset: "2026-05-10T00:00:00+00:00",
    });
    const res = await fetchQ({ query: "x" });
    expect(res.translation).toBeNull();
  });

  it("body snake_case (year_from/year_to) — backend Pydantic forbid uyumlu", async () => {
    const spy = mockFetchOk({
      papers: [],
      quota_remaining: 4,
      quota_reset: "2026-05-10T00:00:00+00:00",
    });
    await fetchQ({ query: "x", yearFrom: 2020, yearTo: 2024 });
    const call = spy.mock.calls[0]!;
    const body = JSON.parse((call[1] as RequestInit).body as string);
    expect(body).toEqual({
      query: "x",
      lang: "tr",
      year_from: 2020,
      year_to: 2024,
    });
    expect(body.yearFrom).toBeUndefined();
    expect(body.yearTo).toBeUndefined();
  });
});

// ENV_KEY referans (lint için kullanılmadığı durumlarda ölü importu önler)
void ENV_KEY;
