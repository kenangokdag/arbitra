# Envanter & Felsefe — PaperMind Sayfa Dağılımı

> **Amaç:** TÜM sistem çıktılarını (sinyaller + warehouse + endpoint + sayfa) tek dosyada görmek. Sonra adil dağıtım için seçim/optimize yapmak.
> **Kanon kaynaklar:** PaperMind_mock.html (1414 sat, 7-rol felsefesi, ~20 sayfa) + sidebar `nav-config.ts` (28 sayfa) + SPINE.md §0 + DECISIONS.md DM-046..055 + planda olan/canlı endpoint'ler.
> **Tarih:** 2026-05-08. Halüsinasyon yasağı: her satırın arkasında repo dosyası veya mock alıntısı var.

---

## §1 — FELSEFE (mock'un 7 rol-fiili)

Mock'ta her workbench TEK bir fiille tanımlı. Bu çerçeve sayfa dağılımının omurgası.

| Rol | Anlam | Workbench | Sayfa sayısı (mock) |
|---|---|---|---|
| **VİTRİN** | Profilsiz, açık mod — hesap/imza yok | Hızlı İnceleme | 4 (Q + Q1 + Q2 + Q3 — ama DM-054 ile **Q2 ELİMİNE** → 3) |
| **KABUK** | Girişli kullanıcının panosu + ayarlar | Ana Sayfa, Ayarlar | 2 |
| **GÖSTERİR** | Manzara, anchor-nötr (kullanıcı görür, okur, olgunlaştırır) | Discovery | 3 |
| **SEÇER** | Kişisel havuz — anchor-merkezli kürasyon | Curation | 2 |
| **İŞARETLER** | Boşluk tespiti — fırsat haritalama | GapAtlas | 2 |
| **YAZAR** | Bilişsel iş ayrı — yazma + dil + atıf | Authoring | 3 |
| **SINAR** | Hakem ≠ jüri — antrenman + simülasyon + sevkıyat | Defense | 4 |

**Mock toplam: 19 sayfa (Q2 sonrası).**
**Sidebar toplam: 28 sayfa** (Vitrin 3 + Discovery 5 + Curation 5 + GapAtlas 5 + Authoring 4 + Defense 6).
**Fark: +9 sayfa** sidebar mock'tan şişkin.

**Felsefe ilkesi (mock alıntı):** *"Hızlı = vanilla, atölye = imza."* Vitrin sade SciSpace mantığı; atölye'de PaperMind imzası (validator çift mühür + ESTRA + gap matrix + jüri sim).

---

## §2 — ÇIKTI ENVANTERİ (proje state — kullanıcının elinde ne var?)

Her sayfa bir veya birkaç **proje state** üretir veya günceller. Funnel akışı:

```
[Q] → query_id (vitrin oturumu, ölmek)
       ↓ "Projeme Dönüştür"
[Discovery 1: Keşfet]      → project_cluster + project_anchor
[Discovery 2: Nabız]       → bibliometric_snapshot
[Discovery 3: Kavram Ağı]  → concept_node + concept_edge
       ↓
[Curation 1: Connected]    → curation_pool
[Curation 2: Havuzum]      → shortlist + paper_role + paper_annotation
       ↓
[GapAtlas 1: Boşluk]       → gap_signal + golden_gap
[GapAtlas 2: Soru&Başlık]  → research_question + title_proposal
       ↓
[Authoring 1: Lit]         → manuscript_section [literatür]
[Authoring 2: Bölüm]       → manuscript_section.draft (intro/findings/discussion)
[Authoring 3: Üslup]       → user_style_profile (sessiz öğrenme)
       ↓
[Defense 1: Prova]         → defense_session
[Defense 2: Hakem]         → revision_list
[Defense 3: Jüri]          → jury_session_log
[Defense 4: Sevkıyat]      → publication_plan + submission_pack
```

**Önemli:** funnel **doğrusal değil dallı**. Curation paralel olabilir; Discovery 2/3 paralel; GapAtlas 1+2 sıralı. Authoring/Defense bölümleri istenildiği sırada.

---

## §3 — HESAPLAMA / SİNYAL ENVANTERİ (40 sinyal)

Mock + plan'lardan toplanan **tüm** hesaplanabilir sinyaller. Her sinyalin warehouse kaynağı + kullanım sayfası belirtilmiş.

