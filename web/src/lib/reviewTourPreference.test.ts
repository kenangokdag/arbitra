// REVIEW_ONBOARDING_TURU_2026-08-17 — defenseSession.ts'nin testleriyle AYNI
// desende: SSR-safe + localStorage hata durumunda sessiz-geç.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { hasSeenReviewTour, markReviewTourSeen } from "./reviewTourPreference";

beforeEach(() => {
  window.localStorage.clear();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("reviewTourPreference", () => {
  it("hiç işaretlenmemişse hasSeenReviewTour false döner", () => {
    expect(hasSeenReviewTour()).toBe(false);
  });

  it("markReviewTourSeen sonrası hasSeenReviewTour true döner", () => {
    markReviewTourSeen();
    expect(hasSeenReviewTour()).toBe(true);
  });

  it("localStorage erişilemezse (privacy mode) çökmez, dürüstçe 'görüldü' varsayar", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("SecurityError");
    });
    expect(hasSeenReviewTour()).toBe(true);
  });

  it("markReviewTourSeen localStorage hatasında sessizce geçer, çökmez", () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("QuotaExceededError");
    });
    expect(() => markReviewTourSeen()).not.toThrow();
  });
});
