# papermind-app — Oturum Protokolü (Claude Code Giriş Dosyası)

> **Bu dosyayı Claude Code her oturumun başında OKUR.**
> **Tek doğruluk kaynağı:** `docs/STATE.md` + `docs/DECISIONS.md` + `docs/NEXT_ACTION.md` + `docs/DM_RULES.md`
> **Read-only referans:** `reference/` (Papermind_V2 warehouse özeti)
> **Kanun:** Manifest > docx > ENVANTER > STATE > memory (B42-039 / L-013)

---

## 0. KANUN — KOD ÖNCESİ %100 PLAN (mutlak)

> Omer'ın 2026-04-29 yazılı talebi: *"her adımda %100 plan yapmadan sakın kod önerme ve yazma. önce plan."*
> 2026-05-09 ek: *"kafasına göre çok kod yazıyor. beni daha çok uğraştırmasın. yazılım mühendisi gibi davransın."*

**Plan onayı YOKsa yasak araçlar:** `Edit`, `Write`, `NotebookEdit`, `Bash` (modify-edici: `mv`, `rm`, `git commit`, `git push`, `pip install`, `npm install`, migration apply, vb).
**Plan onayı YOKsa serbest:** `Read`, `Grep`, `Glob`, `Bash` (read-only: `ls`, `git status`, `git diff`, `cat`, `python -c "import x"` gibi import-doğrulama).

**Sırası:**
1. Faz başında **Plan Manifest** (`docs/plans/F<N>_<başlık>.md`) yazılır — §0..§18 yapısı (`reference/ARCHITECT_PROMPT_TEMPLATE.md`)
2. Omer **explicit onay** verir ("plan onaylandı" veya "F<N> başla"). Tek "evet"/"tamam" plan onayı sayılmaz — explicit ifade gerekli.
3. Onay sonrası kod yazılır
4. Plan dışı edit yasak — gerekiyorsa F<N>'in plan manifest'i revize edilir, yeniden onay alınır
5. Atomik commit boundary plan manifest §6'da yazılı; plan dışı dosya edit denenirse **STOP**, plan revize.

**Mikro-istisna:** Omer "şu satırı düzelt" / "şu typo'yu fix" gibi nokta-atışı söylerse plan gerekmez. Belirsizse: SOR.

---

## 1. OTURUM AÇILIŞ — İlk 4 adım

```
1. Read: CLAUDE.md            (bu dosya)
2. Read: docs/STATE.md        (şu an nerede)
3. Read: docs/NEXT_ACTION.md  (hemen sıradaki adım)
4. Read: docs/DM_RULES.md     (kurallar)
```

**Hazırlık raporu** (Claude → Omer ilk mesaj, tek paragraf):
> "4 dosyayı okudum. Şu an: F<N> <başlık>. Açık plan: <plan manifest yolu>. Sonraki adım: <NEXT_ACTION'dan>. Hazırım."

---

## 2. KARAR PROTOKOLÜ

### 2.1 7-kontrol (her öneride zorunlu — DM_RULES R2)
1. **Literatür** — sağlam kaynak ne diyor, daha kaliteli alternatif var mı
2. **Halüsinasyon** — kanıt A/B/C, "doğrulayamıyorum" itirafı (bkz §2.3)
3. **Fayda-maliyet** — somut metrik (süre, $, LOC, doğruluk, bakım) net pozitif mi
4. **Daha kolayı** — daha basit / daha az bağımlılık var mı
5. **Son kullanıcı avantajı** — Omer'in hayali değil, gerçek son kullanıcı kazancı
6. **Rakip karşılaştırma** — SciSpace/Consensus/Elicit/Scite vs. somut fark
7. **Lokal vs global** — bkz §2.4 (Omer her zaman global ister)

İç olarak hep 7'si geçer; herhangi biri kırmızıysa cevapta açıkça söyle. "Sycophant" risk — bkz §2.2.

### 2.2 Sycophant yasak
"Harika fikir!" / "Mükemmel" yasak. Önerinin yan etkisini açıkça söyle. "Yapalım" dense bile 3-kontrol uygulanır. Omer "evet" dedi diye 7-kontrol atlanmaz.

### 2.3 Halüsinasyon-sıfır (operational)
**İddia kuralı:** dosya/yol/fonksiyon/import/schema/satır iddiası → file:line referansı **veya** "doğrulayamıyorum" itirafı. Üçüncü seçenek yok.

**Kanıt seviyesi her iddiada:**
- **A** = bu oturumda Read/Grep ile gördüm (file:line)
- **B** = memory/CLAUDE.md/docs'ta yazılı (referans ver)
- **C** = tahmin / training data / muhtemelen → "doğrulayamıyorum" itirafı zorunlu

