// kaynak: docs/plans/V1_S12_sesli_arama_ve_dinlet.md §6
// V1-S12-03 adapter unit: snake body + audio/mpeg blob + 4xx → ApiError.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, fetchTTSReview } from "./tts-api";

beforeEach(() => {
  globalThis.localStorage?.clear?.();
});

afterEach(() => {
  vi.restoreAllMocks();
});

function mockAudioOk() {
  const blob = new Blob([new Uint8Array([0, 1, 2])], { type: "audio/mpeg" });
  return vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(blob, {
      status: 200,
      headers: { "Content-Type": "audio/mpeg" },
    }),
  );
}

describe("fetchTTSReview", () => {
  it("body snake_case (content + lang) — backend Pydantic forbid uyumlu", async () => {
    const spy = mockAudioOk();
    await fetchTTSReview({ content: "uzun bir özet metni 10+ char", lang: "tr" });
    const call = spy.mock.calls[0]!;
    const url = call[0] as string;
    const init = call[1] as RequestInit;
    expect(url).toContain("/api/tts/literature-review");
    expect(init.method).toBe("POST");
    const body = JSON.parse(init.body as string);
    expect(body).toEqual({
      content: "uzun bir özet metni 10+ char",
      lang: "tr",
    });
  });

  it("response → audio/mpeg Blob döner", async () => {
    mockAudioOk();
    const blob = await fetchTTSReview({ content: "yeterince uzun metin var" });
    // jsdom Blob multi-realm farkı → instanceof yerine type+size kontrolü
    expect(blob.type).toBe("audio/mpeg");
    expect(blob.size).toBeGreaterThan(0);
    expect(typeof blob.arrayBuffer).toBe("function");
  });

  it("default lang='tr' (request'te verilmezse)", async () => {
    const spy = mockAudioOk();
    await fetchTTSReview({ content: "yeterince uzun metin var burada" });
    const init = spy.mock.calls[0]![1] as RequestInit;
    const body = JSON.parse(init.body as string);
    expect(body.lang).toBe("tr");
  });

  it("4xx response → ApiError fırlatır (detail JSON)", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: { error: "quota_exceeded" } }), {
        status: 429,
        headers: { "Content-Type": "application/json" },
      }),
    );
    await expect(
      fetchTTSReview({ content: "yeterince uzun metin var burada" }),
    ).rejects.toThrow(ApiError);
  });

  it("Authorization Bearer header eklenir", async () => {
    const spy = mockAudioOk();
    await fetchTTSReview({ content: "yeterince uzun metin var burada" });
    const init = spy.mock.calls[0]![1] as RequestInit;
    const headers = init.headers as Record<string, string>;
    expect(headers.Authorization).toMatch(/^Bearer /);
    expect(headers.Accept).toBe("audio/mpeg");
  });
});