### A. Embedding & retrieval (havuz oluşturma)
| # | Sinyal | Kaynak | Kullanım sayfası |
|---|---|---|---|
| 1 | bgem3 1024-d cosine embedding | Pinecone | Discovery 1, Curation 1, Authoring 1 |
| 2 | BM25 hybrid | tsvector + Pinecone | Discovery 1 |
| 3 | c-TF-IDF cluster | offline batch | Discovery 1 |
| 4 | HyDE → fan-out → RRF → rerank | F9 anchor_finder | Discovery 1 (Stage B) |
| 5 | 5-katman pipeline (Listener/Anchor/PoolRouter/Reranker/Curator) | engine/ | Q + (eski plan) Discovery 2 |
| 6 | LangDetect TR/EN/ID | langdetect | Q (havuz dil routing) |
| 7 | Bibliographic coupling top-50 | fact_paper_bibcoupling_top50 (4.81 GB · 643M sat) | Curation 1 |
| 8 | Co-citation 2-hop | mart_cocitation_pair | Curation 1 (opsiyonel) |
| 9 | Margin gate (raw reranker score) | Q havuz logic | Q1 LLM rerank |

### B. Olgunluk & kalite (paper sınıflandırma)
| # | Sinyal | Kaynak | Kullanım sayfası |
|---|---|---|---|
| 10 | **t-ESTRA olgunluk** (4 sınıf: Core/Emerging Frontier/Golden Zone/Weak Signal) | fact_paper_topic + 7-boyut | Discovery 1 (cluster rengi) |
| 11 | **w-ESTRA 7-boyut** (paper kalite radar) | fact_paper_w_estra | Curation 1 (hover-card), Curation 2 (mühür) |
| 12 | **r-ESTRA** (kullanıcı/öğrenci profili) | user_style_profile | Authoring 3 (üslup), GapAtlas 1 (uyum) |
| 13 | **a-ESTRA** (advisor profili) | advisor_profile | GapAtlas 1 (sweet spot) |
| 14 | RCR (iCite) | validator API | Curation 1/2 (ESTRA Pasaportu) |
| 15 | FCR (Dimensions) | validator API | Curation 1/2 |
| 16 | SJR (SCImago) | dim_journal | Curation 1/2, Discovery 2 (top mecra) |
| 17 | h-index sıralama | dim_author | Discovery 2 (top yazar) |

### C. Anomali & atılım (zaman/atıf dinamiği)
| # | Sinyal | Kaynak | Kullanım sayfası |
|---|---|---|---|
| 18 | **Funk-Owen CD index** (Disruption ★) | fact_paper_velocity | Discovery 2 (★ rozet, "hangi referansı yıktı" panel) |
| 19 | **Sleeping Beauty B-coefficient** (◆) | fact_paper_velocity | Discovery 2 (◆ rozet) |
| 20 | Atıf hızı eğrisi (citation velocity) | fact_paper_velocity | Discovery 2 |
| 21 | Novelty (Uzzi) | fact_paper_quality_v3 | Curation 1 (ESTRA Pasaport) |

### D. Kavram & ontoloji (terim grafı)
| # | Sinyal | Kaynak | Kullanım sayfası |
|---|---|---|---|
| 22 | **KeyBERT extraction** | offline batch | Discovery 3 |
| 23 | **NPMI eş-anma** | concept_edge | Discovery 3 |
| 24 | **Betweenness centrality** (köprü kavram) | concept_edge | Discovery 3 (altın yıldız rozet) |
| 25 | Eigenvector centrality | concept_edge | Discovery 3 |
| 26 | **11-kategori ontoloji** (FLD/CON/THR/MTD/ANL/SMP/CTX/INS/OUT/TEC/TMP) | dim_term | Discovery 3 (renk-kod), Authoring 2 (rol-aware atıf) |
| 27 | Yükseliş eğrisi (yeni terim trend) | concept_edge time-series | Discovery 3 (panel) |

### E. Boşluk & fırsat (gap atlas)
| # | Sinyal | Kaynak | Kullanım sayfası |
|---|---|---|---|
| 28 | **8 boşluk formülü M1-M8** (0.25D + 0.20K + 0.20E + 0.15F + 0.20Y) | fact_paper_topic + fact_paper_metod + fact_paper_w_estra | GapAtlas 1 |
| 29 | **a-ESTRA × r-ESTRA sweet spot** (0.55-0.85) | uyum yüzdesi | GapAtlas 1 (yeşil bant) |
| 30 | 3-mod RQ stilleri (temkinli/dengeli/iddialı) | LLM | GapAtlas 2 |
| 31 | **3 bağımsız özgünlük denetimi** (OpenAlex + S2 + Pinecone) | validator API trio | GapAtlas 2 (🟢/⚠/🔴) |
| 32 | **230-keyword title profile** (atıf-potansiyeli) | offline batch | GapAtlas 2 (deneysel) |