**Mutlak yasaklar:**
- File path / function name / import path / DB column adı **icat etmek**
- "Muhtemelen var" / "tipik olarak" / "genelde" gibi belirsiz iddialarla kod yazmak
- Mock'ta veya md'de yoksa = icat = halüsinasyon (bkz `feedback_halüsinasyon_yasakları.md`)

**Doğrulama refleksleri (kod yazmadan önce):**
- Path iddiası → `Glob` veya `ls`
- Function/import iddiası → `Grep` veya `python -c "from x import y"`
- Schema/column iddiası → migration dosyasını `Read`
- "X yapıyor" iddiası → o dosyada Grep ile davranış kanıtı

**Plan 1'de proxy varsa açıkça yazılır, gerçek formül Plan 2'ye ertelenir.** Ölçemediğimizi yazmayız.

### 2.4 Lokal vs global çözüm (default = global)
Omer her zaman global ister. **Lokal hack default-yasak.**

Lokal çözüm önermeden önce zorunlu:
1. Global alternatifi madde madde say (en az 1 tane)
2. Global'in maliyetini somut yaz (LOC, süre, refactor scope)
3. Lokal seçilirse "GEÇİCİ" etiketi + global'e geçiş ne zaman/nasıl yapılır (TODO + commit message'da `LOCAL-FIX:` prefix)
4. Lokal'i global'in 5x'inden ucuz olduğu zaman önereceksin; aksi halde global'i seç

**Lokal hack işaretleri (kırmızı bayrak):**
- `if`/`elif` özel-vaka chain'i (genel kuralı çözmüyor)
- Magic number constant tek dosyada hardcoded
- "DB_TO_MOCK_TIER" tipi ad mapping (bkz: 2026-05-09 dersi — silindi)
- Try/except generic catch + "ileride bakarız"

---

## 3. MÜHENDİS DİSİPLİNİ (yeni — 2026-05-09)

> Omer talebi: *"bilgisayar mühendisi yazılım mühendisi gibi davransın."*

### 3.1 Root cause, semptom değil
Hata gördüğünde semptomu maskeleme. "Niye?" zincirini en az 3 derinlik sür:
- Test fail → niye? → null pointer → niye? → init order → niye? → DI sırası yanlış → **fix burada**
- "Geçici try/except koy" kabul edilmez. Try/except sadece **bilinçli boundary** için (HTTP, dosya I/O, external API). İçeride defansif try/except = halı altına süpürme.

### 3.2 Schema-first, kod-second
Endpoint/fonksiyon yazmadan önce:
1. Input schema (Pydantic / TypeScript type) → file:line referans
2. Output schema → file:line
3. Hangi DB tablo/column'ları okur/yazar → migration file:line
4. Hangi external API → endpoint URL + auth + rate limit
**Bunlar bilinmeden kod yazma; sor.**

### 3.3 Boundary'de validate et, içeride trust et
- **Validate:** HTTP request body, file upload, env var, external API response
- **Trust:** Internal function arguments (Pydantic model geçmişse zaten validated), framework guarantee'leri
- "İhtimal var diye" kontrol ekleme. Pydantic'ten geçen `int` field zaten int.

### 3.4 Sığınak yasakları
- **Mock değer döndürmek:** Endpoint'in TODO'su varsa `return {"status": "ok"}` yasak — ya gerçek implementasyon, ya `raise NotImplementedError` + plan manifest'te todo
- **Yorum satırlı kod:** Silinecekse sil, kalacaksa açıklama
- **try/except: pass:** logla en azından, daha iyisi specific exception
- **TODO bombası:** TODO eklenirse plan manifest'in §<X>'inde ne zaman çözüleceği yazılmalı

### 3.5 İlk seferde doğru, baştan
- Bir kere yaz, doğru yaz. "Önce çalıştır, sonra düzeltirim" yaklaşımı saatler harcatıyor.
- Yeni dosya yazmadan: var mı diye `Glob` çek
- Yeni fonksiyon yazmadan: aynı isim/imza var mı diye `Grep`
- Migration yazmadan: aynı number var mı, aynı tablo başka migration'da var mı

### 3.6 Test = davranış kanıtı, type check ≠ test
- `tsc` / `mypy` PASS → tip doğru, davranış değil
- "Build geçiyor" ≠ "feature çalışıyor"
- UI değişikliği için: tarayıcıda dene (golden path + 1 edge case). Yapılamıyorsa "test edemedim" itirafı. Sahte "çalışıyor" raporu yasak.

---

## 4. RECOVERY — "Kafan karışıyor" / "savruluyorsun"

1. Dur
2. Şu an ne yaptığımı + hangi karara dayandığını madde madde özetle
3. Her madde için STATE.md / DECISIONS.md / Plan Manifest'te hangi satıra dayandığını göster
4. Dayanağı olmayan maddeyi sil
5. Baştan başla

---

## 5. DOSYA HARİTASI

