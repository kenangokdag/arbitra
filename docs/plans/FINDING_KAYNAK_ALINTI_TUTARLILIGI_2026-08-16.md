# Plan: Her Finding'i makaledeki kaynak metne bağlayan tutarlı gösterim

**Tarih:** 2026-08-16
**Durum:** UYGULANDI (Katman A) — Kenan kararı (AskUserQuestion): "Katman A + Katman B, A bugün, B ayrı günde." Katman A bu oturumda uygulandı (sonuçlar §6'da). **Katman B AYRI bir oturuma TODO olarak kilitlendi** (§3'te tanımlı, guardian + goldset regresyon zorunlu — bu oturumun tempo/risk profiline uymuyor, bilinçli erteleme).
**Kaynak:** Kenan'ın bu oturumdaki isteği — "bazı bulgular ham metinden alıntı yapıyor ama tutarsız, her Finding için standart bir gösterim olsun."

---

## 1. Mevcut veri yapısı — kaynak metin/konum bilgisi VAR (kanıtlı, A-seviye)

`Finding.manuscript_anchors: list[ManuscriptAnchor]` (`api/models/review.py:562-569`, her biri `anchor_id`/`section`/`quote`) — TAM DA bunun için tasarlanmış. Frontend'de zaten bir gösterim deseni VAR: `ManuscriptAnchorLink` → tıkla → `AnchorDrawer` (alıntıyı gösterir) — bu oturumun ilk planında ("Danışman") da referans verdiğim, önceden test edilmiş ("İMZA ANI") bir akış.

**Ama sadece `manuscript_anchors` DOLU olan Finding'lerde görünüyor.** `FindingDetail` (`ReviewReportView.tsx:875`): `finding.manuscript_anchors.length > 0 ? <...ManuscriptAnchorLink...> : null` — boşsa HİÇBİR ŞEY gösterilmiyor, nedeni (global-sorun mu, yoksa veri eksik mi) HİÇ ayırt edilmiyor.

## 2. Kök neden (3+ derinlik, kanıtlı)

**Semptom:** Bazı Finding'ler tıklanabilir "makaledeki yer" linki gösteriyor, bazıları göstermiyor — tutarsız. Kullanıcının verdiği örnek ("Başlıkta X ifadesi...") muhtemelen `summary`/`reasoning_public` serbest metnine GÖMÜLÜ, `manuscript_anchors`'a hiç YAZILMAMIŞ.

- **Niye tutarsız?** → `manuscript_anchors` bazı Finding'lerde boş kalıyor.
- **Niye boş kalıyor?** → LLM'e SADECE `severity ∈ {critical, major}` için anchor ZORUNLU kılınmış — **3 role module'de de (`qualitative_rigor.py:25-29`, `quantitative_validity.py:29-30`, `academic_dimension.py:85-86`) BİREBİR aynı "ZORUNLU KANIT KURALI" ifadesiyle doğrulandı.**
- **Niye sadece critical/major?** → `_engine_base.py:295-310`'daki sözleşme uygulaması da SADECE `severity in _HIGH_SEVERITY` iken anchor/action eksikliğini `moderate`'e indiriyor (dürüst downgrade). `moderate`/`minor`/`info` için HİÇBİR zorunluluk/teşvik yok.
- **Kök neden:** Motorun kanıt-zorunluluğu severity'ye göre kademelendirilmiş — critical/major'da GARANTİLİ (anchor VEYA global_issue=true, aksi halde otomatik downgrade), moderate/minor/info'da LLM'in serbest tercihine bırakılmış. LLM bazen alıntıyı prose'a gömüyor, bazen structured anchor'a koyuyor — GARANTİSİZ.

**Sonuç:** Bu bir FRONTEND render eksikliği DEĞİL (mevcut kod, mevcut veriyi doğru gösteriyor) — kök neden ENGINE/PROMPT katmanında, kademelendirilmiş zorunluluk kuralında.

## 3. İki bağımsız katman — Kenan'ın kapsam kararı gerekiyor

