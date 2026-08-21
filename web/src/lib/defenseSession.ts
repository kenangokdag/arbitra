// F13-S2.3 — defense session id'sini sayfalar arasi tasi.
// DefenseFormatPage (defense-1) yazar; IndividualFeedbackPage (defense-3)
// + JurySimulationPage (defense-5) okur. Backend tarafinda GET endpoint
// yok; F1'de eklenirse bu helper kaldirilir.

const KEY_PREFIX = "defense_session:";

export function getDefenseSessionId(projectId: string): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(`${KEY_PREFIX}${projectId}`);
  } catch {
    return null;
  }
}

export function setDefenseSessionId(projectId: string, sessionId: string): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(`${KEY_PREFIX}${projectId}`, sessionId);
  } catch {
    // sessionStorage / privacy mode — sessiz gec
  }
}

export function clearDefenseSessionId(projectId: string): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(`${KEY_PREFIX}${projectId}`);
  } catch {
    // sessiz gec
  }
}
