# reference/ — READ-ONLY warehouse referansı

> **⛔ EDIT YASAK.** Bu klasör Papermind_V2 warehouse build'inin dondurulmuş özetidir.
> Değişiklik için: `~/Desktop/Papermind_V2/` klasörüne git, oradan güncelle, sonra buraya kopyala.

---

## Ne içerir (Papermind_V2 closure sonrası buraya kopyalanacak)

| Dosya | Kaynak | Amaç |
|---|---|---|
| `ENVANTER.md` | Papermind_V2/04_plan_analiz_kararlar/ENVANTER.md (final) | Drive warehouse tek doğruluk |
| `ENVANTER_dump.json` | envanter_dump notebook çıktısı | Drive gerçek state snapshot |
| `ENVANTER_dump.md` | envanter_dump notebook çıktısı | İnsan-okur tablo |
| `DECISIONS_warehouse.md` | Papermind_V2/04/DECISIONS.md (B41-001..B42-046 closure) | Warehouse karar log'u |
| `ESTRA_uygulama_politikasi.md` | Papermind_V2/04/ESTRA_uygulama_politikasi_2026-04-26.md | ESTRA Politikası v1.1 |
| `Pipeline_Akis_v4.md` | Papermind_V2/05_dokumanlar/Pipeline_Akis.docx → md çevrimi | Canonical pipeline |
| `B42_045_paper_card.md` | DECISIONS.md B42-045 entry özeti | M31 + M51 + 5-katman + PMID |
| `B42_040_chip_library.md` | DECISIONS.md B42-040 entry özeti | 12 scientometric chip + 4 freeze |
| `BACKEND_PROTOKOL.md` | Papermind_V2/04/BACKEND_PROTOKOL.md | 6-fazlı + ROL 1/2/3 + bütçe |
| `ARCHITECT_PROMPT_TEMPLATE.md` | Papermind_V2/04/ARCHITECT_PROMPT_TEMPLATE.md | Plan Manifest §0..§18 |
| `manifests/` | Drive `~/Dataleak/state/manifest_*.json` son snapshot | Tablo PASS verdict tarihçesi |

---

## Ne ZAMAN kopyalanacak

**Papermind_V2 closure tamam olduktan sonra:**

1. ✅ N09e CD₅ Disruption PASS (28 Nis 14:35) — TAMAM
2. ⏳ N14b_patch_CD_k → t-ESTRA 8/8 closure (~1-2h)
3. ⏳ N17 audit → warehouse PASS verdict (~4-5h)
4. ⏳ N18 Supabase upload (~6-8h)
5. ⏳ envanter_dump notebook koş

Sonra Bash ile kopyalama:
```bash
cp ~/Desktop/Papermind_V2/04_plan_analiz_kararlar/ENVANTER.md ~/Desktop/papermind-app/reference/
cp ~/Desktop/Papermind_V2/04_plan_analiz_kararlar/DECISIONS.md ~/Desktop/papermind-app/reference/DECISIONS_warehouse.md
cp ~/Desktop/Papermind_V2/04_plan_analiz_kararlar/ESTRA_uygulama_politikasi_2026-04-26.md ~/Desktop/papermind-app/reference/
cp ~/Desktop/Papermind_V2/04_plan_analiz_kararlar/BACKEND_PROTOKOL.md ~/Desktop/papermind-app/reference/
cp ~/Desktop/Papermind_V2/04_plan_analiz_kararlar/ARCHITECT_PROMPT_TEMPLATE.md ~/Desktop/papermind-app/reference/
# ENVANTER_dump.json + ENVANTER_dump.md Drive'dan indirildikten sonra
```

---

## Niye read-only?

- **Tek doğruluk:** Tek bir kaynak → karışıklık yok
- **Audit trail:** Warehouse kararları zaten Papermind_V2'de tarihçeli
- **MVP odak:** Yeni kod burada YAZILMAZ; backend/frontend/engine'de yazılır
- **Karışıklık önleme:** Eski hesap işlerini MVP geliştirme klasörüyle karıştırmamak için
