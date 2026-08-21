# F2 Phase 3 — Warehouse Mirror Migration (Plan Manifest TASLAK)

> **Statü:** TASLAK (2026-04-30) — B-009 (Faz 2 satellite) PASS sonrası Omer onayı bekleyecek
> **Üst plan:** F1' Master Plan §5 (11 schema MVP) + B-008 + B-009 mirror genişlemesi
> **Karar referansı:** Memory `project_papermind_phase3` (Omer 2026-04-30 "hepsi" onayı)
> **Owner:** Omer (warehouse upload + onay) · Claude (migration script + plan watch + LVR audit)

---

## §0 Bağlam (3 cümle)

PaperMind v4 backend (F2 P006 Pool Router → P007 Reranker → P008 Curator) Pinecone'dan dönen paper_id listesini 13 sinyal ile zenginleştirir. Faz 1 (B-008 PaperCard + GhostCard) + Faz 2 (B-009 sentence_role + d_estra + ref_age) sonrası eksik kalan **9-12 warehouse fact/dim tablosu** (quality_v3, w_estra, velocity, field, interdisc, topic, metod, replication, method_topic_affinity, centrality, bibcoupling_top50, author) Supabase'e mirror'lanmadan F3a Pool Router runtime hot-path'te Drive cross-region read'e başvurmak zorunda kalır — KVKK + latency açısından sürdürülemez. Faz 3 = bu eksikleri kapatma migration paketi.

---

## §1 Karar günlüğü

