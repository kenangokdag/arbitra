/**
 * V1-S12-03 TTS API client — sesli dinlet (ElevenLabs proxy via backend).
 * kaynak: docs/plans/V1_S12_sesli_arama_ve_dinlet.md §4
 *
 * Backend `/api/tts/literature-review` audio/mpeg stream döner.
 * apiFetch JSON-only → burada native fetch + blob().
 */

import { getToken } from "./auth";
import { ApiError } from "./api";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type TTSLang = "tr"; // V1: TR-only; EN/ID V1.5

export type TTSReviewRequest = {
  content: string;
  lang?: TTSLang;
};

export async function fetchTTSReview(
  req: TTSReviewRequest,
  signal?: AbortSignal,
): Promise<Blob> {
  const body = JSON.stringify({
    content: req.content,
    lang: req.lang ?? "tr",
  });

  const res = await fetch(`${API_URL}/api/tts/literature-review`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "audio/mpeg",
      Authorization: `Bearer ${getToken()}`,
    },
    body,
    signal,
  });

  if (!res.ok) {
    let detail: unknown = undefined;
    try {
      detail = await res.json();
    } catch {
      // ignore — body audio değildi, hata da JSON değil
    }
    throw new ApiError(res.status, detail, `TTS API ${res.status}`);
  }

  return res.blob();
}

export { ApiError };
