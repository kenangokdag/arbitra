// Plan: docs/plans/RAPOR_DOCX_EXPORT_2026-08-16.md §4.3.
// fetchReviewReportDocx — tts-api.test.ts'deki desenle AYNI (native fetch + blob).

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "./api";
import { fetchReviewReportDocx } from "./review-api";

const DOCX_MIME =
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document";

beforeEach(() => {
  globalThis.localStorage?.clear?.();
});

afterEach(() => {
  vi.restoreAllMocks();
});

function mockDocxOk() {
  const blob = new Blob([new Uint8Array([0x50, 0x4b, 3, 4])], { type: DOCX_MIME });
  return vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(blob, {
      status: 200,
      headers: { "Content-Type": DOCX_MIME },
    }),
  );
}

describe("fetchReviewReportDocx", () => {
  it("doğru URL'e GET atar (job_id path'te)", async () => {
    const spy = mockDocxOk();
    await fetchReviewReportDocx("job-123");
    const call = spy.mock.calls[0]!;
    const url = call[0] as string;
    expect(url).toContain("/api/review/job-123/export.docx");
  });

  it("Authorization Bearer header eklenir", async () => {
    const spy = mockDocxOk();
    await fetchReviewReportDocx("job-123");
    const init = spy.mock.calls[0]![1] as RequestInit;
    const headers = init.headers as Record<string, string>;
    expect(headers.Authorization).toMatch(/^Bearer /);
  });

  it("response → docx Blob döner", async () => {
    mockDocxOk();
    const blob = await fetchReviewReportDocx("job-123");
    expect(blob.type).toBe(DOCX_MIME);
    expect(blob.size).toBeGreaterThan(0);
  });

  it("4xx response → ApiError fırlatır", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "report_not_ready" }), {
        status: 404,
        headers: { "Content-Type": "application/json" },
      }),
    );
    await expect(fetchReviewReportDocx("job-404")).rejects.toThrow(ApiError);
  });
});