### Katman A — Frontend tutarlılık (bu oturumda yapılabilir, guardian GEREKMİYOR, sıfır motor riski)
Her Finding için "Makalendeki yer" bloğunu HER ZAMAN göster, 3 durumu ayırt et:
1. `manuscript_anchors` dolu → mevcut `ManuscriptAnchorLink` (değişmiyor).
2. `manuscript_anchors` boş + `global_issue=true` → yeni, sakin bir etiket: *"Bu belge geneli bir sorun — tek bir cümleye işaret edilmiyor."*
3. `manuscript_anchors` boş + `global_issue=false` (moderate/minor/info'da şema-seviyesinde İZİN VERİLEN durum) → yeni, dürüst bir itiraf: *"Kaynak konumu yapısal olarak belirtilmedi."*

**Bunun karşılamadığı şey (dürüstçe belirtilmeli):** Kullanıcının somut örneği ("Başlıkta X ifadesi..." prose'a gömülü alıntı) durumu 3'e düşer — Katman A SADECE bunu "belirtilmedi" diye dürüstçe işaretler, alıntıyı prose'dan ÇEKİP yapısal hale GETİRMEZ. Görünürlük tutarlılığı sağlar, ALTTAKİ veri tutarsızlığını ÇÖZMEZ.

### Katman B — Engine/prompt kök-neden düzeltmesi (guardian ZORUNLU, goldset regresyon gerekiyor, ayrı/daha büyük iş)
3 role module'ün "ZORUNLU KANIT KURALI"nı TÜM severity'lere genişletmek (ya da en az: "makaleden alıntı yapıyorsan HER ZAMAN `manuscript_anchors`'a koy, `summary`/`reasoning_public`'e gömme" kuralını severity'den bağımsız yapmak). Bu, kullanıcının istediği "her Finding standart göstersin" hedefine TAM ulaşan tek yol.

**Neden bu oturumda YAPILMIYOR (varsayılan):** `engine/academic/` altında bir prompt/sözleşme değişikliği — CLAUDE.md Moat Denetimi kuralı gereği guardian ZORUNLU, ayrıca CLAUDE.md §3.6 ("test=davranış kanıtı") gereği goldset'e karşı önce/sonra regresyon gerektirir (bu oturumdaki DOCX/öncelik-listesi/boyut-vurgusu gibi saf frontend işlerden FARKLI bir risk sınıfı). Kenan'ın bugünkü tempoya göre bu daha ağır bir iş.

## 4. Test planı (Katman A onaylanırsa)

`ReviewReportView.test.tsx`'e: (1) anchor'lı Finding mevcut davranışı koruyor, (2) `global_issue=true` + anchor'sız Finding → yeni etiket görünüyor, (3) `global_issue=false` + anchor'sız Finding → "belirtilmedi" notu görünüyor, (4) mevcut testler regresyon YAŞAMIYOR (özellikle "İMZA ANI" akışı).

## 5. Kapsam dışı (her iki katman onaylansa bile)

1. Geçmiş/mevcut rapor kayıtlarındaki Finding'lerin geriye dönük düzeltilmesi (re-run) — bu bir görüntüleme değişikliği, veri migrasyonu DEĞİL.
2. DOCX export'a aynı 3-durumlu tutarlılığın eklenmesi — ayrı, küçük takip.

## 6. Sonuçlar (Katman A uygulandı, 2026-08-16)

**Kod:** `ReviewReportView.tsx`'in `FindingDetail` bileşeni — "Makalendeki yer" bloğu artık HER Finding için render ediliyor (önceden `manuscript_anchors.length > 0` iken tamamen render-dışıydı), 3 durum: anchor'lı (mevcut `ManuscriptAnchorLink`, değişmedi), `global_issue=true` (yeni `data-testid="finding-source-global"` etiketi), ikisi de değilse (yeni `data-testid="finding-source-unspecified"` dürüst itiraf notu).

**Testler:** 3 yeni test — anchor'lı Finding'de regresyon YOK, `global_issue=false`+anchor'sız (fixture'ın gerçek F-003'ü, clarity) → "belirtilmedi" notu, `global_issue=true` override → "belge geneli sorun" etiketi.

**Regresyon:** `web/src/components/review/` — **41/41 PASS** (8 dosya). `tsc --noEmit` temiz.

**AÇIK, KİLİTLİ TODO — Katman B (kök-neden, ayrı oturum):** 3 role module'ün (`qualitative_rigor.py`, `quantitative_validity.py`, `academic_dimension.py`) "ZORUNLU KANIT KURALI"sını (`manuscript_anchors` zorunluluğu) `critical`/`major`'dan TÜM severity'lere genişletmek. Guardian danışması ZORUNLU (`engine/academic/` değişikliği) + goldset'e karşı önce/sonra regresyon ZORUNLU (CLAUDE.md §3.6). Bu yapılmadan, Kenan'ın orijinal örneği ("Başlıkta X ifadesi..." gibi prose'a gömülü alıntılar) hâlâ yapısal `manuscript_anchors`'a DÖNÜŞMEYECEK — Katman A sadece bu durumu dürüstçe GÖRÜNÜR kılıyor, veriyi düzeltmiyor.
