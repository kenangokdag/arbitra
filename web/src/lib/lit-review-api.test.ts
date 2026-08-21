// kaynak: docs/plans/V1_S10_vitrin_tek_sayfa.md §7
// V1-S10-03 adapter unit: snake_case body + snake→camel response (current_studies → currentStudies).

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { generateLitReview } from "./lit-review-api";

beforeEach(() => {
  globalThis.localStorage?.clear?.();
});

afterEach(() => {
  vi.restoreAllMocks();
});

function backendReview(
  overrides: Partial<Record<string, unknown>> = {},
): Record<string, unknown> {
  return {
    content: "Mock literatür inceleme metni [01].",
    references: [{ index: 1, citation: "Smith, J. (2023). Mock Paper. Mock Journal." }],
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

describe("generateLitReview adapter", () => {
  it("body snake_case (paper_ids, lang) — backend Pydantic forbid uyumlu", async () => {
    const spy = mockFetchOk({
      review: backendReview(),
      quota_remaining: 9,
      quota_reset: "2026-05-10T00:00:00+00:00",
    });
    await generateLitReview({ paperIds: ["W1", "W2"], lang: "tr" });
    const call = spy.mock.calls[0]!;
    const body = JSON.parse((call[1] as RequestInit).body as string);
    expect(body).toEqual({ paper_ids: ["W1", "W2"], lang: "tr" });
    expect(body.paperIds).toBeUndefined();
  });

  it("lang default = 'tr' (omit edildiğinde)", async () => {
    const spy = mockFetchOk({
      review: backendReview(),
      quota_remaining: 9,
      quota_reset: "2026-05-10T00:00:00+00:00",
    });
    await generateLitReview({ paperIds: ["W1"] });
    const body = JSON.parse((spy.mock.calls[0]![1] as RequestInit).body as string);
    expect(body.lang).toBe("tr");
  });

  it("response: content tek blok + references passthrough", async () => {
    mockFetchOk({
      review: backendReview({
        content: "Mock sentez [01][02]. Karşılaştırma cümlesi [02].",
        references: [
          { index: 1, citation: "Ref A" },
          { index: 2, citation: "Ref B" },
        ],
      }),
      quota_remaining: 4,
      quota_reset: "2026-05-10T00:00:00+00:00",
    });
    const res = await generateLitReview({ paperIds: ["W1", "W2"] });
    expect(res.review.content).toBe(
      "Mock sentez [01][02]. Karşılaştırma cümlesi [02].",
    );
    expect(res.quotaRemaining).toBe(4);
    expect(res.review.references).toEqual([
      { index: 1, citation: "Ref A" },
      { index: 2, citation: "Ref B" },
    ]);
  });

  it("eski 4-bölüm alanları (title/introduction/...) artık API yüzeyinde YOK", async () => {
    mockFetchOk({
      review: backendReview({ content: "Tek blok metin [01]." }),
      quota_remaining: 0,
      quota_reset: "2026-05-10T00:00:00+00:00",
    });
    const res = await generateLitReview({ paperIds: ["W1"] });
    const review = res.review as unknown as Record<string, unknown>;
    expect(review.title).toBeUndefined();
    expect(review.introduction).toBeUndefined();
    expect(review.currentStudies).toBeUndefined();
    expect(review.discussion).toBeUndefined();
    expect(review.conclusion).toBeUndefined();
    expect(res.review.content).toBe("Tek blok metin [01].");
  });
});
