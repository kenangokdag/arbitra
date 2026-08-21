# Goldset Genişletme — Yeni Aday Kaynaklar (2026-08-13 araştırması)

**Amaç:** Guardian'ın §42'de belirttiği gibi held-out doğrulama, moat-n büyütme ve boyut-korelasyon analizi FARKLI 3 örneklem ihtiyacı — muhtemelen tek bir kaynak üçünü birden çözmüyor. Bu doküman WebSearch ile araştırılmış, gerçek/doğrulanmış adayları listeler (uydurulmamış — her biri kaynak linkiyle).

**3 ayrı ihtiyaç:**
1. **Held-out/verdict çeşitliliği** — major_revision/minor_revision örneği (şu an goldset'te major_revision=2, minor_revision=0/61).
2. **Moat-n büyütme** — gerçek fabricated/retracted atıflı makale (nadir, kimse etiketlemiyor).
3. **Boyut-korelasyon analizi için n büyütme** — sayısal per-boyut insan skoru olan, restricted-range OLMAYAN (hem accept hem reject/revize dahil) örneklem.

---

## Aday 1: NLPeer (UKPLab / TU Darmstadt) — İNCELENDİ (2026-08-13), ERİŞİM ENGELLİ

**GitHub reposu klonlanıp kod incelendi** (`src/nlpeer/__init__.py`) — asıl VERİ ayrı barındırılıyor, repo sadece kod.

**Somut bulgu:** F1000 alt-veri-seti NLPeer içinde VAR, skor şeması kodda tanımlı: `approve=2, approve-with-reservations=1, reject=0` — İHTİYAÇ 1'i (3 kademeli karar çeşitliliği) çözecek yapı hazır. PLOS/eLife'ın skor şeması kodda HENÜZ tanımlı değil (`DATASET_REVIEW_OVERALL_SCALES` dict'inde yok) — eksik/hazırlanmamış olabilir.

**Erişim engeli (kritik):**
- TU Darmstadt veri deposu (`tudatalib.ulb.tu-darmstadt.de`) erişimi **kısıtlı** — "request-a-copy" süreci gerekiyor, doğrudan indirme YOK. Kullanıcının (Kenan'ın) gerçek kimliği/kurumsal bağlantısıyla talep göndermesi gerekiyor.
- **Lisans: CC BY-NC 4.0 (ticari olmayan kullanım şartı)** — Arbitra ticari bir ürünse bu bir hukuki/iş kararı, AI tarafından karar verilemez.
- Dosyalar büyük (ELIFE 30GB, ARR-EMNLP-24 11GB, PLOS 2.77GB, EMNLP23 3.56GB).

**Durum: DİSKALİFİYE (2026-08-13, kullanıcı teyidi).** Arbitra ticari bir ürün — CC BY-NC 4.0'ın "ticari olmayan kullanım" şartı, bu veriyi bir ticari ürünün kalibrasyon/goldset sürecinde kullanmayı engelliyor. Talep-onay sürecine bile girilmeyecek. Bu adayla devam EDİLMİYOR.

- **Kaynak:** [GitHub — UKPLab/nlpeer](https://github.com/UKPLab/nlpeer), makale: [arXiv:2211.06651](https://arxiv.org/pdf/2211.06651)
- **İçerik:** >5k makale, 11k review raporu, **5 farklı venue**: ARR-EMNLP-2024, EMNLP-2023 (NLP), **PLOS (2019-2024)**, **ELIFE (2023-2024)** (çok-disiplinli, kamu verisi).
- **Format:** PDF dosyaları + GROBID TEI + Docling JSON + review metinleri (reviews.json) + "scores" nesnesi (scoreX/scoreY/overall alanları — TAM İÇERİĞİ İNDİRİLMEDEN DOĞRULANAMADI).
- **Lisans:** Apache-2.0 (açık).
- **Neyi çözüyor:** PLOS/eLife çok-disiplinli (biyoloji/yaşam bilimleri ağırlıklı ama nicel araştırma metodolojisi içeriyor) — gerçek PDF + gerçek review + muhtemelen revizyon-döngüsü verisi. **İhtiyaç 2 ve 3'ü kısmen çözebilir**, ihtiyaç 1 (major/minor revision) PLOS/eLife'ın editoryal karar yapısına bağlı — DOĞRULANMADI, indirilip incelenmeli.
- **Risk:** Skor alanlarının (scoreX/scoreY) hangi kritere karşılık geldiği dokümantasyonda net değil — indirilmeden emin olunamaz.

## Aday 2: berenslab/iclr-dataset — BÜYÜK ÖLÇEK, METADATA-ONLY

- **Kaynak:** [GitHub — berenslab/iclr-dataset](https://github.com/berenslab/iclr-dataset)
- **İçerik:** ICLR'nin OpenReview'daki TÜM submission'larının tam taraması — **55.906 submission, 2017-2026** (ICLR 2025 dahil, Mayıs 2025'te eklendi). Karar (accept/reject) + reviewer skorları + yazar/başlık/özet.
- **Format:** Parquet dosyaları (`iclr24v2.parquet` gibi), MIT lisans.
- **Neyi çözüyor:** Mevcut PeerRead-2017 örneklemini büyük ölçüde genişletebilir — **ihtiyaç 3'ü** (n büyütme, reddedilen makale çeşitliliği) güçlü şekilde çözer, OpenReview'ın önceden karşılaşılan bot-korumalı arama API'sini (403 ChallengeRequiredError) bypass ediyor çünkü ÖNCEDEN scrape edilmiş.
- **Kritik sınır:** **SADECE METADATA — PDF/tam metin YOK.** Gerçek makale PDF'i ayrıca (muhtemelen `openreview.net/pdf?id={forum_id}` deseniyle) çekilmeli — bunun bot-korumasından etkilenip etkilenmediği TEST EDİLMEDİ, doğrulanmamış varsayım.
- **İhtiyaç 1'i (major/minor revision) ÇÖZMÜYOR** — ICLR'de bu karar kademesi hiç yok (journal §26'da zaten teyit edilmiş bir sınır).

## Aday 3: Retraction Watch veritabanı + OpenAlex atıf-grafiği — TEST EDİLDİ, ÇALIŞIYOR (2026-08-13)

- **Kaynak:** [Crossref Labs — Retraction Watch](https://www.crossref.org/labs/retraction-watch/), API: `https://api.labs.crossref.org/data/retractionwatch?<mailto>`
- **Gerçekten indirildi ve test edildi** (bu oturumda) — canlı API'den 9167 kayıtlık kısmi bir dilim çekildi (tam veri seti ~50k, 60s zaman aşımıyla kesildi, tamamı için daha uzun timeout yeterli). Gerçek alanlar doğrulandı: `Reason` (kategorize edilmiş geri çekilme sebebi), `OriginalPaperDOI` (%99.99 dolu), `Subject`, `Paywalled`.
- **Doğrudan ilgili bulgu:** "Concerns/Issues about Referencing/Attributions" — **4243 kayıt** (`citation_integrity` ile doğrudan örtüşüyor). Computer Science (2039) + Data Science (1968) + Technology (2163) en yaygın konular arasında — mevcut goldset'in (ML/CS ağırlıklı) alanıyla örtüşüyor.
- **Kritik sorunun ÇÖZÜMÜ bulundu ve DOĞRULANDI (uçtan uca):** Veritabanı geri çekilen makalenin KENDİSİNİ listeliyor, ona atıf yapan başka makaleleri değil — ama **Arbitra'nın zaten kullandığı OpenAlex atıf-grafiği ile bu boşluk kapatılabiliyor.** Test edilen zincir:
  1. Retraction Watch'tan gerçek bir "Rogue Editor" vakası (`10.1007/s00500-021-06562-y`) alındı.
  2. OpenAlex'te bu DOI GERÇEKTEN `"RETRACTED ARTICLE:"` başlığıyla ve retraction meta-verisiyle indeksli çıktı.
  3. `GET /works?filter=cites:{openalex_id}` ile bu geri çekilmiş kaynağa **hâlâ dolaşımda olan 4 gerçek makale** (2023-2024 tarihli, geri çekilmemiş) atıf yapıyor bulundu.
  4. **3/4'ünün doğrudan açık-erişim PDF URL'i var** (MDPI, IEEE, ETASR) — `open_access.oa_url` alanında.
  5. **Ölçek testi:** 2889 CS/Data-Science + gerçek-DOI'li aday DOI'den rastgele 30'u örneklendi — 28/30'unun (%93) en az 1 atıf-yapan makalesi var, toplamda **100 açık-erişimli, geri çekilmemiş atıf-yapan makale** bulundu (sadece 30 tohumdan).
- **Sonuç:** Bu, guardian'ın §42'de koşullu onayladığı sentetik/adversarial veriden DAHA İYİ — **%100 gerçek, doğrulanmış ground truth**, sentetik veri riski (kolay yakalanabilirlik, moat_grounding_accuracy'nin dairesel olma riski) yok. Ölçek yeterli (mevcut n=4'ü onlarca kata çıkarabilir).
- **Kalan iş (uygulama, henüz yapılmadı):** Adayları PDF indirip Arbitra'nın `GoldEntry` formatına dönüştürmek — bu ayrı bir uygulama adımı, kullanıcı onayı bekliyor.

## Aday 4: MOPRD — Çok-disiplinli, revizyon-döngüsü verisi VAR

- **Kaynak:** [arXiv:2212.04972](https://arxiv.org/pdf/2212.04972)
- **İçerik:** "paper metadata, multiple version manuscripts, review comments, meta-reviews, author's rebuttal letters, ve editorial decisions" — **çoklu-versiyon manuscript + revizyon döngüsü** açıkça var.
- **Neyi çözüyor:** İhtiyaç 1 (major/minor revision benzeri karar çeşitliliği) için EN UMUT VERİCİ aday — ama tam karar kategorileri (accept/major/minor/reject mi, yoksa farklı bir taksonomi mi) web araştırmasıyla DOĞRULANAMADI, indirilip makalenin kendisi okunmalı.
- **Risk:** Erişim/indirme detayları web aramasında net çıkmadı, doğrudan makaleye gidilip incelenmesi gerekiyor.

## Aday 5: F1000Research / FMMD — YENİ (2026), muhtemelen henüz olgun değil

- **Kaynak:** [arXiv:2602.14285](https://arxiv.org/abs/2602.14285) ("work in progress" olarak işaretli)
- **İçerik:** F1000Research'in açık hakemlik modeli — reviewer kararı **Approve / Approve with Reservations / Not Approved** (accept/minor-revision-benzeri/reject'e kabaca karşılık gelebilir), gerçek revizyon döngüleri (yazar tam noktasal cevap yazıyor, yeni versiyon aynı hakemlerce tekrar inceleniyor).
- **Risk:** Makale "work in progress" — indirme linki bulunamadı, veri seti henüz kamuya açık olmayabilir. Düşük öncelik, takip edilmeli.

---

## Öneri (2026-08-13 güncellemesi — 2 aday gerçekten test edildi)

**Durum netleşti:**
1. **NLPeer: DİSKALİFİYE** (CC BY-NC 4.0, Arbitra ticari ürün — kullanıcı teyit etti).
2. **Retraction Watch + OpenAlex atıf-grafiği: DOĞRULANDI, ÇALIŞIYOR** — İHTİYAÇ 2'yi (moat-n büyütme) uçtan uca test edilmiş, gerçek veriyle kanıtlanmış bir yöntemle çözüyor. **Önerilen sıradaki somut adım: bu yöntemle 20-30 gerçek aday makaleyi (PDF indir + GoldEntry formatına çevir) üretmek.**
3. **berenslab/iclr-dataset**: İHTİYAÇ 3 (n büyütme) için hâlâ geçerli ikincil aday — PDF erişimi henüz test edilmedi, İHTİYAÇ 1'i çözmüyor.
4. **MOPRD**: İHTİYAÇ 1 (major/minor revision çeşitliliği) için hâlâ en umut verici ama test edilmedi.
5. **FMMD**: düşük öncelik, takipte.

**Kalan açık ihtiyaç:** İHTİYAÇ 1 (held-out için major_revision/minor_revision çeşitliliği) hâlâ çözülmedi — Retraction Watch bunu çözmüyor (o sadece moat-n). MOPRD veya berenslab/iclr-dataset + F1000 (NLPeer dışında, doğrudan F1000Research API'sinden) ayrıca araştırılmalı.
4. **MOPRD'yi oku** (makalenin kendisi) — İHTİYAÇ 1 için en güçlü aday görünüyor ama detaylar doğrulanmadı.
5. FMMD'yi düşük öncelikli izlemede tut (muhtemelen henüz kullanılamaz durumda).

**Hiçbiri "hazır, hemen entegre et" durumunda değil** — hepsi indirme + elle inceleme + goldset.json'a uygun `GoldEntry` formatına dönüştürme gerektiriyor (tıpkı PeerRead'in journal §26'daki entegrasyonu gibi). Bu, ayrı bir uygulama adımı, kullanıcı kararı bekliyor: hangi aday(lar)la devam edelim?

**Kaynaklar:**
- [NLPeer GitHub](https://github.com/UKPLab/nlpeer) · [NLPeer arXiv](https://arxiv.org/pdf/2211.06651)
- [berenslab/iclr-dataset](https://github.com/berenslab/iclr-dataset)
- [Retraction Watch / Crossref Labs](https://www.crossref.org/labs/retraction-watch/)
- [MOPRD arXiv](https://arxiv.org/pdf/2212.04972)
- [FMMD arXiv](https://arxiv.org/abs/2602.14285)
- [PeerRead (mevcut kaynağımız, karşılaştırma için)](https://arxiv.org/abs/1804.09635)
