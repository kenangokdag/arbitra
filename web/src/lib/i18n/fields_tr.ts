// F5-PRE — onboarding dropdown TR görüntü adları (PROMPT #4-PRE brief §1.B).
// Brain: K-011 (DB EN-only), K-012 (UI TR statik dictionary; post-MVP runtime Gemini).
//
// Key kanunu: PROMPT #1 seed_dim_field.derive_field_id =
//   re.sub(r'[^a-z0-9]+', '_', name_en.lower()).strip('_')
// Key'ler dim_field DB satırları ile birebir uyumlu (psql kanıt).
//
// Kapsam: 26 OpenAlex level-1 alanı (Arbitra warehouse N04D extract).
// Brief sample dictionary'sinden 2 sapma DB'ye göre düzeltildi:
//   • biochemistry_genetics_molecular_biology  → biochemistry_genetics_and_molecular_biology
//   • multidisciplinary (DB'de yok) → kaldırıldı; veterinary (DB'de var) → eklendi.
// (§1.B kanunu: DB ↔ dictionary key birebir, halüsinasyon yasak)

export const FIELDS_TR: Record<string, string> = {
  agricultural_and_biological_sciences:        "Tarım ve Biyolojik Bilimler",
  arts_and_humanities:                         "Sanat ve Beşeri Bilimler",
  biochemistry_genetics_and_molecular_biology: "Biyokimya, Genetik ve Moleküler Biyoloji",
  business_management_and_accounting:          "İşletme, Yönetim ve Muhasebe",
  chemical_engineering:                        "Kimya Mühendisliği",
  chemistry:                                   "Kimya",
  computer_science:                            "Bilgisayar Bilimleri",
  decision_sciences:                           "Karar Bilimleri",
  dentistry:                                   "Diş Hekimliği",
  earth_and_planetary_sciences:                "Yer ve Gezegen Bilimleri",
  economics_econometrics_and_finance:          "İktisat, Ekonometri ve Finans",
  energy:                                      "Enerji",
  engineering:                                 "Mühendislik",
  environmental_science:                       "Çevre Bilimi",
  health_professions:                          "Sağlık Meslekleri",
  immunology_and_microbiology:                 "İmmünoloji ve Mikrobiyoloji",
  materials_science:                           "Malzeme Bilimi",
  mathematics:                                 "Matematik",
  medicine:                                    "Tıp",
  neuroscience:                                "Sinirbilim",
  nursing:                                     "Hemşirelik",
  pharmacology_toxicology_and_pharmaceutics:   "Farmakoloji, Toksikoloji ve Eczacılık",
  physics_and_astronomy:                       "Fizik ve Astronomi",
  psychology:                                  "Psikoloji",
  social_sciences:                             "Sosyal Bilimler",
  veterinary:                                  "Veterinerlik",
};

export function fieldDisplay(field_id: string, name_en_fallback: string): string {
  return FIELDS_TR[field_id] ?? name_en_fallback;
}
