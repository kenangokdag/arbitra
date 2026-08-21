# Araştırma: Revize makale tekrar yüklendiğinde versiyon karşılaştırma/zaman çizelgesi

**Tarih:** 2026-08-16
**Durum:** ARAŞTIRMA — bu bir uygulama planı DEĞİL, kapsam netleştirmesi. Kenan'ın kapsam kararı bekleniyor (§4).
**Kaynak:** Kenan'ın bu oturumdaki isteği — "revize makale tekrar yüklenirse, neyin değiştiğini ve hangi bulguların kapandığını gösteren bir görünüm."

---

## 1. Soru: versiyon takibi zaten var mı? — HAYIR (kanıtlı, A-seviye)

**`review_job` tablosu tamamen düz, hiçbir versiyon/lineage kolonu yok.** İncelenen: `db/migrations/0041_review_domain.sql` (tablo tanımı) + `0042_review_worldclass_v2.sql` (v2 additive kolonlar: `lifecycle`, `stages`, `privacy`, `idempotency_key`, `classification`, `schema_version`). Hiçbirinde `parent_job_id`, `manuscript_hash`, `previous_version` gibi bir alan YOK.

**`idempotency_key` bunun için DEĞİL** — `review_service.py:272-287` — aynı (user_id, key) ile GELEN AYNI isteğin çift dispatch edilmesini önlüyor (aynı istek iki kez gönderilirse aynı job_id döner). Bu, "revize versiyon önceki versiyona bağlansın" ile TAMAMEN farklı bir problem (dedup vs. lineage).

**Kullanıcı-yüzü bir "geçmiş işlerim" listesi de YOK.** `api/routes/review.py:218`'deki tek liste `admin_list_jobs()` — SADECE admin. `web/src/app/(app)/review/page.tsx` tamamen stateless: yükle → `/review/{job_id}`'ye yönlen → bitti. Kullanıcı kendi önceki job'larını GÖREMİYOR, seçemiyor. Bu, versiyon karşılaştırmadan ÖNCE çözülmesi gereken bir ön-koşul: kullanıcının "bu, önceki makalemin devamı" diyebileceği bir yüzey yok.

**Sonuç: Bu özellik, mevcut yapıyla ÇÖZÜLEMEZ — yeni bir veri modeli (en az 1 kolon) VE yeni bir kullanıcı-yüzü (en az 1 sayfa/liste) gerektiriyor.**

## 2. Kapsamın gerçek boyutu — parçalara ayrılmış tahmin

| Parça | Boyut | Neden |
|---|---|---|
| DB: `parent_job_id uuid` nullable FK kolonu | **Küçük** | 0042'nin additive-önce deseniyle BİREBİR aynı (nullable, default yok, mevcut satırlar bozulmaz) — yeni bir migration, tek kolon. |
| "Neyin değiştiği" özeti (verdict/hazırlık puanı/boyut skorları deltası) | **Küçük** | İki `ReviewReport` JSON'unu üst-seviyede diff'lemek — tamamen deterministik, LLM YOK, guardian GEREKMİYOR (bu oturumdaki DOCX/öncelik-listesi gibi saf sunum işi). |
| "Hangi bulgular kapandı" eşleştirmesi | **Orta-büyük** | **Kritik engel:** `Finding.finding_id` iki AYRI motor koşumu arasında STABİL DEĞİL — `_engine_base.py:260` (`fid = f"{id_prefix}.f{i}"`) sırayla/index'e göre üretiliyor, içerik-hash'i ya da kalıcı kimlik DEĞİL. Yani v1'deki "F-003" ile v2'deki "F-003" AYNI bulgu OLMAK ZORUNDA DEĞİL. "Kapandı" demek için `dimension`+`title`/`summary` benzerliğine dayalı BULANIK eşleştirme gerekiyor — bu bir tasarım kararı (string benzerliği mi, embedding mi, anchor section eşleşmesi mi), basit bir plumbing işi DEĞİL. |
| Kullanıcının "bu revize versiyon" diyebileceği yüzey | **Orta** | Şu an HİÇ yok. En az: upload akışına "önceki bir versiyonu var mı?" adımı VEYA otomatik title-benzerliği önerisi + kullanıcı onayı (yanlış eşleştirme riski var, sessiz otomatik bağlama GÜVENLİ DEĞİL). |
| Rapor sayfasında karşılaştırma/zaman çizelgesi görünümü | **Orta** | Yeni component(ler) — ama mevcut `ReviewReportView.tsx` desenleriyle (RiskBadge, SEVERITY_RANK, vb.) tutarlı yazılabilir. |