| Karar | Kaynak | Etki |
|---|---|---|
| Drive warehouse fact/dim **HEPSİ** Supabase'e mirror | Omer 2026-04-30 onayı | Migration 0005-0008 |
| Drive'da kalır: `mart_cocitation_pair` (28 GB) + `mart_bibcoupling_pair` (30 GB) | F1 master §2 ASCII şeması + boyut → Postgres'e sığmaz | Pool Router komşu havuz `bibcoupling_top50` (4.81 GB Postgres'e gelir) ile çözülür; full pair mart sadece offline analiz için |
| Compute: upload sırasında **2XL → 4XL** geçici | Memory `feedback_supabase_compute_4xl` | $1.32 × ~5 saat ≈ $7 ek; bitince Small'a dönüş kalıcı |
| Disk: önceden ~80 GB autoscale (B-009 öncesi) | Memory `feedback_supabase_disk_threshold` | %85 threshold respect |
| FK pattern: `VALID_PAPER_IDS` anti-join (B-009 patch'i) | DECISIONS B-009 | Tüm 0005+ tablolarda fact_paper_id_card.paper_id'ye FK |
| Migration sayısı: 4 (0005-0008) tematik gruplama | scope/restart/audit kolaylığı | Aşağıda |

---

## §2 Tablolar (12 toplam, ~5-8 GB ek Postgres tahmini)

| # | Tablo | Drive parquet | Satır × kol | Drive boyut | Ekibi rol |
|---|---|---|---|---|---|
| 1 | `fact_paper_quality_v3` | `~/Dataleak/facts/fact_paper_quality_v3.parquet` | 24,867,210 × 6 | 216 MB | ESTRA q_weak + LF coverage + ci_band runtime lookup |
| 2 | `fact_paper_w_estra` | `~/Dataleak/facts/fact_paper_w_estra.parquet` | 24,867,210 × 15 | 1024 MB | w-ESTRA scalar + 4 alt eksen + gate_w |
| 3 | `fact_paper_velocity` | `~/Dataleak/facts/fact_paper_velocity.parquet` | 24,867,210 × 5 | 303 MB | d-ESTRA IR ekseni + age_adjusted_impact |
| 4 | `fact_paper_field` | `~/Dataleak/facts/fact_paper_field.parquet` | 24,866,945 × 4 | 177 MB | EB strata (`field × year`) + domain rollup |
| 5 | `fact_paper_interdisc` | `~/Dataleak/facts/fact_paper_interdisc.parquet` | 24,866,945 × 5 | ~320 MB | Rao-Stirling + n_distinct_themes (gate G7) |
| 6 | `fact_paper_topic` (rank≤3) | `~/Dataleak/facts/fact_paper_topic.parquet` | 24,867,210 × ? | ? | Pool Router theme havuz primary_topic + rank |
| 7 | `fact_paper_metod` | `~/Dataleak/facts/fact_paper_metod.parquet` | ? | ? | Anchor PMID 12-segment metod component |
| 8 | `dim_paper_replication` | `~/Dataleak/facts/dim_paper_replication.parquet` | 24,867,210 × 3 | ~80 MB | Replikasyon flag (broad regex CANDIDATE_ONLY) |
| 9 | `fact_method_topic_affinity` | `~/Dataleak/N09c/fact_method_topic_affinity.parquet` | 65,061 × 6 | <10 MB | M5 gap matrix slice (theme × method centrality) |
| 10 | `fact_paper_centrality` (corpus subset) | `~/Dataleak/facts/fact_paper_centrality.parquet` (filtrelenmiş) | ~24.87M × 4 | ~600 MB | s-ESTRA + advisor centrality (PageRank + indegree) |
| 11 | **`fact_paper_bibcoupling_top50`** | `~/Dataleak/N09b/fact_paper_bibcoupling_top50.parquet` | 643,445,780 × 5 | **4.81 GB** | Pool Router "Komşu" havuz cosine_direct_top50 |
| 12 | `dim_author` | `~/Dataleak/dims/dim_author.parquet` | 22,649,014 × 22 | ~3 GB | first_author h-index + coauth_deg lookup |

**Tahmini Postgres ek:** parquet 11.6 GB × ~1.5 indeks overhead ≈ **15-18 GB**. Disk hesabı tekrar:
- Faz 2 sonrası: ~44 GB total
- Faz 3 sonrası: ~60 GB total
- **80 GB disk hedef** önceden autoscale edildiğinde marj rahat (%75 doluluk)

---

## §3 Migration dosyaları (4 adet, atomik commit'ler)

| Migration | Tablolar | Mantık |
|---|---|---|
| **0005_paper_estra_facts.sql** | quality_v3 + w_estra + velocity | ESTRA çekirdek tabloları (Pool Router runtime hot-path) |
| **0006_paper_metadata_facts.sql** | field + interdisc + topic + metod + replication | Anchor PMID + gate sistemi tabloları |
| **0007_method_topic_centrality.sql** | method_topic_affinity + centrality (corpus subset) | Advisor + M5 slice |
| **0008_neighbor_graph_author.sql** | bibcoupling_top50 + dim_author | Komşu havuz + author meta (en büyük) |

Her migration: schema + CHECK constraint + FK to `fact_paper_id_card(paper_id)` ON DELETE CASCADE + indeksler. B-009 patch pattern'i (VALID_PAPER_IDS anti-join) loader scriptine uygulanır.

---

## §4 Notebook

`scripts/colab_load_phase3.ipynb` — tek notebook, **12 tablo sırayla** (küçükten büyüğe):

```
1. dim_paper_replication             (~80 MB,  ~5 dk)
2. fact_method_topic_affinity        (<10 MB,  <1 dk)
3. fact_paper_field                  (177 MB,  ~10 dk)
4. fact_paper_interdisc              (320 MB,  ~15 dk)
5. fact_paper_velocity               (303 MB,  ~15 dk)
6. fact_paper_quality_v3             (216 MB,  ~12 dk)
7. fact_paper_w_estra                (1024 MB, ~40 dk)  ← orta büyük
8. fact_paper_topic                  (?,       ~30 dk tahmin)
9. fact_paper_metod                  (?,       ~30 dk tahmin)
10. fact_paper_centrality            (~600 MB, ~25 dk)
11. dim_author                       (~3 GB,   ~90 dk)   ← büyük
12. fact_paper_bibcoupling_top50     (4.81 GB, ~3 saat) ← en büyük
```

**Tahmini toplam: ~7-8 saat upload** (4XL compute ile). Tek oturumda bitmezse her migration sonrası state.json checkpoint, restart-safe.

---

## §5 Önkoşullar

| Önkoşul | Statü |
|---|---|
| **Faz 2 (B-009)** sentence_role + d_estra + ref_age PASS | ⏳ Yarıda — Supabase disk açılınca devam |
| Pinecone N12d bulk import PASS (24,867,210 vector) | ⏳ Yarıda — split + import sürüyor |
| Disk hedef: **80 GB** (autoscale 60'tan sonra ek) | ⏳ Şu an autoscale 40 → 60 bekliyor; sonra Faz 3 öncesi 60 → 80 manuel? veya 2. autoscale otomatik mi? |
| Compute: **4XL** (geçici) — Faz 3 başlamadan önce | ⏳ B-009 sonrası geçilecek |
| Migration 0005-0008 schema yazılı + audit | ⏳ Plan onayı sonrası yazılacak |
| `VALID_PAPER_IDS` set hazır (Faz 1 PaperCard'dan) | ✅ B-008'de pattern kuruldu |

---

## §6 Çalıştırma sırası (B-009 PASS sonrası)

```
Adım 1: Plan manifest onayı (Omer onayı R1/DM-008)
Adım 2: Migration 0005-0008 yaz + lokal psql --dry-run audit
Adım 3: Compute 2XL → 4XL geçişi (Settings > Compute and Disk)
Adım 4: psql migration 0005-0008 apply
Adım 5: scripts/colab_load_phase3.ipynb hazırla (tek notebook 12 tablo)
Adım 6: Notebook çalıştır (~7-8 saat 4XL'de)
Adım 7: Verify (her tablo row count + index sanity)
Adım 8: Compute 4XL → Small (kalıcı tasarruf)
Adım 9: STATE.md + DECISIONS.md güncelle (B-010 entry)
Adım 10: F3a Pool Router lookup'ları artık Supabase'ten yapabilir (P006 önkoşul kapanır)
```

---

## §7 KK gate (her tablo için)

- Row count mismatch ≤ %0.05 (Drive parquet'ten)
- FK violation count = 0 (anti-join sonrası)
- NULL değer dağılımı parquet ile ±%1 sapma
- INDEX build PASS (her indeks için)
- Cosine sanity (centrality + author için indegree dağılımı)

---

## §8 Rollback

- Her migration ayrı commit; başarısızsa `DROP TABLE IF EXISTS` ile reset
- Loader idempotent (`ON CONFLICT (paper_id) DO NOTHING`)
- 4XL → Small downgrade her zaman geri alınabilir

---

## §9 Açık sorular (B-009 PASS sonrası netleşecek)

| OPEN | Soru | Karar gereği |
|---|---|---|
| OPEN-P3-1 | `fact_paper_topic` ve `fact_paper_metod` schema/satır net? Drive'da gerçek dosya boyutu? | Loader hücresi yazımdan önce `pf.metadata.num_rows` ile doğrula |
| OPEN-P3-2 | `fact_paper_centrality` corpus subset filtresi: `WHERE paper_id IN VALID_PAPER_IDS` — runtime'da uygulanır mı yoksa Drive'da pre-filter parquet hazırlanır mı? | Runtime daha hızlı (Drive parquet 100M satır) |
| OPEN-P3-3 | Disk 80 GB'a tek autoscale step'te ulaşır mı (40→60→80)? | Supabase autoscale step davranışı doğrulanmalı; gerekirse manuel cooldown sonrası 60→80 |
| OPEN-P3-4 | Pool Router runtime lookup: 12 tablo'dan hangileri `JOIN` mu `subquery` mi? | F3a P006 kod tasarımı sırasında |

---

## §10 Sonraki adım

Bu manifest **TASLAK**. B-009 PASS olduktan sonra (Pinecone import + Supabase satellite upload) Omer'in açık onayı alınınca kod yazılır (R1 / DM-008).

Onay öncesi yapılmayacak: migration .sql, notebook .ipynb, hiçbir kod commit'i.

---

## §11 SCOPE AUDIT — 2026-05-01 (Claude analiz + DÜZELTME)

**Bağlam:** Omer'in talebi (2026-05-01): *"envantere bak. eksik tablo var mı? supabase tarafında karşılaştıralım. sonra tekrar uğraşmayalım."*

**DÜZELTME (2026-05-01 öğle, halüsinasyon iptali):** İlk audit'te (turn 1) **8 eksik tablo** iddiası — `0001-0004` migration SQL'leri okunmadan yapıldı; halüsinasyondu. Gerçek migration tarama (`grep CREATE TABLE`) sonrası şu tablolar **zaten kaydedilmiş**:
- `fact_paper_id_card` → 0003 (B-008 PaperCard)
- `fact_paper_d_estra` → 0004 (B-009 satellite)
- `fact_paper_sentence_role` → 0004 (B-009 satellite)
- `fact_paper_ref_age` → 0004 (B-009 satellite)
- `fact_theme_year_aggregates` → 0002 (B-002 statik)
- `fact_gap_matrix` → 0002 (B-002 statik)

Yalnızca **2 tablo gerçekten eksik** (alt §11.2'de revize edildi).

ENVANTER.md §5 (fact tables) + §6 (edge/pair) tam tarandı; mevcut Faz 3 plan kapsamı (15 tablo) ile karşılaştırıldı.

### §11.1 Faz 3'te zaten kapsanan (15 tablo) ✅

| Migration | Tablo | Rows | Kaynak |
|---|---|---|---|
| 0005 | `fact_paper_quality_v3` | 24.87M × 6 | ENVANTER §161 |
| 0005 | `fact_paper_w_estra` | 24.87M × 15 | ENVANTER §178 |
| 0005 | `fact_paper_velocity` | 24.87M × 5 | ENVANTER §169 |
| 0005 | `fact_paper_disruption` (cd_5) | 24.87M × 8 | ENVANTER §176 |
| 0005 | `fact_paper_beauty` | 24.87M × 10 | ENVANTER §177 |
| 0006 | `fact_paper_field` | 24.87M × 4 | ENVANTER §168 |
| 0006 | `fact_paper_interdisc` | 24.87M × 5 | ENVANTER §173 |
| 0006 | `fact_paper_topic` | 69.75M × N | ENVANTER §3-4 |
| 0006 | `fact_paper_metod` | 51.79M × N | ENVANTER §4 |
| 0006 | `dim_paper_replication` | 24.87M | ENVANTER §3 |
| 0007 | `fact_method_topic_affinity` | 65,061 × 6 | ENVANTER §175 |
| 0007 | `fact_method_field_affinity` | 390 × 6 | ENVANTER §174 |
| 0007 | `fact_paper_centrality` | 24.87M (subset) | ENVANTER §163 |
| 0008 | `fact_paper_bibcoupling_top50` | 643M × 5 | ENVANTER §194 |
| 0009 | `dim_author` (dynamic) | 22.65M × 22 | ENVANTER §3 |

### §11.2 Gerçekten eksik tablolar — REVİZE (2 tablo)

| # | Tablo | Rows × Cols | Disk parquet | Kanıt | Niçin lazım |
|---|---|---|---|---|---|
| 1 | **fact_paper_abstract_flags_v5** | 24.87M × 7 | 0.36 GB | A (B42-035, manifest 2026-04-27 N05d_UNION) | LLM-validated `has_hypothesis` + `has_novelty` UI rozeti (Scite/Consensus pattern); JuryMind persona kritiği input; t-ESTRA `MQ_k` Plan 1 patch (theme_year_aggregates'te `mq_k` NULL/blocked → flags_v5 olmadan dolmaz) |
| 2 | **fact_paper_temporal** | 18.38M × 7 | ~0.3 GB | A (W-03) | `total_citations` (OpenAlex `cited_by_count`, ≠ centrality.indegree) + `cite_half_life` (Price 1965, ≠ beauty.B Sleeping Beauty) + `cite_recency_index`; alan yaşlanma rozeti, recency UI sinyali |

**Toplam ek disk:** ~0.6 GB Drive parquet → Postgres'te ~1-1.5 GB tahmini.

### §11.2-bis 7-kontrol uygulaması (closure-bias düzeltmesi)

İlk turn'de "Plan 2'ye ertelenebilir" dedim → **closure-bias** (Faz 3 kapatma aceleciliği). Düzeltme:

1. **Literatür** — has_hypothesis/has_novelty Scite/Consensus/SciSpace ürün omurgası. Atlamak rakip karşısında zayıflık.
2. **Halüsinasyon** (önceki turn'de düştüm):
   - "cite_half_life ≈ beauty.B" — YANLIŞ. Beauty.B = Ke 2015 Sleeping Beauty (geç keşif). half_life = Price 1965 atıf yarı-ömrü (alan yaşlanma). Farklı metrikler.
   - "total_citations ≈ centrality.indegree" — YANLIŞ. indegree = corpus içi referans, cited_by_count = OpenAlex tüm atıf. Genellikle cited_by_count >> indegree.
3. **Fayda-maliyet** — Postgres ek 1-1.5 GB; 4XL window halen açık → upload 5-10 dk; SQL ~80 LOC.
4. **Daha kolayı** — Şimdi yüklemek vs. Plan 2'de ayrı oturum + 4XL geri açma + state restore (~1-2h).
5. **Son kullanıcı avantajı** — Akademisyen profili (empirical-test ↔ theoretical-novelty ayrımı) için has_hypothesis/has_novelty rozeti **birinci derece değerli**.
6. **Rakip** — Scite claim detection ürün omurgası. Atlamak = zayıflık.
7. **Lokal vs global** — Şimdi tek migration global çözüm; erteleme = lokal hack.

### §11.3 Bilinçli Drive-only (mirror edilmez) ✅

- `mart_cocitation_pair` (2.45B pair / 28.14 GB) — manifest_Marts 2026-04-27 PASS — Drive (Postgres'e sığmaz)
- `mart_bibcoupling_pair` (2.39B pair / 29.80 GB) — Drive sync FAIL kurtarma in-flight — Drive
- `fact_paper_sentence` (193.65M sentence-level × 6) — engine.Curator BGE-reranker retrieval index, Drive
- `fact_citation_edge` (833M edge × 3) — graph compute, Drive
- `fact_coauthor_edge` (256M edge × 5) — graph compute, Drive
- `fact_paper_pagerank` — `fact_paper_centrality` subset (redundant)
- v1/v2 `fact_paper_quality`, v1/v4 `fact_paper_abstract_flags` — DEPRECATED
- `fact_term_arm_static` (297K) + `fact_term_arm_temporal` (547K) — gap mining input, Drive (küçük ama sadece offline analiz; mirror edilebilir Plan 2)
- `n15_*` state tables (rollup intermediate) — Drive

### §11.4 REVİZE aksiyon (Omer akşam çalışacak)

**Verdict:** Faz 3 = 15 tablo (mevcut plan, yüklenmekte) + **2 micro tablo (yeni 0010 migration)**. Toplam 17.

**Yapılacak:**
- `0010_paper_flags_temporal.sql` (2 tablo): `fact_paper_abstract_flags_v5` (24.87M × 7) + `fact_paper_temporal` (18.38M × 7)
- Colab `colab_load_phase3.ipynb`'a 2 upload cell ekle (en küçükten en büyüğe sıralamada `temporal` ve `flags_v5` orta blok)
- 4XL window halen açıkken yüklenir (~5-10 dk ek)

**Şema notları (SQL yazılırken):**
- `flags_v5`: `id` parquet kolonu → `paper_id` rename (semantik açıklık, fact_paper_topic pattern); `has_hypothesis` + `has_novelty` Int64→smallint nullable (parse_err non-NULL durumlarda flag NULL olabilir, CHECK koymadan); `result/parse_err` text nullable; logprob'lar double precision; FK `fact_paper_id_card(paper_id) ON DELETE CASCADE`; index: `has_hypothesis` + `has_novelty` partial WHERE = 1.
- `temporal`: paper_id PK FK; `total_citations` integer NOT NULL; 5 metrik real; FK aynı; coverage 18.38M/24.87M (sparse, atıfsız 6.49M paper bu tabloda yok — anti-join doğal); index: `total_citations DESC`, `cite_half_life`, `cite_recency_index DESC`.
- L-021 `_norm_w` defansif paper_id normalize loader-side (SQL DDL'de değil).
- L-022 Int8 NOT Bool (Polars/parquet sadık mirror).

**Karar yetkisi:** Omer (akşam SQL üret + Supabase Dashboard'a paste). Onay öncesi sql commit edilmez.

**~~Eski 8-tablo öneri~~** (arşiv): ~~0010_paper_card_estra + 0011_theme_gap_signals~~ — halüsinasyondu, 5/8 tablo zaten 0001-0004'te kayıtlı.
