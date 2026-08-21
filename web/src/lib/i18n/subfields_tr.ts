// F5-PRE — subfield TR görüntü adları stub (PROMPT #4-PRE brief §1.C).
// Brain: K-011 (DB EN-only), K-012 (UI TR statik dictionary).
//
// Neden boş: 252 subfield için TAM TR çeviri uzmanlık gerektirir
// (örn. "Hematology, Oncology and Palliative Care" gibi birleşikler).
// Halüsinasyon yasağı (BRAIN feedback_halüsinasyon_yasakları) → MVP'de boş bırakılır.
// Fallback: kullanıcı name_en görür (akademisyen pilot, kabul edilebilir).
//
// Post-MVP plan: Omer + uzman 252 satır TR çeviri çalışması; runtime Gemini opsiyonel.

export const SUBFIELDS_TR: Record<string, string> = {
  // intentionally empty — see file header
};

export function subfieldDisplay(subfield_id: string, name_en_fallback: string): string {
  return SUBFIELDS_TR[subfield_id] ?? name_en_fallback;
}
