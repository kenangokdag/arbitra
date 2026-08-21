# Freelance Illustrator Brief — PaperMind v4

> **Karar:** B-017 (2026-04-30) Senaryo B — Claude kod üretir, Omer iterasyon yapar, freelance illustrator 7 asset paketi sağlar, Sercan post-hoc prod hardening.
> **Bütçe:** $500-1500 (1 hafta)
> **Stil:** Akademik Defter & Akşam Kütüphanesi metaforu (B42-050)
> **Teslimat:** SVG (vektör, ölçeklenebilir, dark mode varyantı dahil) + tema renk değişkenleri ile uyumlu

---

## 1. Proje özeti (illustrator için)

PaperMind v4 — akademisyenler için literatür keşfi + hakemlik + savunma simülasyonu platformu (TR + EN + ID). 5 tezgâh × 25 alt-sayfa Notion-benzeri Defter ile kullanılır. **Estetik yön: "Akademik Defter & Akşam Kütüphanesi"** — Notion'ın sıcak hiyerarşisi × Türk akademik kültürünün ritueli × kütüphane fişi metaforu.

**Rakip ayrışımı:** Connected Papers soğuk-grafik / Litmaps dramatik-cluttered / Elicit ruhsuz-form / SciSpace jenerik-SaaS. PaperMind farkı: **danışman varlığı + tören ağırlığı + okuma-önce arayüz**.

**Tipografi (illustration ile uyumlu olmalı):**
- Display: Crimson Pro
- Body: Lora (serif — rakip ayrışımının ana sinyali)
- UI: Geist Sans
- Mono: Geist Mono

