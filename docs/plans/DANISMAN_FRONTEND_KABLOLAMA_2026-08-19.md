# Plan: Danışman panelinin rapor sayfasına kablolanması (Faz 2)

**Tarih:** 2026-08-19
**Durum:** UYGULANDI — sonuçlar §5'te.
**Kaynak:** `docs/plans/DANISMAN_REPORT_GROUNDING_PERSONA_2026-08-16.md` §7 — o zaman bilinçli olarak ertelenen 2 madde, şimdi tamamlanıyor.
**Guardian gerekmiyor** — saf frontend kablolama, motor/backend'e dokunmuyor (backend mekanizması zaten var ve test edilmiş).
**Karar verici:** Kenan.

---

## 1. Mevcut durum (kanıtlı, bu oturumda yeniden doğrulandı)

- `ChatboxPanel.tsx:90-98` — `sendMutation`, context'i (mode/reportId/pageState) TAMAMEN yok sayıyor, `paper_context_ids: []` hardcoded, `mode`/`report_id`/`page_state` hiç gönderilmiyor.
- `stores/ui.ts:19` — `ChatboxContext`'in `"advisor"` varyantında `reportId` alanı YOK, sadece `mode`+`pageState`.
- `ReviewReportView.tsx`'de hiçbir Danışman tetikleyicisi mount edilmemiş.
- `AdvisorButton.tsx` var ama sadece TEK yerde kullanılıyor değil (grep: kullanım YOK) — stili (`border-stone-300`) rapor sayfasının CSS-var tasarım diliyle (DownloadDocxButton vb.) UYUMSUZ.
- `ChatboxPanel.test.tsx` mevcut testler `apiFetch`'i mock'lamıyor ve send/starter tıklamıyor — body genişletmesi regresyon YARATMAZ (doğrulandı).

## 2. Değişiklikler

### 2.1 `stores/ui.ts`
`ChatboxContext`'in `"advisor"` varyantına `reportId?: string` eklenir (additive, tek mevcut kullanım yeri — `AdvisorButton.tsx` — opsiyonel olduğu için kırılmaz).

### 2.2 `ChatboxPanel.tsx`
`sendMutation`'ın body'si context'i GERÇEKTEN kullanır:
```ts
mode: context?.kind === "advisor" ? context.mode : "default",
report_id: context?.kind === "advisor" ? context.reportId : undefined,
page_state: context?.kind === "advisor" ? context.pageState : undefined,
```
`paper_context_ids: []` KALIR (literatür-context farklı bir kanal, bu planın kapsamı dışında).

### 2.3 `ReviewReportView.tsx` — yeni tetikleyici
`DownloadDocxButton`'ın YANINA (aynı üst şerit), aynı görsel dilde yeni bir buton — `DownloadDocxButton` gibi kendi küçük bileşeni, `useOpenChatbox` çağırır:
```ts
openChatbox({ kind: "advisor", mode: "review_advisor", reportId: jobId })
```
**`pageState` BİLİNÇLİ OLARAK gönderilmiyor** — rapor verisi zaten backend'de `report_id` üzerinden sahip-kapsamlı çekiliyor (`_build_report_context`); `pageState` istemciden gelen, sahtelenebilir bir kanal, burada gereksiz/çakışan olurdu (orijinal plan §4.5'in gerekçesiyle tutarlı).

## 3. Test planı

1. `ChatboxPanel.test.tsx`'e yeni test — `context.kind==="advisor"` iken `apiFetch`'e giden body'de `mode`/`report_id`/`page_state` doğru gidiyor mu (mock `apiFetch`).
2. Yeni butonun testi — tıklayınca `openChatbox({kind:"advisor", mode:"review_advisor", reportId: jobId})` çağrılıyor mu.
3. Mevcut testlerin regresyon YAŞAMADIĞI (`ChatboxPanel.test.tsx`, `ReviewReportView.test.tsx`).

## 4. Kapsam dışı

1. `chat/page.tsx` (tam-sayfa `/chat` rotası) — aynı eksiklik orada da var ama rapor sayfası akışı ÇalıboxPanel üzerinden, bu planın kapsamı dışında.
2. `AdvisorButton.tsx`'in diğer 15 sayfaya mount edilmesi (F9-S2, eski TODO) — bu planla ilgisiz.

## 5. Sonuçlar (uygulandı, 2026-08-19)

**Kod:** `stores/ui.ts` (`reportId?: string`, additive) + `ChatboxPanel.tsx` (`sendMutation` artık `mode`/`report_id`/`page_state`'i context'ten GERÇEKTEN okuyup gönderiyor) + `ReviewReportView.tsx` (yeni `AskAdvisorButton`, `DownloadDocxButton`'ın yanına, aynı görsel dil).

**Testler:** `ChatboxPanel.test.tsx`'e 2 yeni (advisor context'te doğru body + advisor-DIŞI'nda `mode="default"`/`report_id` yok) — bu testler için `@/lib/api` mock'landı (sadece `apiFetch`, `ApiError` render ağacında hiç kullanılmadığı doğrulandı, güvenli). `ReviewReportView.test.tsx`'e 1 yeni (buton → `openChatbox` doğru argümanlarla).

**Regresyon:** `ChatboxPanel.test.tsx` + `review/` bileşenleri + `stores/ui.test.ts` — **70/70 PASS** (65+5). `tsc --noEmit` temiz. Backend zaten çalışıyor (bugün `--reload` ile yeniden başlatıldı) — canlı uçtan-uca deneme Kenan tarafından yapılabilir.
