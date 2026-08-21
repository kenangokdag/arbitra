# IS_PLANI.md — PaperMind App MVP İş Akışı (30 Gün)

> **Statü:** v0.2 (2026-04-29). F0 ✅ + Hat A ✅ tamam, F1 frontend planlama eşiğinde.
> **Mutlak kural:** R1 / DM-008 → Her faz başında Plan Manifest → Omer onayı → SONRA kod.
> **Plansız kod = STOP.**
> **Yöntem değişikliği (2026-04-29):** F1 = frontend planlama (eskiden backend skeleton'du); önce menü, sonra mutfak, sonra pişirme.

---

## 0. İKİ HAT PARALEL ÇALIŞACAK

| Hat | Kim | Statü | Bitiş |
|---|---|---|---|
| **A — Warehouse Closure** | Omer (Colab) | ✅ TAMAM (10 manifest A-evidence) | 28-29 Nis |
| **A.1 — N11 v2 + Redis curation** | Omer | ⏳ in-flight + yarın | sabah + yarın |
| **B — MVP Plan & Kod** | Claude + Omer onay | F1 frontend planlama eşiğinde | 28-35 gün |

**Çıkış kapısı:** Hat A tamam → Hat B'nin F3 backend skeleton'u 24.87M corpus + tüm fact tablo input'ları kullanabilir.

---

## 1. HAT A — Papermind_V2 Closure ✅ TAMAM

**A-evidence (10 manifest doğrulandı, sırasıyla):**

| # | Saat (28 Nis) | Adım | Çıktı | Verdict |
|---|---|---|---|---|
| A1 | 14:35 | N09e CD₅ Disruption | 24.87M × 8, CD_k unblocked | ✅ PASS 8/8 |
| A2 | 14:51 | N14b_patch_CD_k | fact_theme_year_aggregates v3→v4, **t-ESTRA 8/8 KAPANIŞ** | ✅ PASS 8/8 |
| A3 | 15:22 | N99 main warehouse audit | 7 risk taraldı, overall YELLOW (3Y+4G) | ✅ PASS |
| A4 | 15:52 | N20e_patch_suspicious_flag | fact_paper_id_card v1.1→v1.2, +`is_suspicious` (20,677 paper) | ✅ PASS 8/8 |
| A5 | 16:00 | N20f_patch_ghost_triage | dim_ghost_paper v1.1→v1.2, +`triage_priority` (75K high) | ✅ PASS 8/8 |
| A6 | 16:09 | N99b ek_risk_audit | overall RED → false-RED EK_RISK_8 (L-023, %0.041 baseline) | ✅ PASS effective |
| A7 | 16:23 | N16_patch_M1_feasibility v3 | fact_gap_matrix v1→v2, +`feasibility_class` (M1 unknown=0, L-024) | ✅ PASS 10/10 |
| A8 | 16:42 | N09c_method_field_affinity | fact_method_field_affinity 390 cell × 6 col | ✅ PASS 8/8 |
| A9 | 21:18 | N12b BGE-M3 SHARD_B | fact_paper_embedding_bge_m3_shard_b 12.43M × 1024-d (4.15h) | ✅ PASS 8/8 |
| A10 | 21:19 | N12b BGE-M3 SHARD_A | fact_paper_embedding_bge_m3_shard_a 12.43M × 1024-d (4.17h paralel); **toplam 24.87M Pinecone-ready** | ✅ PASS 8/8 |

**Önceki referans (audit trail için):**
- B42-045 v1.1 N20e PaperCard + N20f GhostCard ÇİFT KAPANIŞ (28 Nis 13:18 + 13:35)
- B42-043 N14b_patch_C_k SHARDED (27 Nis 21:20)
- B42-042 Marts cocite + bibcoup (27 Nis 18:41)
- W-23 N11 sentence_role v1 (27 Nis 20:33)

**Hat A.1 — kalan tek warehouse iş:**

| # | Adım | Statü | Bitiş |
|---|---|---|---|
| A11 | N11 v2 sentence-level persistence (Curator ALCE ön-koşul) | ⏳ in-flight chunk 7/25 (21:52) | ~05:00 sabah |
| A12 | Redis paper + theme curation (cache priming için manuel seçim) | ⏳ Omer yarın | yarınki gün |

**B42-046 ŞARTLI KABUL DECISIONS'a yazma:** Omer onayı bekliyor (Papermind_V2/DECISIONS.md, R6.2 yazılı onay olmadan EKLENMEZ).

---

## 2. HAT B — MVP 8 Faz (Claude + Omer)

### F0 — Hazırlık ✅ TAMAM (2026-04-29)

35 klasör + 12 skeleton dosya + DM-001..DM-012 + R1-R12 + METHOD.md v0.1 yazıldı.

---

### F1 — Frontend Planlama (4-5 gün, kod yok)

**Hedef:** Frontend'in ne göstereceği + nasıl yapılacağı %100 tasarım belgeleri (sayfa felsefesi + envanter + design system + UX kuralları). Tasarım MOCK YOK; sadece markdown belgeler.

**Önkoşul:** METHOD §1 mekan modeli onayı (Omer).

**Plan Manifest:** `docs/plans/F1_frontend_planlama.md` (Claude yazacak, Omer onayı gerekli)

**Sırası:**
1. **F1-METHOD-ONAY** Omer METHOD §1 onayı verir → "GO" / "STOP+düzelt"
2. **F1-PLAN** Claude `F1_frontend_planlama.md` taslağı yazar (§0..§18)
3. **F1-PLAN-ONAY** Omer plan manifest'i okur → "GO"
4. **F1-DOSYALAR** Onay sonrası:
   - `docs/frontend/ENVANTER.md` — veri + aksiyon + sayfa eşlemesi
   - `docs/frontend/sayfalar/*.md` — 14 sayfa şablonu (her biri 11 madde: felsefe + problem + ne gösterir + ne yapabilir + rakip + UX + boş/hata + mobil + erişilebilirlik + yapmayacak + backend gereksinimi)
   - `docs/frontend/design_system.md` — renk + tipografi + komponent + ikon
   - `docs/frontend/ux_kurallar.md` — i18n + erişilebilirlik + mekan ses tonu
5. **F1-§8** Plan Manifest §8 verification (her dosya tek tek kontrol)
6. **F1-COMMIT** Atomic commit + SPRINT_HISTORY güncelle

**Çıktı:** Frontend planı tam, F2'ye geçilebilir (kod yok, sadece belge).

---

### F2 — Backend Planlama (3-4 gün, kod yok)

**Hedef:** Backend'in hangi sebzeleri (data) hangi tencerelerde (servisler) işleyeceği + 5 endpoint kontrat tasarımı.

**Önkoşul:** F1 onaylı + OPEN-001 (LLM model) + OPEN-003 (12 chip) + OPEN-004 (Pipeline_Akis).

**Plan Manifest:** `docs/plans/F2_backend_planlama.md`

**Çıktı dosyaları:**
- `docs/backend/ENVANTER.md` — Drive fact tabloları + 5 endpoint × hangi tablo + hangi cache
- `docs/backend/pipeline_akis.md` — query → 5-katman → response akış detay
- `docs/backend/api_kontrat.md` — 5 endpoint × request/response schema
- `docs/backend/chip_library_spec.md` — 12 chip × hangi tablodan + hangi formül
- `docs/backend/estra_lookup.md` — w/d/t/c/s/r/m hangi tablo lookup

**Çıktı:** Backend planı tam, F3 kodu yazılabilir (kod yok, sadece belge).

---

### F3 — Backend Skeleton + Slice 1: POST /api/search (4-5 gün)

**Hedef:** Tek endpoint sonuna kadar çalışsın: query → 5-katman → top 10 paper + KararBant verisi + LVR cümleler.

**Önkoşul:** F1 + F2 onaylı.

**Plan Manifest:** `docs/plans/F3_backend_skeleton_search.md`

**Sırası:**
1. F3-PLAN, F3-ONAY
2. F3-KOD atomic commitler:
   - P001 api/main.py + api/middleware/* + Redis client + Celery app + LiteLLM adapter skeleton
   - P002 engine/core/{listener,anchor,pool_router,reranker,curator}.py boş sınıflar + LVR validator
   - P003 Listener (Qwen multi-query) + tests
   - P004 Anchor (PMID 12-segment match) + tests
   - P005 Pool Router (3-havuz RRF k=60) + tests
   - P006 Reranker (BGE-v2-m3) + tests
   - P007 Curator (Outlines + LVR) + tests
   - P008 POST /api/search endpoint + integration + e2e + perf test
3. F3-§8 her commit sonrası verification
4. F3-DURDUR ARCHITECTURE.md v1.0 dondurulur

**Çıktı:** `curl POST /api/search` → JSON cevap (paper[] + faithfulness_meta + latency_ms). p50<4s hedefi.

---

### F4 — Frontend Skeleton + Arama Sayfası (3-4 gün)

**Plan Manifest:** `docs/plans/F4_frontend_skeleton_arama.md`

Next.js 14 + Tailwind + shadcn + i18n + arama sayfası `/kutuphane/arama/[query_id]` (PaperCard + KararBant + GateUyari + chip).

---

### F5 — Onboarding + Kütüphaneci Sohbet + Top 5 Onay (4-5 gün)

**Plan Manifest:** `docs/plans/F5_onboarding_chat.md`

8-input anket + multi-turn LLM sohbet + IntentPMID extraction + Top 5 paper onay (margin altı sorgu). OPEN-005 gerekli.

---

### F6 — Detay + Tema + Okuma + Ghost + Redis Cache Prime (4-5 gün)

**Plan Manifest:** `docs/plans/F6_detail_summary_ghost.md`

`/calisma-masasi/paper/[pmid]` + `/konu-atolyesi/tema/[id]` + `/konu-atolyesi/okuma/[pmid]` + ghost on-demand OpenAlex + Redis cache priming (Hat A.12 manuel listesinden). OPEN-006 gerekli.

---

### F7 — Quality Gate + Observability + Pilot Deploy (3-4 gün)

**Plan Manifest:** `docs/plans/F7_quality_deploy.md`

3-katlı faithfulness (JSON %100 + MiniCheck NLI ≥0.7 + ALCE ≥0.8) + Sentry/Prometheus/Grafana + Docker compose + HF Endpoint deploy + Supabase migration up + Pilot 5 user. OPEN-007 gerekli.

---

## 3. ONAY KAPILARI (R1 / DM-008)

```
[Plan Manifest yazılır] → [§0..§18 tam mı?] → [Omer "GO"]
                                                  ↓
                                           [Atomic commit'ler / belge yazımı]
                                                  ↓
                                        [§8 verification N PASS / 0 FAIL]
                                                  ↓
                                          [ROL 2 audit GREEN]
                                                  ↓
                                  [SPRINT_HISTORY + STATE güncelle]
                                                  ↓
                                          [Sonraki faza geç]
```

**Plansız iş yazılırsa:** STOP, geri al, plan manifest yaz, onay al, baştan.

---

## 4. CEVAP BEKLEYEN — Engelli Açık Kararlar

| OPEN | Engellediği | Son tarih |
|---|---|---|
| **METHOD §1 mekan modeli onayı** | F1 başlangıcı | Omer (yarın akşam öncesi) |
| OPEN-001 LLM model adı | F3 backend skeleton (abstract adapter ile geçici çözüm var) | Omer 2026-04-30 |
| OPEN-003 12 chip listesi | F2 backend planlama (chip_library/) | Omer F2 öncesi |
| OPEN-004 Pipeline_Akis canonical | F1-F2 chip + UI | Omer paylaşacak |
| OPEN-005 Top 5 onay davranışı | F5 onboarding | Omer F5 öncesi |
| OPEN-006 Ghost cache TTL | F6 enrichment | Omer F6 öncesi |
| OPEN-007 Pilot kullanıcı | F7 deploy | Omer F7 öncesi |
| B42-046 onayı (Papermind_V2 tarafı) | Backend Aşama 2 dondurma | Omer onayı sonrası DECISIONS'a yaz |

**METHOD §1 + OPEN-001/003/004** kritik — diğerleri faz öncesi cevaplanırsa yeter.

---

## 5. TAKVİM (kümülatif)

| Faz | Süre | Bitiş (en erken) |
|---|---|---|
| F0 + Hat A | tamam | 2026-04-29 |
| F1 frontend plan | 4-5 gün | 2026-05-04 (yarın akşam başlar) |
| F2 backend plan | 3-4 gün | 2026-05-08 |
| F3 backend kod | 4-5 gün | 2026-05-13 |
| F4 frontend kod | 3-4 gün | 2026-05-17 |
| F5 onboarding+chat | 4-5 gün | 2026-05-22 |
| F6 detay+tema+ghost | 4-5 gün | 2026-05-27 |
| F7 quality+deploy | 3-4 gün | 2026-05-31 |

**Toplam:** 28-35 gün → **MVP hazır 2026-05-27..05-31 aralığı.**

Kayma sebepleri (riskler):
- METHOD §1 onayı yarın gelmezse +1 gün
- OPEN cevapları gecikirse +2-3 gün
- HF Endpoint cold start çözümü zor çıkarsa +2 gün
- Faithfulness gate ALCE ≥0.8 zor tutturulursa +3-5 gün

---

## 6. ŞİMDİ — İLK SOMUT 3 ADIM

1. **Omer:** N11 v2 sabah biter → manifest paylaşır → IS_PLANI Hat A.1 son satır eklenir
2. **Omer:** Yarın Redis paper+theme curation manuel iş + akşam METHOD §1 onayı
3. **Claude:** METHOD §1 onayı gelince `docs/plans/F1_frontend_planlama.md` Plan Manifest yazımı

---

## 7. NE YAPILMAYACAK (kapsam dışı, MVP sonrası)

- AdvisorMind YOL 2 (Faz 2)
- JuryMind YOL 3 (Faz 3)
- 100M paper indirme (ay 6+)
- Mobile app
- Stripe billing
- Multi-tenant
- Lacuna platformu (ayrı proje)

Bunlar MVP'ye **eklenmez**, eklemek isteyen "sonra" der.
