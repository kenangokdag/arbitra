// kaynak: docs/plans/V1_S8_q_wire.md §5
// V1-S8-01 hook unit: TanStack mock — disabled / success / kısa query / fetch error / authors 4+.

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type ReactNode } from "react";

import { useQ } from "./useQ";
import * as api from "@/lib/q-api";

function makeWrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("useQ", () => {
  it("enabled=false → fetchQ ÇAĞRILMAZ", async () => {
    const spy = vi.spyOn(api, "fetchQ");
    const { result } = renderHook(
      () => useQ({ query: "transformer", enabled: false }),
      { wrapper: makeWrapper() },
    );
    await new Promise((r) => setTimeout(r, 50));
    expect(spy).not.toHaveBeenCalled();
    expect(result.current.data).toBeUndefined();
    expect(result.current.isPending).toBe(true);
  });

  it("enabled=true + valid query → fetchQ çağrılır, data döner", async () => {
    const fakeResponse: api.QResponseApi = {
      papers: [
        {
          id: "W123",
          doi: "10.1/foo",
          title: "Attention Is All You Need",
          abstract: "Transformer architecture…",
          year: 2017,
          venue: "NeurIPS",
          authors: ["Vaswani, A.", "Shazeer, N."],
          authorsLabel: "Vaswani, A.; Shazeer, N.",
          citedByCount: 50000,
        },
      ],
      translation: null,
      quotaRemaining: 4,
      quotaReset: "2026-05-10T00:00:00+00:00",
    };
    vi.spyOn(api, "fetchQ").mockResolvedValue(fakeResponse);

    const { result } = renderHook(
      () => useQ({ query: "transformer attention", enabled: true }),
      { wrapper: makeWrapper() },
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(fakeResponse);
  });

  // V1-S11-03: translation field response'ta expose edilir
  it("translation field response'ta expose edilir (KD-V1-S11-02)", async () => {
    const fakeResponse: api.QResponseApi = {
      papers: [],
      translation: {
        original: "transformer dikkat",
        detectedLang: "tr",
        englishQuery: "transformer attention",
      },
      quotaRemaining: 4,
      quotaReset: "2026-05-10T00:00:00+00:00",
    };
    vi.spyOn(api, "fetchQ").mockResolvedValue(fakeResponse);
    const { result } = renderHook(
      () => useQ({ query: "transformer dikkat", enabled: true }),
      { wrapper: makeWrapper() },
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.translation).toEqual({
      original: "transformer dikkat",
      detectedLang: "tr",
      englishQuery: "transformer attention",
    });
  });

  it("query<2 char → enabled effective=false", async () => {
    const spy = vi.spyOn(api, "fetchQ");
    renderHook(() => useQ({ query: "x", enabled: true }), {
      wrapper: makeWrapper(),
    });
    await new Promise((r) => setTimeout(r, 50));
    expect(spy).not.toHaveBeenCalled();
  });

  it("fetch error → isError + error.message expose", async () => {
    vi.spyOn(api, "fetchQ").mockRejectedValue(new Error("openalex down"));
    const { result } = renderHook(
      () => useQ({ query: "transformer", enabled: true }),
      { wrapper: makeWrapper() },
    );
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toBe("openalex down");
  });

  // V1-S10-06: yearFrom/yearTo backend filter
  it("yearFrom/yearTo verilirse fetchQ'ya iletilir", async () => {
    const fakeResponse: api.QResponseApi = {
      papers: [],
      translation: null,
      quotaRemaining: 4,
      quotaReset: "2026-05-10T00:00:00+00:00",
    };
    const spy = vi
      .spyOn(api, "fetchQ")
      .mockResolvedValue(fakeResponse);

    const { result } = renderHook(
      () =>
        useQ({
          query: "transformer",
          enabled: true,
          yearFrom: 2018,
          yearTo: 2024,
        }),
      { wrapper: makeWrapper() },
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({
        query: "transformer",
        lang: "tr",
        yearFrom: 2018,
        yearTo: 2024,
      }),
      expect.anything(),
    );
  });
});