### F. Yazım & atıf (RAG + faithfulness)
| # | Sinyal | Kaynak | Kullanım sayfası |
|---|---|---|---|
| 33 | **Faithfulness skoru** (LLM atıf doğrulama) | RAG + cite-verifier | Authoring 1, Defense 1 (atıfsız iddia) |
| 34 | Cümle bazlı paper-zinciri ①②③ | section_citation_link | Authoring 1/2 |
| 35 | **Rol-aware atıf** (Temel→Giriş, Ampirik→Bulgular) | paper_role + section type | Authoring 2 |
| 36 | TR/EN ayrı stil kural seti (devrik/edilgen/tekrar) | engine/style | Authoring 3 |
| 37 | **Sycophant kilidi** | LLM prompt + Pydantic gate | Authoring tüm + Defense tüm |

### G. Defense (sınama)
| # | Sinyal | Kaynak | Kullanım sayfası |
|---|---|---|---|
| 38 | 30-soru havuzu (anchor/RQ/yöntem/etki/sınırlılık) | defense_question_bank | Defense 1 |
| 39 | **3 hakem persona** (Şüpheci/Sempatik/Yöntemci) | LLM persona | Defense 2 |
| 40 | **Karar tahmini bandı** (kabul/küçük/büyük/red) | 3 ortalama + SJR + scope match | Defense 2 |
| 41 | **Çok-ajan jüri + zincir soru** (max 2 derinlik) | LLM agent sim | Defense 3 |
| 42 | Statcheck (p-değeri tutarlılık) | engine/statcheck | Defense 4 |
| 43 | Dergi eşleme (kapsam + etki + ücret) | dim_journal + Unpaywall | Defense 4 |

### H. Operasyonel (sessiz öğrenme + tier)
| # | Sinyal | Kaynak | Kullanım sayfası |
|---|---|---|---|
| 44 | Sessiz öğrenme (kabul/red → r-ESTRA güncelleme) | user_silent_learning_log (30g) | Authoring 3, Settings |
| 45 | Validator çift mühür (RCR×FCR×SJR uyum 🟢🟡🔴) | validator API trio | Curation 2 (rozet) |
| 46 | Tier matrisi (T0-T4) | user_subscription | Ana Sayfa (5-satır vurgu) |
| 47 | Aylık öneri engine | recommendation_log | Ana Sayfa (deneysel batch) |
| 48 | Atıfsız iddia tespiti (cümle-eşleme) | RAG | Defense 1 |

**Toplam: 48 hesaplanabilir sinyal.**

---

## §4 — WAREHOUSE TABLO ENVANTERİ

### A. Fact (ölçüm)
| Tablo | Boyut | Kaynak | Kullanım |
|---|---|---|---|
| fact_paper_id_card | 24.86M paper | Papermind_V2 | tüm sayfalar (paper meta) |
| fact_paper_topic | — | offline | Discovery 1/3, GapAtlas, Authoring 1 |
| fact_paper_centrality | — | offline | Discovery 1/2 |
| fact_paper_velocity | — | offline | Discovery 2 (Disruption + Sleeping Beauty) |
| fact_paper_quality_v3 | — | offline | Curation 1 (ESTRA Pasaport) |
| fact_paper_w_estra | 7-boyut | offline | Curation, GapAtlas 1, Authoring |
| fact_paper_bibcoupling_top50 | **4.81 GB · 643M sat** | offline | Curation 1 (en ağır tablo) |
| fact_paper_metod | — | offline | Q3 (metod dağılımı), GapAtlas 1 |
| fact_method_topic_affinity | — | offline | Defense 4 (yöntem uyum) |
| fact_paper_signals_13 | abstract flags | offline | (planda — eski referans) |

### B. Dim (boyut)
| Tablo | Boyut | Kullanım |
|---|---|---|
| dim_paper_field | — | Discovery 1 |
| dim_author | **22.65M** | Discovery 2 (top yazar) |
| dim_journal | SCImago Q1-Q4 | Discovery 2, Curation, Defense 4 |
| dim_term | 11-kategori ontoloji | Discovery 3, Authoring 2 |

### C. Mart (hazır birleştirme)
| Tablo | Kullanım |
|---|---|
| mart_cocitation_pair | Curation 1 (2-hop opsiyonel) |

