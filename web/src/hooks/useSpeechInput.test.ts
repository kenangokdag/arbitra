// kaynak: docs/plans/V1_S12_sesli_arama_ve_dinlet.md §6
// V1-S12-02 hook unit: SSR-safe support tespiti + onResult callback + cleanup.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";

import { useSpeechInput } from "./useSpeechInput";

type Listener<E = unknown> = ((e: E) => void) | null;

class FakeSpeechRecognition {
  lang = "";
  continuous = false;
  interimResults = false;
  onresult: Listener = null;
  onerror: Listener = null;
  onend: Listener = null;
  start = vi.fn();
  stop = vi.fn();

  fireResult(transcript: string, isFinal = true): void {
    this.onresult?.({
      results: [
        Object.assign([{ transcript }], {
          isFinal,
          length: 1,
          item: () => ({ 0: { transcript }, isFinal }),
        }),
      ],
    });
  }
}

let lastInstance: FakeSpeechRecognition | null = null;

beforeEach(() => {
  lastInstance = null;
  (window as unknown as { SpeechRecognition?: unknown }).SpeechRecognition =
    function () {
      lastInstance = new FakeSpeechRecognition();
      return lastInstance;
    };
});

afterEach(() => {
  delete (window as unknown as { SpeechRecognition?: unknown })
    .SpeechRecognition;
  delete (window as unknown as { webkitSpeechRecognition?: unknown })
    .webkitSpeechRecognition;
});

describe("useSpeechInput", () => {
  it("isSupported true (SpeechRecognition var)", async () => {
    const onResult = vi.fn();
    const { result } = renderHook(() => useSpeechInput({ onResult }));
    // useEffect Mount sonrası setState
    await act(async () => {});
    expect(result.current.isSupported).toBe(true);
  });

  it("isSupported false (SpeechRecognition yok)", async () => {
    delete (window as unknown as { SpeechRecognition?: unknown })
      .SpeechRecognition;
    const onResult = vi.fn();
    const { result } = renderHook(() => useSpeechInput({ onResult }));
    await act(async () => {});
    expect(result.current.isSupported).toBe(false);
  });

  it("start → instance oluşur, lang TR set edilir, recognition.start() çağrılır", async () => {
    const onResult = vi.fn();
    const { result } = renderHook(() =>
      useSpeechInput({ lang: "tr-TR", onResult }),
    );
    await act(async () => {});
    act(() => {
      result.current.start();
    });
    expect(lastInstance).not.toBeNull();
    expect(lastInstance!.lang).toBe("tr-TR");
    expect(lastInstance!.continuous).toBe(false);
    expect(lastInstance!.start).toHaveBeenCalledOnce();
    expect(result.current.isListening).toBe(true);
  });

  it("onresult final → onResult callback transcript ile çağrılır", async () => {
    const onResult = vi.fn();
    const { result } = renderHook(() => useSpeechInput({ onResult }));
    await act(async () => {});
    act(() => {
      result.current.start();
    });
    act(() => {
      lastInstance!.fireResult("transformer dikkat mekanizması");
    });
    expect(onResult).toHaveBeenCalledWith("transformer dikkat mekanizması");
  });

  it("onerror → onError callback + isListening=false", async () => {
    const onResult = vi.fn();
    const onError = vi.fn();
    const { result } = renderHook(() => useSpeechInput({ onResult, onError }));
    await act(async () => {});
    act(() => {
      result.current.start();
    });
    act(() => {
      lastInstance!.onerror?.({ error: "no-speech" });
    });
    expect(onError).toHaveBeenCalledWith("no-speech");
    expect(result.current.isListening).toBe(false);
  });

  it("onend → isListening=false (recognition normal bitti)", async () => {
    const onResult = vi.fn();
    const { result } = renderHook(() => useSpeechInput({ onResult }));
    await act(async () => {});
    act(() => {
      result.current.start();
    });
    act(() => {
      lastInstance!.onend?.(undefined);
    });
    expect(result.current.isListening).toBe(false);
  });

  it("isSupported false iken start no-op (instance oluşmaz)", async () => {
    delete (window as unknown as { SpeechRecognition?: unknown })
      .SpeechRecognition;
    const onResult = vi.fn();
    const { result } = renderHook(() => useSpeechInput({ onResult }));
    await act(async () => {});
    act(() => {
      result.current.start();
    });
    expect(lastInstance).toBeNull();
    expect(result.current.isListening).toBe(false);
  });
});
