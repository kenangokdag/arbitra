// REVIEW_ONBOARDING_TURU_2026-08-17 — "ilk girişte, sadece bir kez" turu için
// tercih saklama. defenseSession.ts'nin BİREBİR aynı deseni: SSR-safe +
// try/catch + sessiz-geç (localStorage yoksa/privacy mode'da çökmez).
// Backend/migration GEREKMİYOR (plan §1 — hiçbir kullanıcı-tercih kolonu yok,
// cihazlar-arası senkronizasyon istenmedi).

const KEY = "arbitra:review-onboarding-seen";

export function hasSeenReviewTour(): boolean {
  if (typeof window === "undefined") return true; // SSR'da göstermeyi tetikleme
  try {
    return window.localStorage.getItem(KEY) === "1";
  } catch {
    return true; // localStorage erişilemezse turu ISRARLA göstermeyiz — sessiz geç
  }
}

export function markReviewTourSeen(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(KEY, "1");
  } catch {
    // localStorage / privacy mode — sessiz geç
  }
}