### D. Project state
| Tablo | Üreten | Tüketen |
|---|---|---|
| projects | "Projeme Dönüştür" / Discovery 1 | tüm proje sayfaları |
| project_cluster | Discovery 1 | Discovery 2/3, GapAtlas |
| project_anchor | Discovery 1 | Curation 1 |
| project_pool | Curation 1 | Curation 2, Authoring, GapAtlas |
| project_event | her sayfa eylem | Ana Sayfa (timeline) |
| paper_role | Curation 2 | Authoring 2 (rol-aware atıf) |
| paper_annotation | Curation 2 | Authoring |
| paper_translation_cache | Curation 2 | Authoring |
| gap_signal + golden_gap | GapAtlas 1 | GapAtlas 2 |
| research_question + title_proposal | GapAtlas 2 | Authoring |
| manuscripts + manuscript_section | Authoring | Defense |
| section_citation_link | Authoring 1 | Authoring 2, Defense 1 |
| advisor_profile | onboarding | GapAtlas 1 |
| user_style_profile | sessiz öğrenme | Authoring 3 |
| user_silent_learning_log (30g) | Authoring 3 | Settings |
| defense_session | Defense 1 | — |
| peer_review_simulated | Defense 2 | — |
| jury_session_log | Defense 3 | — |
| publication_plan + submission_pack | Defense 4 | — |
| user_subscription (T0-T4) | Stripe / pilot key | Ana Sayfa, paywall |
| paid_unlock | one-shot ödeme | tier override |

**Toplam: ~30 fact/dim/mart/state tablosu.**

---

## §5 — ENDPOINT ENVANTERİ

### Mevcut canlı (papermind-app/api)
- POST /api/q/search · POST /api/q/literature (Q1) · POST /api/q/method (Q3) — **DM-055, partial implement**
- POST /api/waitlist
- POST /api/project/{id}/research-area/messages — **F9 P094 canlı** ✅
- POST /api/project/{id}/research-area/anchor-candidates — **F9 P095 canlı** ✅
- POST /api/top5 — **B-018 canlı** ✅
- POST /api/project/{id}/research-area/anchor/lock — **F9 P096 IN-QUEUE** ⏳

### Mock'ta tanımlı, henüz yok
- POST /api/discovery/topics (Keşfet — Discovery 1 monolitik akış)
- GET /api/discovery/biblio?topic_id= (Nabız)
- GET /api/discovery/concept-network?topic_id= (Kavram Ağı)
- GET /api/discovery/anchor?paper_id= (Connected Papers)
- POST /api/curation/role-suggest
- POST /api/translate (EN→TR 2-line cache)
- POST /api/gapatlas/matrix
- POST /api/gapatlas/rq-title
- POST /api/authoring/lit-review
- POST /api/authoring/section
- POST /api/authoring/style
- POST /api/defense/practice
- POST /api/defense/peer-review
- POST /api/defense/jury
- POST /api/defense/dispatch
- GET /api/projects + /api/projects/{id}/timeline
- GET /api/recommend/monthly (deneysel batch)
- GET /api/me/tier
- GET/PUT /api/settings · DELETE /api/learning/reset · GET /api/user/export · GET /api/guardian/health

**Toplam endpoint: 25** (4 canlı + 1 IN-QUEUE + 20 mock-tanımlı).

---

## §6 — SAYFA ENVANTERİ (mock vs sidebar yan yana)

