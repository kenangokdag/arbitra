# HEDEF.md — Yemek Ne? (MVP Bitiş Tanımı)

> **Amaç:** "Sonunda nereye varacağımızı bilelim. Oraya bir şekilde varacağız ama önce yemek ne onu belirlemek lazım." — Omer 2026-04-29
> **Kullanım:** Her plan / öneri bu dosyaya bakar. Burada yazmayan özellik MVP'ye girmez. Burada yazan özellik MVP'de **çalışmak zorundadır**.

---

## 1. YEMEK — Tek cümle

**PaperMind MVP**, **Türkçe / İngilizce / Bahasa Indonesia** konuşan bir akademisyenin / öğrencinin tek bir doğal dil cümlesiyle 25M paper corpus üzerinden **5 saniye altında** literatür özetini çıkarıp; her cümlenin paper'la doğrulandığını gösteren, halüsinasyonu sıfır, karar bandıyla (canon / frontier / kuvvetli kanıt / risk) güvenilirlik veren bir akademik literatür asistanıdır. Onboarding'de seçilen ana dil (TR/EN/ID) sunum katmanını sabitler; karışık dil sorgu çatışması ortadan kalkar (B-005, 2026-04-30).

---

## 2. NE GÖRECEK SON KULLANICI (5 ana ekran)

### E1 — Onboarding (1 kez)
Ana akademik alan + eğitim seviyesi + dil tercihi + araştırma konusu (varsa) — 8 input, ~2 dk.

### E2 — Kütüphaneci sohbet (her oturum)
Konu yoksa LLM ile multi-turn diyalog → konu kilitlenir. Konu varsa atlanır.

### E3 — Top 5 paper onay (margin altı sorgularda)
PMID 12-segment match + clarification card. Kullanıcı "bu mu?" der → konu kilit.

### E4 — Arama sonucu (ana iş ekranı)
- Sorgu kutusu (TR/EN/karışık)
- Top 10 paper kartı (PaperCard M31)
- Her kart: başlık + yazar + yıl + venue + **karar bandı** + **gate uyarısı (G1-G7)** + 12 chip rozetleri
- "Neden?" tıkla → NedenPanel (engineer-mode: 13 sinyal detay)

### E5 — Paper detay + özet
- 13 sinyal görüntü
- "Özet ver" → on-demand LLM (Qwen + Claude TR rötuş)
- "Okuma önerisi" → 50 corpus komşu + ghost ek (M51)
- "Reading list'e ekle"

---

## 3. NE YAPACAK BACKEND (5 endpoint)

| Endpoint | İş |
|---|---|
| `POST /api/search` | 5-katman → top 10 paper + faithfulness_meta + latency_ms |
| `POST /api/chat` | Kütüphaneci LLM diyalog (SSE stream) |
| `POST /api/summarize` | On-demand özet (Celery → HF → Qwen → Claude → cache) |
| `POST /api/enrichment` | Ghost on-demand (OpenAlex .edu.tr polite pool) |
| `GET /api/reading-list` | M52 CRUD |

Auth: Supabase JWT. Cache: Redis (3-katlı). Worker: Celery.

---

## 4. KABUL KRİTERLERİ (sayı, ölçülebilir)

| # | Kriter | Hedef | Nasıl ölçülür |
|---|---|---|---|
| **C1** | Arama p50 latency | < 4s | 100 sorgu örnekleminin medyanı |
| **C2** | Arama p95 latency | < 7s | aynı örneklem |
| **C3** | JSON şema validation | %100 | Outlines + lm-format-enforcer |
| **C4** | MiniCheck NLI | ≥ 0.7 | 100 yanıt cümle örnekleminin ortalaması |
| **C5** | ALCE citation-recall | ≥ 0.8 | aynı örneklem |
| **C6** | Cache hit ratio | ≥ %70 | Redis stats 7 gün |
| **C7** | HF endpoint warm ratio | ≥ %95 | keep-alive ping log |
| **C8** | LVR_min_distance ihlal | %0 | her cümle paper_id+span ile doğrulanır |
| **C9** | K1 ihlali (yıl tahmini gösterimi) | %0 | runtime fail enforced |
| **C10** | Pilot 5 user sorgu sayısı | ≥ 50 / kullanıcı / hafta | Supabase event log |
| **C11** | Pilot kullanıcı NPS | ≥ +30 | hafta 2 anket |

**MVP "tamam" demek için:** C1-C9 her zaman PASS, C10-C11 pilot 2 hafta sonunda PASS.

---

## 5. NE YAPMAYACAK MVP (kapsam dışı — sycophant kalkanı)

| Özellik | Sebep | Ne zaman |
|---|---|---|
| AdvisorMind YOL 2 | 1 ay'a sığmaz | Faz 2 (ay 3-4) |
| JuryMind YOL 3 | 1 ay'a sığmaz | Faz 3 (ay 5-6) |
| 100M paper indirme | $300+ ek + leaf %95 kullanılmaz | Ay 6+ selective |
| Mobile app | web responsive yeter | Pilot sonrası |
| Stripe billing | pilot 5 user free | Pilot sonrası |
| Multi-tenant org | tek user için tasarlandı | Faz 2 |
| LLM ile özet otomatik üretim | $/cold start maliyeti | On-demand kalır |
| Lacuna platformu | ayrı proje | Ayrı repo |

Bu listeye eklemek "sonraki versiyon" demek; MVP'ye sokmak demek değil.

---

## 6. RAKİPLERDEN AYRIM (K6 — her zaman cevabı hazır)

| Rakip | Yapıyor | Biz farkımız |
|---|---|---|
| **SciSpace** | abstract özeti, ilişki bazlı | Biz **13 sinyal + karar bandı + LVR cümle-düzey atıf** |
| **Consensus** | claim → yes/no/mixed oran | Biz **gate sistemi (G1-G7) + Q_weak + MQ_Tier1** |
| **Elicit** | tablo çıkarma | Biz **5-katman pipeline + 3-havuz (Çekirdek/Komşu/Uzak) RRF** |
| **Scite** | citation context (supporting/contrasting) | Biz **CD₅ disruption + Sleeping Beauty + sentence-role** |
| **Genel** | İngilizce odaklı, opak skor | Biz **TR-native + karar bandı (skor değil) + neden-paneli** |

"Aynı"sa yapma. Bu tablo plan onayında her zaman gözden geçirilir (K6).

---

## 7. NEREYE VARILACAK — 30 günlük zincir

```
F0 ✅ → F1 (skeleton) → F2 (search slice) → F3 (frontend search) →
F4 (onboarding+chat) → F5 (detail+theme) → F6 (summary+ghost) → F7 (quality+deploy)
                                                                       ↓
                                                              MVP HAZIR — pilot 5 user
                                                                       ↓
                                                              C1-C11 ölç → pilot rapor
```

Her ok bir Plan Manifest + Omer onay + atomic commit'ler + §8 verification PASS.

---

## 8. HEDEF DOĞRULAMA SORUSU

Her plan / öneri sunulmadan önce sor:
> "Bu çıktı HEDEF.md §1-§4'tekini somut olarak ileri taşıyor mu, yoksa §5'tekine mi kayıyorum?"

Cevap "kayıyorum" ise STOP.