**Dürüst genel değerlendirme:** Bu, bugüne kadarki 5 maddeden (hepsi: mevcut veriyi yeniden düzenleme, sıfır/minimal backend, sıfır yeni DB şeması) FARKLI bir risk/boyut sınıfında — yeni migration + yeni kullanıcı-yüzü + gerçek bir eşleştirme-algoritması tasarım kararı gerektiriyor.

## 3. "Kapandı" iddiasının dürüstlük riski (CLAUDE.md "yok ≠ uydurma" ile aynı hassasiyet sınıfı)

Bulanık eşleştirme YANLIŞ "kapandı" diyebilir (örn. v1'deki bir soundness bulgusu ile v2'deki BAŞKA bir soundness bulgusu benzer başlıklı ama aslında farklı bir sorun — biri "kapandı" biri "yeni" sanılabilir). Bu, kullanıcıya YANLIŞ bir güven verebilir ("düzelttim" sanıp aslında düzeltmemiş olabilir). İlk sürüm bunu YÜKSEK GÜVEN iddiası olarak SUNMAMALI — "muhtemelen aynı konu" gibi dürüst bir çerçeve, ya da başta SADECE deterministik özet (verdict/skor deltası — §2'nin küçük parçası) ile başlayıp, bulgu-eşleştirmeyi (§2'nin orta-büyük parçası) ayrı, daha dikkatli bir adıma bırakmak daha güvenli.

## 4. Önerilen kademelendirme — Kenan'ın kararı gerekiyor

**Faz 1 (küçük, bugün mümkün, guardian gerekmiyor):**
- DB: `parent_job_id` kolonu.
- Upload akışına BASİT bir bağlama: kullanıcı yeni yüklerken "bu, önceki bir işimin devamı" checkbox'ı + son N job'ından (yeni, küçük bir liste endpoint'i — sadece kendi job'ları, admin değil) seçim. Otomatik/sessiz eşleştirme YOK — kullanıcı KENDİSİ seçer, yanlış-bağlama riski ortadan kalkar.
- Rapor sayfasında SADECE deterministik özet: verdict değişti mi, hazırlık puanı deltası, boyut skorları deltası (tablo). Bulgu-eşleştirme YOK.

**Faz 2 (orta-büyük, ayrı oturum, muhtemelen guardian):**
- "Hangi bulgular kapandı/yeni/devam ediyor" bulanık eşleştirmesi — eşleştirme algoritması tasarımı + dürüstlük/güven çerçevesi (§3) ayrıca ele alınmalı.
- Otomatik title-benzerliği önerisi (kullanıcı deneyimini kolaylaştırır ama yanlış-eşleştirme riskini yönetmek gerekir).

## 5. Kapsam dışı (her iki faz için de)

1. Geçmiş (bu özellik öncesi yüklenmiş) job'ların geriye dönük birbirine bağlanması — sadece BUNDAN SONRAKİ yüklemeler için `parent_job_id` set edilebilir.
2. 30 günlük retention (`delete_after`, migration 0044) ile çakışma — eski versiyon silinmişse karşılaştırma yapılamaz, bu bir KVKK/veri-saklama kararı, bu planın kapsamı dışında ama not düşülüyor.