| Workbench | Mock | Sidebar | Δ | Mock isimleri | Sidebar isimleri |
|---|---|---|---|---|---|
| **Vitrin** | 4 (Q2 dahil) | 3 (Q2 elimine) | -1 | Hızlı İnceleme · Lit · Giriş · Metod | Q · Q1 · Q3 |
| **Ana Sayfa** | 1 | 0* | -1 | Projelerim | (kabuk dışı) |
| **Discovery** | 3 | 5 | **+2** | Keşfet · Nabız · Kavram Ağı | Araştırma · Konu · Bibliyo · Tematik · Kavram |
| **Curation** | 2 | 5 | **+3** | Connected · Havuzum | Önerilen · İlişkili · Yöntem&Veri · Sentez · Gen.Sentez |
| **GapAtlas** | 2 | 5 | **+3** | Boşluk · RQ&Başlık | Harita · Profil · Özgünlük · Karş. · Etki Eğrisi |
| **Authoring** | 3 | 4 | +1 | Lit · Bölüm · Üslup | Format · Taslak · Dil · Atıf&Stil |
| **Defense** | 4 | 6 | +2 | Prova · Hakem · Jüri · Sevkıyat | Format · İçerik · Bireysel · Kaynak · Jüri&Hakem · Tamamlama |
| **Ayarlar** | 1 | 0* | -1 | Ayarlar | (kabuk dışı) |
| **TOPLAM** | **20** (Q2'siz 19) | **28** | **+8/+9** | | |

*Sidebar'da Ana Sayfa + Ayarlar var ama "general" kategoride; workbench değil.

---

## §7 — DENGESİZLİK ANALİZİ

### A. Sidebar şişkinliği
Sidebar mock'tan **+9 sayfa şişkin**. En çok şişkin: Curation +3, GapAtlas +3, Discovery +2, Defense +2. Bu sayfaların **gerçek bir iş yapıp yapmadığı belirsiz** — mock 1 sayfada toplandığı işler sidebar'da 2-3 sayfaya yayılmış.

### B. Adil olmayan dağıtım örnekleri
- **Discovery sidebar 5 sayfa** ama gerçek sinyal 3 farklı (Keşfet/Nabız/Kavram). Tematik (UMAP) sinyali mock'ta YOK; sidebar'a fazladan eklenmiş. Konu Belirleme sinyali mock'ta Keşfet içine gömülü.
- **Curation sidebar 5 sayfa** ama mock 2 sayfada bitiriyor (Connected Papers + Havuzum). Sidebar 5 isim üretmiş ama içerik 2 işe sığar.
- **GapAtlas sidebar 5 sayfa** ama mock 2 işe indirgemiş (Boşluk Atlası + RQ&Başlık). 8-matris + RQ + başlık = 2 sayfa yeter, sidebar 5 sayfaya yaymış.
- **Defense sidebar 6 sayfa** ama mock 4 işe sığdırıyor: prova / hakem / jüri / sevkıyat. Sidebar "Format" ve "Kaynak Bütünlüğü" gibi ek sayfalar eklemiş — gereksiz.

### C. Algoritma derinlik enjeksiyonu eksik
Plan'larda algoritma yüzeysel — mock'ta zenginlik var ama sidebar plan'larına geçmemiş. Eksik enjeksiyonlar:
- t-ESTRA olgunluk (Discovery)
- Funk-Owen CD + Sleeping Beauty (Discovery — Nabız)
- KeyBERT + NPMI + 11-kategori ontoloji (Discovery — Kavram)
- 8 boşluk formülü M1-M8 (GapAtlas)
- a-ESTRA × r-ESTRA sweet spot (GapAtlas)
- Bibliographic coupling top-50 (Curation)
- Faithfulness skoru + cite-verifier (Authoring)
- 3-persona hakem + zincir soru (Defense)
- 230-keyword title profile (GapAtlas RQ)
- Validator çift mühür (Curation)

### D. Endpoint tasarım çelişkisi
- Mock: `POST /api/discovery/topics` **monolitik** (alan + cluster + anchor TEK endpoint)
- Plan: `POST .../research-area/messages` + `POST .../anchor-candidates` + `POST .../anchor/lock` (3 endpoint)
- Mock = atomik flow; Plan = staged flow. Plan F9 (Stage A + B + Lock) zaten 3-stage; mock soyutlamış.
- **Karar gerek**: monolitik mı kalsın (kullanıcı 1 sayfada) yoksa staged endpoint'ler mi (mevcut F9 mimari)?

---

## §8 — 3 SENARYO (sayfa dağıtımı için)

### Senaryo A — Mock kanon (sidebar küçültülür)

**Hedef: 19-20 sayfa.** Sidebar'dan 8-9 sayfa silinir.

| Workbench | Sayfa | Yeni isim/birleşim |
|---|---|---|
| Vitrin | 3 | Q · Q1 · Q3 (mevcut) |
| Discovery | 3 | **D1 Keşfet** (Araştırma+Konu+Tematik birleş) · D2 Nabız · D3 Kavram Ağı |
| Curation | 2 | C1 Connected (İlişkili+Önerilen birleş) · C2 Havuzum (Yöntem+Sentez+GenSentez birleş) |
| GapAtlas | 2 | G1 Boşluk Atlası (Harita+Profil+Özgünlük+Karş+Etki birleş) · G2 RQ&Başlık |
| Authoring | 3 | A1 Lit · A2 Bölüm (Taslak+Dil+Atıf birleş) · A3 Üslup |
| Defense | 4 | F1 Prova (İçerik+Bireysel+Kaynak birleş) · F2 Hakem · F3 Jüri · F4 Sevkıyat (Format+Tamamlama birleş) |

**Avantaj:** Mock'un sade felsefesi (1 fiil = 1 işe odak), endpoint mimarisi atomik, kullanıcı gezintisi az.
**Dezavantaj:** Sidebar 28 → 17 sayfa **revizyon büyük**. Planlanan UMAP+HDBSCAN içerik yok.
**Effort:** Sidebar refactor + plan rewrite (5 plan değil 3 plan Discovery için) + 8 sayfa silinen kararla DM yazımı.

### Senaryo B — Sidebar kanon (mock derinlik enjekte)

**Hedef: 28 sayfa kalır.** Mock'tan algoritma sinyalleri her sayfaya enjekte edilir.

Ek sayfaların gerçek işleri tanımlanır:
- Discovery: 5 sayfa kalır → her birine 1 sinyal-grubu atanır
  - disc-1 = sohbet+çapa (mevcut plan)
  - disc-2 = top-5 konu lock (mevcut)
  - disc-3 = Nabız (Funk-Owen CD + Sleeping Beauty)
  - disc-4 = t-ESTRA olgunluk haritası (UMAPClusterCard reuse)
  - disc-5 = Kavram Ağı (KeyBERT + NPMI + 11-kategori)
- Curation 5 sayfa: Önerilen=eski connected papers; İlişkili=co-citation; Yöntem&Veri=fact_paper_quality_v3 detay; Sentez=tema RAG; GenSentez=cross-paper sentez
- GapAtlas 5 sayfa: Harita=8-matris; Profil=hücre detay; Özgünlük=3 API denetim; Karş=paper-paper diff; Etki=230-keyword projeksiyon
- Authoring 4: mock 3'e "Format" eklenir
- Defense 6: mock 4'e "Kaynak Bütünlüğü" + "Tamamlama" eklenir

**Avantaj:** Sidebar değişmez, mevcut plan/UMAPClusterCard/NetworkMapCard zayi olmaz.
**Dezavantaj:** 28 sayfa **şişkinlik riski** — kullanıcı "neden bu kadar sayfa?" sorar; her sayfanın gerçek bir işi olmazsa boş plan'lar üretilir.
**Effort:** 28 plan'a derinlik enjeksiyon (her plan 270 sat hedef) + algoritma/warehouse tablo eşleme.

### Senaryo C — Hibrit (çekirdek+detay)

**Hedef: ~22 sayfa.** Her workbench mock'a yakınlaşır ama 1-2 detay sayfası korunur.

| Workbench | Sayfa | Mantık |
|---|---|---|
| Vitrin | 3 | Aynı |
| Discovery | **3 (mock kanon)** | Keşfet+Nabız+Kavram. Tematik/Konu siliniyor. |
| Curation | **3** | Connected · Havuzum · **Yöntem&Veri detay** (mock'ta yok ama Q3 metod analizine bağlanır) |
| GapAtlas | **3** | Boşluk · RQ&Başlık · **Etki Eğrisi** (deneysel 230-keyword projeksiyon) |
| Authoring | **3 (mock kanon)** | Lit · Bölüm · Üslup. Format siliniyor. |
| Defense | **4 (mock kanon)** | Prova · Hakem · Jüri · Sevkıyat. Format/Bireysel/Kaynak/Tamamlama siliniyor (4'ü "Sevkıyat"a sığar). |
| **TOPLAM** | **19** | |

**Avantaj:** Mock'un sadeliği + sidebar'ın detay esnekliği. UMAP/Tematik gibi gereksizi atar; "Yöntem&Veri" gibi gerçek katma değerli detayları tutar.
**Dezavantaj:** Sidebar revizyonu (-9 sayfa silme + 3 yeni plan); UMAPClusterCard 635 LOC orphan kalır (ya silinir ya başka sayfada reuse).
**Effort:** Senaryo A ile yakın; ama 3 detay sayfası ek plan gerektirir (toplam ~19 plan).

---

## §9 — FELSEFE ÖNERİSİ (kalite kapısı)

### Tek-fiil ilkesi
Her sayfa **1 rol-fiili** ile tanımlı: GÖSTERİR / SEÇER / İŞARETLER / YAZAR / SINAR. Sayfa içeriği bu fiile göre temellenir. Çakışma veya örtüşme = sayfa silinmeli.

### 1 sayfa = 1 ana sinyal grubu
Her sayfa 1 ana hesaplama+çıktı sunar:
- Discovery 1 → t-ESTRA olgunluk + cluster + anchor
- Discovery 2 → Funk-Owen CD + Sleeping Beauty
- Discovery 3 → KeyBERT + NPMI + 11-kategori ontoloji
- Curation 1 → Bibliographic coupling top-50 + ESTRA Pasaport
- Curation 2 → Validator çift mühür + 6-raf rol
- GapAtlas 1 → 8-matris + a-ESTRA×r-ESTRA sweet spot
- GapAtlas 2 → 3-mod RQ + 3 bağımsız özgünlük + 230-keyword title profile
- Authoring 1 → Faithfulness + cümle bazlı paper-zinciri
- Authoring 2 → Rol-aware atıf + RAG
- Authoring 3 → r-ESTRA üslup + sessiz öğrenme
- Defense 1 → Atıfsız iddia tespiti + 30-soru havuzu
- Defense 2 → 3-persona hakem + karar tahmini bandı
- Defense 3 → Çok-ajan jüri + zincir soru
- Defense 4 → Statcheck + dergi eşleme + submission pack

### Vanilla vs imza
**Vitrin = vanilla** (SciSpace mantığı, hesap yok, validator yok, ESTRA yok). **Atölye = imza** (validator çift mühür, ESTRA radar, gap matrix, jüri sim). Vitrin'de derinlik gösterilmez (bilerek); atölyeye geçince *"oh işte fark buradaymış"* açılır.

### Sycophant kilidi (cross-cutting)
LLM atıfsız iddia üretemiyor. Faithfulness skoru < eşik = kırmızı işaret. Pydantic structured output ile `paper_ids` zorunlu (halüsinasyon kapısı). DM-049 doktrini.

### Tier şeffaflığı
Tier matrisi her zaman üstte; kullanıcı 1 üst seviyeye geçince ne açıldığını görür. T0 anonim → T1-T4 girişli (mock); plan: Anon + Pro (DM-046 sade). **Mock T0-T4 ÇOK karmaşık** — DM-046 ile basitleştirildi (Anon + Pro).

---

## §10 — KARAR İHTİYACI

Bu envanter sonrası **3 senaryodan 1'i seçilmeli** ve ardından plan rewrite başlamalı.

**Sorular (kullanıcı kararına bağlı):**
1. **Senaryo A (mock kanon, 19 sayfa) / B (sidebar kanon, 28 sayfa) / C (hibrit, 19 sayfa+3 detay)** hangisi?
2. UMAPClusterCard 635 LOC + NetworkMapCard 773 LOC orphan kalırsa zayi mı (sil) yoksa farklı sayfada reuse mu?
3. Discovery endpoint mimarisi: monolitik `POST /api/discovery/topics` (mock) mı, staged 3-endpoint (mevcut F9 P094-P095-P096) mı?
4. Curation 5 sayfa şişkinliği: Önerilen+İlişkili birleş mi (Senaryo A/C), ayrı tutalım mı (Senaryo B)?
5. Tier modeli: DM-046 Anon+Pro sade (mevcut karar) korunsun mu, yoksa mock T0-T4 5-tier'ı geri gelsin mi?

**Kalite kapısı:** her senaryoda HER sayfa için "tek fiil + tek ana sinyal grubu" kuralı uygulanır. Boş sayfa veya çakışma = silinir. Plan'lar 270 ± 20 sat hedef, format q.md (TASARIM DETAYI/Frontend/Backend/Veri ayrı bölüm).

---

**Bu dosya kanıt envanteridir; karar yoktur.** Kullanıcı senaryo seçtikten sonra `_optimize.md` (veya seçilen senaryo adıyla) ayrı dosyada plan rewrite başlar.

---

## §11 — VİTRİN İÇERİK SABİTLERİ (TASHİH 2026-05-08)

> **Neden burada:** Mock'ta Q1'i "3-paragraf tematik özet (Tema 1/2/3)" olarak yazıldı — **YANLIŞ**. q1.md kanonu okunmadan halüsinasyon yapıldı. Aşağıdakiler `C_vitrin/q.md`, `q1.md`, `q3.md`'den çıkarılan **bağlayıcı içerik kuralları**. Mock'a + her tasarım önerisine bu sabitler uygulanır. Tema/küme/paragraf yapısı **icat edilmez**.

### Q — Hızlı İnceleme
- **Havuz:** 50-paper (TR sorgu: S2 30 + TRDizin 20 · EN/ID: S2 50)
- **Görünüm chip:** `3 / 20 / 50` — Anon: 3 aktif, 20/50 → paywall (DM-052)
- **Card özet dili:** sorgu diline eşit (TR/EN/ID — `langdetect`)
- **CTA:** `Q1 Literatür Özeti` + `Q3 Metod Önerisi` (Q2 ELİMİNE — DM-054)
- **Endpoint:** `POST /api/q/search`

### Q1 — Literatür Özeti
- ❌ **Tema YOK.** "Tema 1 / Tema 2 / Tema 3" başlıkları yasak.
- ✅ **Doğrudan literatür incelemesi** — tek bütün metin, ~400 kelime, sorgu dilinde (TR/EN/ID)
- **K = 12 paper** (final). Rerank: 50-havuz → Aşama 1 (deterministic native skor) top-25 → Aşama 2 (Gemini Flash 2.0) top-12. Kullanıcıya "25 paper analiz edildi, en alakalı 12'sinden özet" mantığı anlatılabilir.
- **Atıf:** her cümle ≥ 1 paper'a dayanır; cümle sonunda `[01]`..`[12]` rank-tag inline (kaynakça gömülü değil — LLM Pydantic structured output ile `CitationMap[]`)
- **Halüsinasyon kapısı:** `citations[i].paper_ids ⊆ used_paper_ids` (sınır dışı rank → reject + 1 retry). Faithfulness verifier VAR (Pydantic gate; "yok" diye yazma).
- **Sol panel:** 3 kart (havuzdan rank 1..3, Q1 ile aynı; hover ↔ sağda `[N]` highlight)
- **Endpoint:** `POST /api/q/literature` (Q1 + Q3 **bağımsız endpoint** — DM-055)
- **Anon:** sağda paywall placeholder + 2 CTA (Deneme Sürecini Başlat / Projeme Dönüştür); sol panel 3 kart yine görünür

### Q3 — Metod Önerisi
- **K = 25 paper** (rerank 50 → 25, Aşama 2 yok — Q1'in aksine).
- **Sağ gövde 3 komponent (Pro):**
  1. **Method Distribution** — 7-tag enum (`experimental_rct` / `observational` / `qualitative` / `mixed_methods` / `systematic_review` / `simulation` / `theoretical`); yüzde + paper_count, 25 paper üzerinde
  2. **2-3 Method Suggestion** — her birinde: method (7-tag), rationale (40-500 char, sorgu dili), `example_paper_id` ⊆ `used_paper_ids`, rank
  3. **Sample Hint** — `typical_sample_size` (serbest metin) + `datasets_or_tools` (2-5 madde)
- **Method classification:** Gemini Flash 2.0 LLM Pass 1 (per-paper 7-tag, cache `q:method_classify:{paper_id}` 30g — Q1+Q3 cross-query reusable). `fact_paper_metod` warehouse tablosu **kullanılmaz** (vitrin Redis-driven, warehouse atölyede).
- **Sol panel:** 3 kart (Q1 ile simetrik)
- **Endpoint:** `POST /api/q/method` (Q1'den **bağımsız** — DM-055)
- **Anon:** Q1 ile aynı paywall davranışı

### Vitrin ortak
- **Vanilla = SciSpace mantığı.** ESTRA, validator çift mühür, gap matrix, jüri sim **YOK** (atölye imzası). Mock metninde bu sinyaller vitrinde geçmez.
- **External:** S2 + TRDizin (TR için). `OpenAlex` vitrinde değil — atölyede.
- **LLM:** Pilot tek model **Gemini Flash 2.0** (Q1 özet, Q3 classification + suggestion). F8 LLMService `vitrin_summary` / `vitrin_method` mode reuse.
- **Cache:** `q:search:{sha256}:{lang}` 1h · `q:literature:{qid}:{tier}` 24h · `q:method:{qid}:{tier}` 24h · `q:method_classify:{paper_id}` 30g · `q:card_summary:{paper_id}:{lang}` 30g
- **Tier:** Anon (T0) vs Pro — DM-046 sade. Mock'taki T0-T4 5-tier eski (envanter §9 not).

**Halüsinasyon disiplini:** Mock'a yeni içerik (bölüm/küme/işaret/sinyal) eklemeden önce `C_vitrin/q.md`/`q1.md`/`q3.md` (vitrin) veya `_atolye_icerik.md` (atölye) okunur. q.md'de yoksa = icat = halüsinasyon = silinir.
