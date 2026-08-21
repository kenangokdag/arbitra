/**
 * V1-S4 waitlist API client — POST /api/waitlist (anon-only, PUBLIC_PATHS).
 * kaynak: docs/plans/V1_S4_waitlist_capture.md §1 (kontrat)
 */

import { ApiError, apiFetch } from "./api";

export type WaitlistSource = "landing_hero" | "landing_pricing";

export type WaitlistRequest = {
  email: string;
  name: string;
  source: WaitlistSource;
  website?: string; // honeypot — gerçek kullanıcı boş bırakır
};

export type WaitlistResponse = {
  ok: boolean;
  queued_at: string;
};

export type WaitlistResult =
  | { kind: "success"; queued_at: string }
  | { kind: "duplicate" }
  | { kind: "error"; message: string };

export async function submitWaitlist(req: WaitlistRequest): Promise<WaitlistResult> {
  try {
    const res = await apiFetch<WaitlistResponse>("/api/waitlist", {
      method: "POST",
      body: req,
    });
    return { kind: "success", queued_at: res.queued_at };
  } catch (err) {
    if (err instanceof ApiError && err.status === 409) {
      return { kind: "duplicate" };
    }
    if (err instanceof ApiError && err.status === 422) {
      return { kind: "error", message: "Geçersiz e-posta adresi." };
    }
    return { kind: "error", message: "Bağlantı hatası, lütfen tekrar deneyin." };
  }
}

export { ApiError };
