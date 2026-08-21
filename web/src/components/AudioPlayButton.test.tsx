// kaynak: docs/plans/V1_S12_sesli_arama_ve_dinlet.md §6
// V1-S12-03 component unit: ilk tık fetch + cache replay + 429 mesajı.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { AudioPlayButton } from "./AudioPlayButton";
import * as ttsApi from "@/lib/tts-api";

const sampleText = "Bu yeterince uzun bir literatür özeti metnidir.";

beforeEach(() => {
  // Blob URL stubs (jsdom desteklemez)
  globalThis.URL.createObjectURL = vi.fn(() => "blob:fake-url-1");
  globalThis.URL.revokeObjectURL = vi.fn();
  // HTMLAudioElement.play() jsdom'da yok
  Object.defineProperty(HTMLMediaElement.prototype, "play", {
    configurable: true,
    value: vi.fn().mockResolvedValue(undefined),
  });
  Object.defineProperty(HTMLMediaElement.prototype, "pause", {
    configurable: true,
    value: vi.fn(),
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("AudioPlayButton", () => {
  it("ilk tık → fetchTTSReview çağrılır, audio element render olur", async () => {
    const blob = new Blob([new Uint8Array([0, 1])], { type: "audio/mpeg" });
    const spy = vi.spyOn(ttsApi, "fetchTTSReview").mockResolvedValue(blob);
    render(<AudioPlayButton text={sampleText} lang="tr" />);

    const btn = screen.getByTestId("audio-play-button");
    await userEvent.click(btn);

    await waitFor(() => {
      expect(spy).toHaveBeenCalledWith({ content: sampleText, lang: "tr" });
    });
    await waitFor(() => {
      expect(screen.getByTestId("audio-element")).toBeInTheDocument();
    });
  });

  it("2. tık → fetchTTSReview tekrar ÇAĞRILMAZ (blob cache)", async () => {
    const blob = new Blob([new Uint8Array([0])], { type: "audio/mpeg" });
    const spy = vi.spyOn(ttsApi, "fetchTTSReview").mockResolvedValue(blob);
    render(<AudioPlayButton text={sampleText} />);
    const btn = screen.getByTestId("audio-play-button");

    await userEvent.click(btn);
    await waitFor(() =>
      expect(screen.getByTestId("audio-element")).toBeInTheDocument(),
    );
    expect(spy).toHaveBeenCalledTimes(1);

    // 2. tık: pause/play toggle — yeni fetch yok
    await userEvent.click(btn);
    expect(spy).toHaveBeenCalledTimes(1);
  });

  it("429 quota → kullanıcı dostu mesaj", async () => {
    vi.spyOn(ttsApi, "fetchTTSReview").mockRejectedValue(
      new ttsApi.ApiError(
        429,
        { detail: { error: "quota_exceeded" } },
        "API 429",
      ),
    );
    render(<AudioPlayButton text={sampleText} />);
    await userEvent.click(screen.getByTestId("audio-play-button"));

    await waitFor(() => {
      expect(screen.getByTestId("audio-error")).toHaveTextContent(
        /Günlük dinlet kotanız doldu/,
      );
    });
  });

  it("isLoading state — fetch sırasında butonun disabled olur", async () => {
    let resolve: ((b: Blob) => void) | null = null;
    vi.spyOn(ttsApi, "fetchTTSReview").mockReturnValue(
      new Promise<Blob>((r) => {
        resolve = r;
      }),
    );
    render(<AudioPlayButton text={sampleText} />);
    const btn = screen.getByTestId("audio-play-button");
    await userEvent.click(btn);
    expect(btn).toBeDisabled();
    resolve!(new Blob([new Uint8Array([0])], { type: "audio/mpeg" }));
    await waitFor(() => expect(btn).not.toBeDisabled());
  });
});
