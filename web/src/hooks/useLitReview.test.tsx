// kaynak: docs/plans/V1_S10_vitrin_tek_sayfa.md §7
// V1-S10-03 hook unit: useMutation idle / mutate→success / error.

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type ReactNode } from "react";

import { useLitReview } from "./useLitReview";
import * as api from "@/lib/lit-review-api";

function makeWrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("useLitReview", () => {
  it("idle başlar — mutate çağrılmadıkça generateLitReview tetiklenmez", async () => {
    const spy = vi.spyOn(api, "generateLitReview");
    const { result } = renderHook(() => useLitReview(), {
      wrapper: makeWrapper(),
    });
    await new Promise((r) => setTimeout(r, 30));
    expect(spy).not.toHaveBeenCalled();
    expect(result.current.isIdle).toBe(true);
    expect(result.current.data).toBeUndefined();
  });

  it("mutate({paperIds}) → success state + data döner", async () => {
    const fakeResponse: api.LitReviewResponseApi = {
      review: {
        content: "Mock literatür inceleme metni [01][02][03].",
        references: [{ index: 1, citation: "Mock cite" }],
      },
      quotaRemaining: 9,
      quotaReset: "2026-05-10T00:00:00+00:00",
    };
    const spy = vi
      .spyOn(api, "generateLitReview")
      .mockResolvedValue(fakeResponse);

    const { result } = renderHook(() => useLitReview(), {
      wrapper: makeWrapper(),
    });
    act(() => {
      result.current.mutate({ paperIds: ["W1", "W2", "W3"], lang: "tr" });
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    // N-14: ikinci argüman AbortSignal — hook her mutate'te yeni controller üretir.
    expect(spy).toHaveBeenCalledWith(
      { paperIds: ["W1", "W2", "W3"], lang: "tr" },
      expect.any(AbortSignal),
    );
    expect(result.current.data).toEqual(fakeResponse);
  });

  it("mutate hata atarsa → isError + error.message expose", async () => {
    vi.spyOn(api, "generateLitReview").mockRejectedValue(
      new Error("API 502: empty_llm_output"),
    );
    const { result } = renderHook(() => useLitReview(), {
      wrapper: makeWrapper(),
    });
    act(() => {
      result.current.mutate({ paperIds: ["W1"] });
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toBe("API 502: empty_llm_output");
  });

  it("reset() → idle state'e döner", async () => {
    vi.spyOn(api, "generateLitReview").mockResolvedValue({
      review: {
        content: "Mock content [01].",
        references: [{ index: 1, citation: "R" }],
      },
      quotaRemaining: 1,
      quotaReset: "2026-05-10T00:00:00+00:00",
    });

    const { result } = renderHook(() => useLitReview(), {
      wrapper: makeWrapper(),
    });
    act(() => {
      result.current.mutate({ paperIds: ["W1"] });
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    act(() => {
      result.current.reset();
    });
    await waitFor(() => expect(result.current.isIdle).toBe(true));
    expect(result.current.data).toBeUndefined();
  });

  // N-14: AbortController kullanıcı iptaline cevap verir.
  it("abort() → in-flight isteği iptal eder + idle'a döner", async () => {
    let capturedSignal: AbortSignal | undefined;
    vi.spyOn(api, "generateLitReview").mockImplementation(
      (_req, signal) =>
        new Promise((_resolve, reject) => {
          capturedSignal = signal;
          signal?.addEventListener("abort", () => {
            reject(new DOMException("Aborted", "AbortError"));
          });
        }),
    );

    const { result } = renderHook(() => useLitReview(), {
      wrapper: makeWrapper(),
    });
    act(() => {
      result.current.mutate({ paperIds: ["W1"] });
    });
    await waitFor(() => expect(result.current.isPending).toBe(true));
    expect(capturedSignal?.aborted).toBe(false);

    act(() => {
      result.current.abort();
    });
    expect(capturedSignal?.aborted).toBe(true);
    await waitFor(() => expect(result.current.isIdle).toBe(true));
  });
});
