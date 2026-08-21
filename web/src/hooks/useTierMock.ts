// kaynak: Page_Design/Sayfa_Plani_v1/C_vitrin/q1.md §TIER DAVRANIŞI + 0012 migration 3-tier canon
// V1-S2 mock — useSyncExternalStore ile localStorage subscribe (SSR-safe).
// TODO(V1-S5): replace with useSession() from supabase auth

"use client";

import { useSyncExternalStore } from "react";

export type UserTier = "ogrenci" | "arastirmaci" | "profesyonel";
export type TierMode = "anon" | UserTier;

const STORAGE_KEY = "arbitra_tier_mock";
const VALID_TIERS: readonly TierMode[] = [
  "anon",
  "ogrenci",
  "arastirmaci",
  "profesyonel",
] as const;

function isValidTier(value: string | null): value is TierMode {
  return value !== null && (VALID_TIERS as readonly string[]).includes(value);
}

function subscribe(callback: () => void): () => void {
  if (typeof window === "undefined") return () => {};
  window.addEventListener("storage", callback);
  return () => window.removeEventListener("storage", callback);
}

function getSnapshot(): TierMode {
  if (typeof window === "undefined") return "anon";
  const stored = window.localStorage.getItem(STORAGE_KEY);
  return isValidTier(stored) ? stored : "anon";
}

function getServerSnapshot(): TierMode {
  return "anon";
}

export function useTierMock(): {
  tier: TierMode;
  isAuthenticated: boolean;
} {
  const tier = useSyncExternalStore(
    subscribe,
    getSnapshot,
    getServerSnapshot,
  );
  return { tier, isAuthenticated: tier !== "anon" };
}