**Renk paleti (4-bölgeli):**
- Discovery/Curation: krem-parşömen `#F5EBDD` + ink lacivert `#1A1F3A` + abajur amber `#E8A157`
- Gap Atlas: soğuk açık gri `#EEF2F5` + derin teal `#0E4F4A`
- Authoring: saf krem `#FAF7F2` + koyu mor-gri `#2A1F3A`
- Defense: parşömen `#F0E9DD` + koyu lacivert `#0F1A2E` + ahşap altın `#C9A961`
- **Abajur amber `#E8A157` 4 modda sabit** = danışman varlığı sembolü
- Dark mode = "Gece Kütüphanesi" (light invers DEĞİL, kendi mood'u — derin lacivert + altın aksanlar)

---

## 2. Asset listesi (7 parça)

### Asset 1 — ✒ Kalem ikonu (3-boyut perspektif)

**Açıklama:** Çelik uçlu antika dolma kalem; **danışman varlığı sembolü**, her sayfada banner'da ve "Danışmana sor" butonunda kullanılacak. Vintage akademik öğretmen masası estetiği.

**Gereksinimler:**
- 3 boyut hafif perspektif (düz değil, dinamik açı)
- Çelik uç (gümüş gri detay)
- Gövde abajur amber `#E8A157` ana renk
- 3 boyut: 16×16 (inline), 24×24 (banner), 48×48 (boş-state)
- SVG, viewBox standardize, currentColor parametre desteği

**Referans:** Vintage Pelikan / Faber-Castell ahşap dolma kalem; Notion ✏ ikon değil daha karakterli.

### Asset 2 — Adviser avatar (3-mood)

**Açıklama:** Danışman karakteri stilize avatar. PaperMind'in "yanında durmuş danışman" hissi — soğuk profesör değil, sıcak akademik mentor.

**Gereksinimler:**
- 3 mood: **dinleyen** (başı hafif eğik, gözler nazik), **anlatan** (eli açıklama yapıyor pozisyonu), **cesaret veren** (omuz dokunuşu hareketi veya sıcak gülümseme)
- Stilize (foto-gerçekçi DEĞİL — illustration); cinsiyet/yaş nötr (akademisyen tipolojisinden uzak); ten/saç/kıyafet farklılığı yok
- Amber accent (eşarp/koltuk/kahve fincanı detayı)
- 64×64 + 128×128 + 256×256 boyutlar
- SVG layered (mood değişimi tek dosyada `data-mood` attribute ile)

**Referans:** Linear illustrations / Notion's onboarding characters / Stripe documentation chars — özellikle **Notion's "Welcome to Notion" karakterleri** stiline yakın ama akademik dokunuş.

### Asset 3 — Boş-state illustration (5 varyant)

**Açıklama:** Kullanıcı sayfası boş olduğunda gösterilen sıcak illustration. "Henüz bir şey yok" mesajı yerine **davet** hissi.

**Gereksinimler:**
- 5 varyant (her tezgâh için 1):
  1. Discovery boş — yarı açık kitap + büyüteç + sıcak kahve fincanı (akşam kütüphane masası)
  2. Curation boş — boş kütüphane fişi rafı + ✒ kalem hazır
  3. Gap Atlas boş — boş harita parşömeni + pusula
  4. Authoring boş — boş Defter sayfası + dolma kalem
  5. Defense boş — kapalı kırmızı kadife perde + sahne ışıkları (yanmamış)
- Her biri 4-bölgeli paletten kendi tezgâh rengi
- 320×240 boyut (responsive lazım — viewBox)
- SVG; karmaşık değil ama detaylı (3-5 ana element)

**Referans:** Undraw.co stilinde değil daha **karakterli + Türk akademik öğretim üyesi masası** estetiği.

### Asset 4 — Defense perde girişi (durağan SVG fallback)

**Açıklama:** B42-050 §5.5 perde-reveal sinematik animasyon ana asset olarak Google Flow video kullanılacak (1-3 MB MP4/WebM); ama low-bandwidth fallback + meta-tag/og:image için **durağan SVG**.

**Gereksinimler:**
- Kırmızı kadife perde yarı açık + arkasında jüri silüet + spotlight ışığı yere düşüyor
- Defense paleti (parşömen + koyu lacivert + ahşap altın)
- 1280×720 (16:9 op:image standart)
- SVG; çok detay gerekmez — atmosferik, sinematik

**Referans:** Tiyatro perde clipart değil, daha karanlık akademik salon havası (yeterlilik / tez savunması salonu).

### Asset 5 — 5 tezgâh ikon-arması

**Açıklama:** Üst nav + denizci pusulası rotasında her tezgâh için temsili arma. Lucide React generic icon yetersiz — özgün karakter.

**Gereksinimler:**
- 5 ikon: Discovery (büyüteç + ışık), Curation (kütüphane fişi + amber şerit), Gap Atlas (parşömen harita + pusula), Authoring (Defter + ✒), Defense (perde + jüri masası)
- Monokrom + amber accent (her tezgâh kendi ana renginden çıkmaz)
- 32×32 + 64×64 + filled/outlined varyant her biri
- SVG, currentColor desteği (Tailwind `text-amber-500` ile renklenebilir)

**Referans:** Apple SF Symbols genişletilmiş + Notion's emoji yerine custom ikon yaklaşımı.

### Asset 6 — 🎓 5.6 limanı (Defense bitiş)

**Açıklama:** Pusula rotasının en sağ ucunda Defense Tezgâhı tamamlandığında "limanına ulaştın" hissi. Mezuniyet metaforu.

**Gereksinimler:**
- Tezgâh sırası bitince görünen "ödül asset"i — küçük liman + ahşap iskele + amber ışık
- Mezuniyet kepi 🎓 yerine **kütüphane lambası + açık kitap** (akademik tören mesajı)
- 96×96 + 192×192
- SVG, statik (animasyon Framer Motion ile kod tarafından)

### Asset 7 — Custom SVG pack (8-12 micro-asset)

**Açıklama:** Sayfa içi micro-decoration — Lucide React generic-yetersiz kalan yerlerde kullanılacak özgün SVG'ler.

**Gereksinimler:**
- Kütüphane fişi alt bandı texture (PaperCard için, paper-grain CSS gradient ile uyumlu)
- Dolma kalem ucu (banner kenar dekorasyonu)
- Açık kitap (loading / progress indicator alternatifi)
- Klasör (project switching)
- Mum (Authoring odası "deep work" mod sembolü)
- Pusula iğnesi (navigation pointer)
- Mühür (PaperCard "validated" rozeti)
- Kütüphane raf çizgisi (sidebar separator)
- 16-24 px SVG, currentColor, lightweight (<2 KB her biri)

---

## 3. Teslimat formatı

```
illustrator_pack/
├── README.md                          (kullanım rehberi + lisans)
├── pen_3d/
│   ├── pen-16.svg
│   ├── pen-24.svg
│   └── pen-48.svg
├── adviser/
│   ├── listening-64.svg
│   ├── listening-128.svg
│   ├── listening-256.svg
│   ├── explaining-{64,128,256}.svg
│   └── encouraging-{64,128,256}.svg
├── empty_states/
│   ├── discovery-empty.svg
│   ├── curation-empty.svg
│   ├── gap-atlas-empty.svg
│   ├── authoring-empty.svg
│   └── defense-empty.svg
├── defense_curtain/
│   └── defense-curtain-1280x720.svg
├── workbench_emblems/
│   ├── discovery-{32,64}-{filled,outlined}.svg
│   ├── curation-{32,64}-{filled,outlined}.svg
│   ├── gap-atlas-{32,64}-{filled,outlined}.svg
│   ├── authoring-{32,64}-{filled,outlined}.svg
│   └── defense-{32,64}-{filled,outlined}.svg
├── defense_harbor/
│   ├── harbor-96.svg
│   └── harbor-192.svg
└── micro_pack/
    ├── card-band-texture.svg
    ├── pen-tip.svg
    ├── open-book.svg
    ├── folder.svg
    ├── candle.svg
    ├── compass-needle.svg
    ├── seal.svg
    └── shelf-line.svg
```

---

## 4. Stil rehberi (uyulması zorunlu)

| Kural | Detay |
|---|---|
| **Renk uyumu** | 4-bölgeli paletten dışına çıkma; abajur amber `#E8A157` 4 modda sabit |
| **Çizgi kalitesi** | El çizimi hissi — sterile vector-art değil; light texture/grain kabul |
| **Stilize seviyesi** | Foto-gerçekçi YASAK; flat-design YASAK; **akademik vintage illustration** orta nokta |
| **CurrentColor** | İkonlar Tailwind `text-*` ile renklenebilmeli (`stroke="currentColor"`) |
| **A11y** | SVG `<title>` + `<desc>` zorunlu (screen reader); `role="img"` |
| **Dark mode** | Her asset 2 varyant: light + dark; ışık/gölge ters çevrilmiş |
| **Lisans** | Tam ticari haklar (PaperMind ücretli SaaS olacak) — work-for-hire kabul edilebilir |
| **Kaynak dosya** | Final SVG + Figma/Adobe Illustrator kaynak teslim |

---

## 5. Süreç

| Adım | Süre | Çıktı |
|---|---|---|
| 1. Brief + paletten örnekleme | 1 gün | Illustrator 1 örnek asset (Asset 1: Pen 3D) gönderir; Omer onaylar veya revize ister |
| 2. Onay sonrası tüm paketin draft'ı | 3 gün | 7 asset draft (rough); Omer geri bildirim |
| 3. Revize | 2 gün | Draft → final |
| 4. Final teslim | 1 gün | Tam paket + kaynak dosya + README |
| **Toplam** | **7 gün** | — |

---

## 6. Aday illustrator profili (aramaya başlanacak)

- **Türk illustrator tercih** — akademik / kütüphane / Türk vintage estetik anlayışı için
- Behance / Dribbble portfolyosunda akademik veya kütüphane / kitap odaklı iş örneği
- SVG çıktı standart, Figma kaynak uyumlu
- İletişim Türkçe (brief Türkçe, geri bildirim akışı hızlanır)

**Aramaya başlanacak kanallar:**
- LinkedIn "illustrator + Türkçe + akademik"
- Behance "Turkish illustrator + book / library"
- Dribbble Türkiye
- Boğaziçi/ITÜ/MSGSÜ Tasarım bölümü mezunlarının portfolyo siteleri
- Twitter Türk illustration topluluğu

---

## 7. Sözleşme şablonu (kısa)

- **İş kapsamı:** Bu brief'te listelenen 7 asset paketi
- **Süre:** 7 gün; gecikme günde %2 ceza
- **Bütçe:** $500-1500 (anlaşma sonucu)
- **Lisans:** Tam ticari haklar (work-for-hire); kaynak dosya teslim
- **Revize:** 2 tur dahil; ek tur saatlik ücret
- **Tatmin garantisi:** İlk asset onayı zorunlu; reddedilirse %30 ön ödeme iade

---

**Sonraki adım:** Omer bütçeyi onayladıktan sonra aday arama başlar (1-2 gün portfolyo tarama). Aday seçimi sonrası bu brief Türkçe yazılı kontrat ile gönderilir.
