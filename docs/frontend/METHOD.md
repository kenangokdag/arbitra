# METHOD.md — Frontend Planlama Yöntemi

> **Amaç:** Frontend sayfaları tasarlanırken HANGİ felsefe + HANGİ şablon + HANGİ kısıtlarla çalışacağımızı sabitler. Spesifik sayfa listesini DEĞİL, **nasıl yapacağımızı** belirler.
> **Statü:** v0.1 draft — §1 Mekan Modeli onayı bekliyor. Onaysız §3 şablonu uygulanmaz.
> **Ne zaman okunur:** Frontend planlama (F1) başladığında **ilk açılan dosya**.

---

## §1 — Akademik Mekanlar Modeli (felsefe)

PaperMind'de kullanıcı bir **akademik hayat simülasyonu** içinde gezer. Her mekan = bir akademik aşama. Mekan metaforu **isim + ikon + ses tonu**dur — UI modern + temiz kalır.

### MVP — 3 mekan (PaperMind YOL 1)
- **Kütüphane** — literatür arama + kütüphaneci yardımı
- **Çalışma Masası** — paper detay + kişisel okuma
- **Konu Atölyesi** — tema deep-dive + okuma önerisi

### Roadmap büyümesi (kapsam dışı, sadece bağlam)
- AdvisorMind (YOL 2): + Danışman Odası, Savunma Salonu
- JuryMind (YOL 3): + Jüri Odası, Hakemlik Odası

**Kural:** Mekanlar geri uyumlu büyür. Eski mekanlara dokunulmaz, yeni eklenir.

---

## §2 — Skeuomorphism Yasağı (sıkı)

- Literal "3D ahşap kütüphane" / "fiziksel oda animasyonu" / "ahşap masa render" **YASAK**
- Mekan metaforu sadece: **isim + tek-ikon + microcopy ses tonu**
- İçeride UI: Linear / Notion / Figma seviyesi modern + minimal
- Renk + tipografi: `design_system.md`'de tanımlanır (sonraki iş)

---

## §3 — Sayfa Şablonu — 11 Madde (her sayfa için zorunlu)

Her sayfa .md dosyası şu 11 maddeyi sırayla cevaplar:

1. **Felsefe** — bu sayfa neden var (1 paragraf)
2. **Çözdüğü kullanıcı problemi** — 1 cümle
3. **Ne gösterir** — envanterden çekilen veri item'ları
4. **Ne yapabilir** — kullanıcı aksiyonları
5. **Rakip karşılaştırma** — SciSpace + Consensus + Elicit + Scite + bizim somut farkımız (K6)
6. **UX kuralı** — P1 karar bandı + chip + gate + dil + mekan ses tonu
7. **Boş / yükleniyor / hata** durumları
8. **Mobil davranış** — responsive kuralı
9. **Erişilebilirlik** — WCAG AA minimum
10. **Bu sayfada YAPMAYACAĞIZ** — sycophant kalkanı
11. **Backend gereksinimi** — endpoint + alan + cache

**Kural:** Bu 11 madde sabit. Eklemek/çıkarmak için METHOD.md revize edilir + Omer onayı.

---

## §4 — Mekan-Backend Bağımsızlığı

- Backend **mekan metaforunu bilmez**. Endpoint isimleri **nötr**: `/api/search`, `/api/chat`, `/api/summarize`.
- Frontend mekanı backend cevabına bind eder, **tersi yok**.
- Backend refactor → frontend mekanı etkilemez (gevşek bağ).
- Bir endpoint birden fazla mekana hizmet edebilir; bir mekan birden fazla endpoint çağırabilir.

---

## §5 — 7-Kontrol Sayfa İçin Özel Vurgu

Sayfa şablonu yazılırken K-soruların önceliği:

| K | Sayfa için ne demek |
|---|---|
| **K6 (Rakip)** | §3 madde 5 zorunlu — "biz onlardan nerede daha iyiyiz" cevapsız sayfa onaya gitmez |
| **K5 (Son kullanıcı)** | §3 madde 1+2+10 burada kontrol edilir |
| **K4 (Daha kolayı)** | Modal/state vs ayrı route kararı her sayfada gözden geçirilir |
| **K7 (Lokal vs global)** | Sayfa TR'ye spesifik bir hack içeriyorsa açıkça işaretlenir, global karşılığı yazılır |
| **K2 (Halüsinasyon)** | §3 madde 11 backend alan adı uydurmadan, ARCHITECTURE.md veya Plan Manifest'ten alınır |

---

## §6 — Frontend Planlama Dosya Haritası

```
docs/frontend/
├── METHOD.md              ← BU DOSYA (yöntem, ilk okunan)
├── ENVANTER.md            ← veri + aksiyon + sayfa eşlemesi (sonraki)
├── sayfalar/              ← her sayfa şablonu (sonraki)
├── design_system.md       ← renk + tipografi + komponent (sonraki)
└── ux_kurallar.md         ← i18n + erişilebilirlik + mekan ses tonu (sonraki)
```

---

## §7 — Onay Kapısı

§1 mekan modeli **onaylanmadan**:
- §3 şablonu uygulanmaz
- §6'daki diğer dosyalar yazılmaz
- Sayfa ağacı / route listesi tartışılmaz

Onay gelince METHOD.md v1.0 olarak işaretlenir, ENVANTER yazımına geçilir.

---

## §8 — Açık Sorular (sayfa ağacı çizilmeden önce çözülür)

- Toplam sayfa sayısı / route mu yoksa modal mı kararı her sayfa için ayrı verilir
- Profil / ayarlar mekan içi mi yoksa üst seviye mi
- Onboarding tek mekan mı yoksa "kütüphaneci ile tanışma" mı
- Auth ekranları mekan dışı mı

Bu sorular **METHOD onayı sonrası**, ENVANTER yazımı sırasında cevaplanır.