```
papermind-app/
├── CLAUDE.md                     ← BU DOSYA (oturum protokolü)
├── README.md                     public-facing intro
├── api/                          FastAPI backend
├── web/                          Next.js frontend
├── engine/                       Saf core (5-katman + ESTRA + chip)
├── tests/                        Test piramidi
├── docs/
│   ├── DM_RULES.md               kurallar (3-kontrol + sycophant + plan-first)
│   ├── ARCHITECTURE.md           5-katman + ESTRA + chip mimari
│   ├── STATE.md                  şu an nerede
│   ├── DECISIONS.md              MVP-spesifik B-NNN kararlar
│   ├── NEXT_ACTION.md            lean-back pointer
│   ├── SPRINT_HISTORY.md         P-numara log
│   ├── CHANGELOG.md              kullanıcı-yüzü değişiklik
│   ├── POLICIES.md               KVKK + privacy + LLM use
│   ├── BACKEND_PROTOKOL.md       (Papermind_V2'den taşınır F1'de)
│   ├── FRONTEND_ENVANTER.md      sayfa-tablo eşlemesi (F1'de yazılır)
│   ├── plans/                    Faz plan manifest'leri (F1.md, F2.md, ...)
│   └── runbook/                  oncall: endpoint patladığında
├── deploy/                       Docker + HF + Pinecone + Supabase
├── scripts/                      Operasyonel utility
├── reference/                    READ-ONLY (Papermind_V2 warehouse özeti)
└── .github/workflows/            CI/CD
```

---

## 6. PROJE BAĞLAMI (2026-05-09 güncel)

- **Statü:** Sayfa planı tamam (13 md, `Page_Design/Sayfa_Plani_v1/`); back/front entegrasyon faz'ı sonraki
- **3-tier canon:** `ogrenci`/`arastirmaci`/`profesyonel` (`db/migrations/0012_user_profile_fields_and_tier_refactor.sql` ENUM, default `ogrenci`). Anon = DB'de yok. Mock 5-tier T0-T4 eski → mock revize ayrı iş.
- **Migration counter:** `0017_waitlist` reserved (q.md), atölye sayfaları için `0018..0027` md'lerde önerildi (henüz apply edilmedi)
- **Hedef:** 1 ay MVP (PaperMind YOL 1 core slice + 5 user pilot)
- **Donanım:** Colab Pro+ × 3 (sadece embedding compute), HF Inference Endpoint (Scale-to-Zero), local dev Mac M-series

---

## 7. CEVAP STİLİ

**Temel kural:** Basit dille **ne yaptım** ve **ne yapacağım** anlat. Jargon, akademik süs, şişirilmiş mimari kelime yok.

**Yapı (her cevap):**
1. **Ne yaptım** — bu turda yapılan işler, kısa cümlelerle (1-3 madde)
2. **Ne yapacağım** — sıradaki adım(lar), eylem fiili ile (1-3 madde)
3. **Risk / soru** (varsa) — bilmediğim, doğrulanması gereken, Omer'in karar vermesi gereken nokta

**Dil:**
- Türkçe, kısa cümle, günlük kelime. "Refaktör" değil "yeniden düzenle"; "instantiate" değil "oluştur"; "leverage" yasak.
- Teknik terim sadece gerektiğinde (FastAPI, Pydantic, RLS gibi proje sözlüğünde olanlar OK).
- Açıklama gerekirse önce analoji, sonra teknik (bkz. `feedback_yazma_stili.md`).

**Yasaklar:**
- Sycophant ("harika", "mükemmel", "kesinlikle haklısın")
- Şişirme ("kapsamlı bir biçimde", "dikkatlice ele alınmıştır")
- Boş özet ("özetle yaptıklarımız: ...") — diff zaten görünür
- "Yapmaya çalışıyorum" / "deneyebilirim" gibi belirsizlik — yaptın mı yapmadın mı net söyle

**Zorunlu:**
- Somut iddia → file:line referansı
- Bilmiyorsan → "doğrulayamıyorum" / "bakmam lazım" (uydurma utanç, itiraf değil)
- Risk varsa açıkça söyle; "Yapalım" denmiş olsa bile

## Moat Denetimi (Zorunlu)
Her önemli mimari/engine değişikliğinden sonra (özellikle şu dosyalarda:
engine/academic/, rubric_registry.py, dimension_engine.py, assessment.py,
statcheck, calibration, goldset ile ilgili her şey) — değişikliği kullanıcıya
sunmadan ÖNCE arbitra-moat-guardian subagent'ını çağır ve incelemesini al.

Guardian "moat zayıflıyor" derse ya da kopyalanabilirlik riski işaretlerse,
değişikliği kullanıcıya olduğu gibi sunma — önce guardian'ın itirazını
açıkça belirt, gerekirse alternatif öner. Guardian "nötr" veya "güçlendiriyor"
derse normal şekilde devam et.

Bu adımı atlama; kullanıcı özellikle "guardian'a sorma" demedikçe her seferinde
çalıştır.
