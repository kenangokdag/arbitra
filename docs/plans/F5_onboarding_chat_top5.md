# F5 — Mini-Plan: E1 Onboarding + E2 Chat SSE + E3 Top-5 Onay

> **Statü**: TASLAK — F1' master plan onayı sonrası (B-001 §16) + Council 15. tur (2026-04-30)
> **Üst plan**: `docs/plans/F1_master_plan.md` + `docs/plans/F4_frontend_skeleton_arama.md` (i18n migration burada gerçekleşir)
> **Şablon**: ARCHITECT_PROMPT_TEMPLATE §0..§7 + R13 §Council
> **Owner**: Claude (prototype %80) · Sercan (SSE hardening + token usage instrumentation %20) · Omer (OPEN-005 margin eşiği + dil seçimi UX onayı)

---

## §0 Bağlam (3 cümle)

Üç ekran tek sprint'te — E1 (Onboarding 8 input, **1 kez**) + E2 (Kütüphaneci multi-turn SSE diyalog) + E3 (Top-5 onay modal margin altı sorgularda) — kullanıcının ilk açtığında tanışma → konu kilitleme → arama tetikleyici akışın UI tarafı. Niş ayrım: jenerik chat değil — backend `/api/chat` SSE her token için cümle-düzey atıf taşıyabilir, IntentPMID 12-segment partial → `pmid_match_score < OPEN-005` ise clarify, üstü ise topic-lock; E3 modal akademik **"bu mu?" tören kartı** (Crimson italic Banner §3 paterni). Onboarding profil kaydı **doğrudan Supabase client-side** `user_profiles` upsert (RLS koruması) — master §3 5-endpoint scope korunur, ek endpoint yok (bkz. §1 Karar günlüğü çelişki çözümü).

---

## §1 Karar günlüğü

| Karar | Kaynak | Etki |
|---|---|---|
| **Onboarding endpoint YOK** — `user_profiles` upsert direkt Supabase client-side (RLS `user_id = auth.uid()`); master §3 5-endpoint scope korunur. Master plan §7 "POST /api/users/onboarding" satırı çelişki — §3 5-endpoint kararı üstün (B-001 §3 dondurulmuş) | B-001 §3 + B-002 schema_v1 RLS | E1 P046 Supabase upsert; backend endpoint sıfır |
| E1 8 input (HEDEF.md §2): ana akademik alan + eğitim seviyesi + **dil tercihi (TR/EN/ID — B-005 onboarding seçimi)** + araştırma konusu (opsiyonel) + ORCID (opsiyonel) + venue tercih (Q1/Q2/all) + tier (MVP'de Öğrenci-only B42-049 §1) + KVKK consent | HEDEF.md §2 + B-005 + B42-049 §1 | RHF + Zod schema |
| E1 form: RHF (`useForm`) + Zod schema validation + per-field inline error | B42-047 A1-A4 + master §7 | `web/src/app/onboarding/page.tsx` |
| **i18n migration F5'te** (F4'te ertelenmişti): next-intl + `[locale]/` route group; locale onboarding'de seçilir, sonra Supabase profil + cookie + URL prefix; default `en`, kullanıcı seçimi `tr` veya `id` | B-005 + B42-050 §10 (geçersiz revize) | `web/src/middleware.ts` locale detection + `web/src/i18n/{en,tr,id}.json` |
| KVKK consent: `fact_consent_event` SCD-2 (Supabase) — onboarding'de `purpose=mvp_pilot` consent + cascade-delete API hazırlığı | ARCHITECTURE.md §6 + master §6.5 | P046 Supabase insert |
| E2 SSE client: native **`fetch` streaming** + `ReadableStream` (EventSource'tan üstün — POST + JWT + abort signal destekli) | F3b §3 P014 + Next 16 RSC compatible | `web/src/lib/sse-client.ts` |
| E2 SSE 5 event handler: `session` / `token` / `intent_pmid` / `clarify` / `lock` / `done` (+ `error`) | F3b §2 | `web/src/lib/zustand-stores/chat-store.ts` |
| E2 chat UI: solda mesaj listesi (Lora 16px) + sağda input (Geist Sans) + sticky Banner el-yazısı not "Sana 5 konu hazırladım" (B42-050 §3) | B42-050 §3 + HEDEF.md §2 | `web/src/app/[locale]/kutuphaneci/page.tsx` |
| E3 Top-5 onay modal: clarify event tetikler — `<Dialog>` (Radix shadcn) + Crimson italic question + 2-4 options grid + Birincil "Bu" buton (B42-050 §4) | B42-050 §3 + §4 + master §7 | `web/src/components/Top5OnayModal.tsx` |
| E3 modal seçim → POST `/api/chat` `{session_id, message: selected_option}` → server lock event → toast "Konu kilitlendi" | F3b §3 P015 margin branch | E3 modal callback |
| OPEN-005 margin eşiği frontend tarafta yok — backend `pmid_match_score < eşik` kararı verir, frontend sadece event tipini render eder | OPEN-005 (Omer F5 öncesi netleşir, default 0.7) | F5 sırasında öğrenilmesi gerekmez |
| Tier kuota guard: E2'de her mesaj sonrası backend response'tan `quota_used_pct` okunur; %80 → uyarı banner; %100 → input disabled + upgrade CTA | B42-049 §1 + master §6.2 | `web/src/components/QuotaBanner.tsx` |
| Topic-lock UX: lock event → toast (Sonner shadcn) "Konu kilitlendi: [konu adı]" + sol-nav "Aktif konu" badge; "Konu bırak" CTA F6 sonrası | B42-049 §2.1 + master §6.3 | `web/src/components/TopicLockBadge.tsx` |
| Auth flow: F4 P039 Supabase client init + magic-link login (email-otp); MVP'de OAuth yok, email-otp tek yöntem | DM-003 Supabase Auth + B-002 | `web/src/app/[locale]/login/page.tsx` |
| Streaming render: token event → mesaj bubble metnini incremental concat + `useTransition` (React 19) yumuşak update | React 19 idiomatic | P049 |
| **Playwright E2E F5'ten ertelendi → F7 Quality** (Council 15 Fayda-Maliyet) | Council 15 + master §15 F7 | F5'te manuel smoke + RTL component test |

---

## §2 Sayfa sözleşmeleri

### 2.1 E1 Onboarding (`/[locale]/onboarding`, ilk login sonrası 1 kez)
```yaml
auth: Supabase JWT (login flow'dan gelir)
form_lib: react-hook-form + @hookform/resolvers + zod
schema:
  field_of_study: { type: enum, values: [med, eng, cs, soc, hum, sci, biz, edu, other], required: true }
  education_level: { type: enum, values: [undergrad, grad, phd, postdoc, faculty], required: true }
  language: { type: enum, values: [tr, en, id], required: true }   # B-005
  research_topic: { type: string, maxLength: 200, optional: true }
  orcid: { type: string, pattern: "^\\d{4}-\\d{4}-\\d{4}-\\d{3}[0-9X]$", optional: true }
  venue_preference: { type: enum, values: [q1_only, q1_q2, all], default: q1_q2 }
  tier: { const: "ogrenci" }   # MVP-only
  kvkk_consent: { type: boolean, mustBe: true }   # Zod refine
on_submit:
  1. Supabase upsert `user_profiles` { user_id: auth.uid(), ...form_data }
  2. Supabase insert `fact_consent_event` { user_id, purpose: "mvp_pilot", granted: true, scd_start: now() }
  3. Cookie set NEXT_LOCALE=<language> + redirect to /[locale]/kutuphaneci
errors:
  zod_invalid: inline field error (Geist Sans 12px red)
  supabase_rls_reject: toast error + Sentry capture
  supabase_unique_violation: redirect /[locale]/kutuphaneci (zaten onboarding tamam)
```

### 2.2 E2 Kütüphaneci (`/[locale]/kutuphaneci`, multi-turn SSE)
```yaml
data_source: POST /api/chat (SSE)  # F3b
state: Zustand chat-store
  current_session_id: uuid|null
  messages: ChatMessage[]
  active_intent_pmid: PartialPMID|null
  topic_lock: { topic_id, state: "suggested"|"accepted"|"released" }|null
  is_streaming: boolean
  quota_used_pct: number
ui_layout:
  header: Banner el-yazısı not (B42-050 §3) "Anlat bana — sana konu çıkaralım"
  body: mesaj listesi (Lora 16px), token streaming bubble (incremental)
  footer: textarea (Geist Sans) + Birincil buton "Gönder" (B42-050 §4) + quota indicator
event_handlers:
  session: setSessionId(data.session_id)
  token: appendToLastBotMessage(data.delta)
  intent_pmid: setActiveIntentPmid(data.pmid_segments)
  clarify: openTop5OnayModal({ question, options })
  lock: setTopicLock(data) + toast "Konu kilitlendi"
  done: setIsStreaming(false) + bench.log(data.latency_ms)
  error: toast error + Sentry capture
abort: AbortController — kullanıcı yeni mesaj yazınca eski stream cancel
```

### 2.3 E3 Top-5 Onay Modal (E2 içinde modal, clarify event → açılır)
```yaml
trigger: chat-store clarify event
component: Top5OnayModal (Radix Dialog)
ui:
  header: Banner el-yazısı (Crimson italic 17px): "{event.data.question}"
  body: 2-4 option grid (B42-050 §4 İkincil buton 4 column responsive)
  each_option: { label: option_text, onClick: send selected → POST /api/chat with message=option }
  footer: Hayalet buton "Hiçbiri — yeniden anlat" → modal close + textarea focus
on_select:
  POST /api/chat { session_id, message: selectedOption } → bekle lock event → toast → modal close
on_dismiss:
  modal close (chat continues, no lock)
a11y:
  role="dialog" + aria-modal="true" + aria-labelledby + ESC kapatır + focus trap (Radix native)
```

---

## §3 İmplementasyon adımları (atomik P-numara)

| P | İş | Dosya | LOC | Test |
|---|---|---|---|---|
| **P044** | i18n migration: next-intl + `[locale]/` route group + middleware locale detection | `web/src/middleware.ts`, `web/src/i18n/{en,tr,id}.json`, `web/src/i18n/config.ts`, `web/next.config.ts` (i18n hook) | ~120 | smoke: /tr/, /en/, /id/ render; cookie NEXT_LOCALE persist |
| **P045** | E1 Onboarding sayfası + RHF + Zod schema (8 input) | `web/src/app/[locale]/onboarding/page.tsx`, `web/src/lib/schemas/onboarding-schema.ts`, `web/src/components/forms/{FieldOfStudy,EducationLevel,LanguagePicker,OrcidInput,KvkkCheckbox}.tsx` | ~250 | unit: Zod schema 8 field; ORCID regex; KVKK refine |
| **P046** | Form submit → Supabase upsert user_profiles + fact_consent_event + redirect | `web/src/app/[locale]/onboarding/actions.ts` (Server Action), `web/src/lib/supabase-server.ts` | ~100 | integration: mock Supabase → 200 + redirect; RLS reject test |
| **P047** | E2 Kütüphaneci shell + Banner header + mesaj listesi iskeleti | `web/src/app/[locale]/kutuphaneci/page.tsx`, `web/src/components/chat/{MessageList,MessageBubble,ChatInput}.tsx` | ~150 | unit: bubble role=user/bot render; auto-scroll bottom |
| **P048** | SSE client (`fetch` streaming + ReadableStream + AbortController) + 5 event parse | `web/src/lib/sse-client.ts`, `web/src/lib/zustand-stores/chat-store.ts` | ~180 | unit: 5 event mock parse + abort cancel |
| **P049** | Token streaming render (incremental + useTransition) + quota indicator | `web/src/components/chat/MessageBubble.tsx` (extension), `web/src/components/QuotaBanner.tsx` | ~120 | unit: token append O(n); quota %80 → banner render |
| **P050** | E3 Top-5 Onay Modal (Radix Dialog + 2-4 options grid + send selected) | `web/src/components/Top5OnayModal.tsx` | ~140 | unit: clarify event → modal open; option select → POST mock; dismiss close |
| **P051** | Topic-lock state UI: toast (Sonner) + sol-nav badge | `web/src/components/TopicLockBadge.tsx`, `web/src/components/ui/toast.tsx` (shadcn Sonner setup) | ~80 | unit: lock event → toast render; badge state machine 3-state |
| **P052** | E1/E2/E3 i18n string'leri (en + tr + id) — 3 dil | `web/src/i18n/en.json`, `tr.json`, `id.json` | ~150 (3×50) | smoke: tr/onboarding render TR; en/kutuphaneci EN |

**Toplam**: 9 atomic commit, ~1290 LOC. Playwright E2E F7'ye ertelendi.

---

## §4 Verification (komut + beklenen output, 8 manuel smoke senaryosu)

```bash
# S1: Build + type
cd ~/Desktop/papermind-app/web && npm run build
# Beklenen: 0 type error; .next/ + 3 locale variant build

# S2: i18n locale detection
curl http://localhost:3000/   # default redirect /en
curl -H "Accept-Language: tr-TR" http://localhost:3000/   # → /tr
# Beklenen: 307 redirect locale doğru

# S3: E1 Onboarding happy path
# manuel: /en/onboarding → 8 input doldur (med + grad + en + topic + ORCID + q1_q2 + kvkk ✓) → submit
# Beklenen: Supabase user_profiles row + fact_consent_event row + redirect /en/kutuphaneci

# S4: E1 RHF + Zod inline error
# manuel: ORCID alanına "abc" yaz, blur
# Beklenen: red inline "Geçerli ORCID formatı: 0000-0000-0000-0000"; KVKK boş → submit disabled

# S5: E2 SSE happy path (session + token + intent_pmid + lock + done)
# manuel: /en/kutuphaneci → "machine learning depression" gönder
# Beklenen sıra: bubble bot avatarı + token streaming (görsel akış); intent_pmid → console.log; lock event → toast "Topic locked"; done → input enable

# S6: E3 Top-5 Onay Modal (clarify branch)
# manuel: /en/kutuphaneci → "machine learning" tek kelime gönder (margin altı)
# Beklenen: bot bubble + clarify event → modal açılır + 3-4 options grid; "Computer Science" seç → POST → lock → modal close + toast

# S7: SSE abort
# manuel: /en/kutuphaneci → uzun sorgu gönder, 1s sonra başka mesaj yaz
# Beklenen: ilk stream cancel (network tab "cancelled"); ikinci request başlar; chat-store messages doğru sıra

# S8: Quota %80 + %100
# Mock: user_quota.token_used_mtd = 40000 → bubble sonrası 40500 (Öğrenci 50000 limit %81)
# Beklenen: QuotaBanner amber render "%81 used"; %100 → input disabled + upgrade CTA
```

---

## §5 Critical files

### Frontend touch
- `web/src/middleware.ts` (locale detection + auth gate)
- `web/src/i18n/config.ts`, `en.json`, `tr.json`, `id.json`
- `web/src/app/[locale]/onboarding/page.tsx` + `actions.ts`
- `web/src/app/[locale]/kutuphaneci/page.tsx`
- `web/src/app/[locale]/login/page.tsx` (magic-link)
- `web/src/components/forms/*.tsx` (FieldOfStudy, EducationLevel, LanguagePicker, OrcidInput, KvkkCheckbox)
- `web/src/components/chat/MessageList.tsx`, `MessageBubble.tsx`, `ChatInput.tsx`
- `web/src/components/Top5OnayModal.tsx`
- `web/src/components/TopicLockBadge.tsx`, `QuotaBanner.tsx`, `ui/toast.tsx`
- `web/src/lib/schemas/onboarding-schema.ts` (Zod)
- `web/src/lib/sse-client.ts` (fetch streaming + AbortController)
- `web/src/lib/zustand-stores/chat-store.ts`
- `web/src/lib/supabase-server.ts` (Server Action client)

### Tests touch
- `tests/web/unit/onboarding-schema.test.ts` (Zod 8 field)
- `tests/web/unit/sse-client.test.ts` (5 event parse + abort)
- `tests/web/unit/chat-store.test.ts` (state machine)
- `tests/web/integration/onboarding-flow.test.tsx` (RTL: form fill + submit + redirect)
- `tests/web/integration/chat-sse.test.tsx` (RTL + mock SSE → 5 event)
- `tests/web/integration/top5-modal.test.tsx`
- ~~`tests/web/e2e/onboarding-chat-e2e.spec.ts`~~ → **F7'ye ertelendi**

### Read-only (DOKUNMA)
- `~/Desktop/Papermind_V2/04_plan_analiz_kararlar/B42-050-DESIGN-DIRECTION.md` (§3 Banner + §4 Buton)
- `~/Desktop/Papermind_V2/04_plan_analiz_kararlar/B42-049-PROJECT-LIFECYCLE.md` (tier + topic-lock)
- `~/Desktop/papermind-app/docs/plans/F1_master_plan.md`
- `~/Desktop/papermind-app/docs/plans/F3b_chat.md` (SSE 5 event sözleşmesi)
- `~/Desktop/papermind-app/docs/plans/F4_frontend_skeleton_arama.md` (i18n F5 migration kararı)
- `~/Desktop/papermind-app/docs/HEDEF.md` (E1/E2/E3 ekran tanımları)
- `~/Desktop/papermind-app/docs/ARCHITECTURE.md`

---

## §6 TODO(sercan) — production hardening %20

### 6.1 SSE hardening
- [ ] Server-side SSE keep-alive comment (`:keep-alive\n\n` her 15s) — proxy timeout güvencesi
- [ ] Client reconnect on transient network error (max 3× exponential backoff)
- [ ] AbortController cleanup component unmount

### 6.2 Auth + KVKK
- [ ] Magic-link rate limit (Supabase Auth ayarı 5/saat/email)
- [ ] `fact_consent_event` SCD-2 trigger doğrulama (B-002 schema_v1)
- [ ] Cookie HttpOnly + Secure + SameSite=Lax (NEXT_LOCALE)

### 6.3 Token usage instrumentation
- [ ] Her chat response'unda `X-Quota-Used-Pct` header oku → QuotaBanner update
- [ ] Sentry breadcrumb: chat_session_id + token_count + intent_pmid_score

### 6.4 i18n hardening
- [ ] next-intl static rendering (build-time locale extraction)
- [ ] Eksik string fallback EN (key not found → console warn)

### 6.5 Profil avatar dropdown — KD-26 (Council 37 ileride)
- [ ] `@shadcn/dropdown-menu` primitif (KD-23 10. atom F4-S2'de import edilmiş olacak)
- [ ] Topbar user chip → tıkla → dropdown ("Profilim" / "Ayarlar" / "Çıkış")
- [ ] **Dark overlay variant** — `globals.css`'e KD-26 token grubu (`--surface-overlay-dark-*`) ekle; light `--popover` tokens değiştirilmez
- [ ] uiverse Vercel-style ilham: slide-out label animation + grouped separator (REFERENCES §5.1+§5.2)
- [ ] Çıkış → AlertDialog confirm ("Oturumu kapat? Kaydedilmemiş notlar yok") — Hold-to-Confirm pattern REDDEDİLDİ (a11y fail)
- [ ] Empirik kanıt: Anthropic Claude.ai dosya menüsü + Linear context menu yan-yana screenshot
- [ ] §Council 37 — Defne BAĞLAYICI A satırı + Sercan alan-dışı yorum (auth context)
- [ ] RTL desteği F2/Faz 2'de (ID/EN LTR baseline yeter F5'te)

---

## §7 Commit disiplini

- **Branch**: `feat/F5-onboarding-chat-top5`
- **Atomic commit**: P044..P052 ayrı commit + ayrı PR (P045 P044'süz merge edilmez — i18n routing önce)
- **Pre-flight Read**: §5 Read-only listesi
- **Test gate**: §4 S1-S8 PASS olmadan merge **YASAK**
- **Co-Authored-By**: Claude Opus 4.7
- **Commit message**: `[P0XX] web: <kısa öz>` (örn. `[P048] web: SSE client fetch streaming + 5 event parse`)

---

## §8 Önkoşullar — GÜNCEL DURUM (2026-04-30)

### ✅ Kapanmış
| Önkoşul | Kapanış |
|---|---|
| B-005 dil seçimi (TR/EN/ID) onboarding | ✅ DECISIONS.md |
| B42-049 §1 tier (MVP Öğrenci-only) | ✅ Papermind_V2/DECISIONS.md |
| B-002 user_profiles + fact_consent_event tablo + RLS | ✅ schema_v1 |

### ⏳ F4 + F3b bağımlı
| Önkoşul | Statü |
|---|---|
| **F4 PASS** (P037-P043 frontend skeleton + EN baseline) | ⏳ F4 sprint |
| **F3b PASS** (`/api/chat` SSE 5 event çalışır) | ⏳ F3b sprint |

### ⏳ Aktif engelleyiciler
| Önkoşul | Statü | Kim |
|---|---|---|
| **OPEN-005 margin eşiği** (default 0.7) | ⏳ Omer F5 öncesi netleşir | F3b backend kararı, F5 frontend transparent |
| **METHOD §1 onayı** (Akademik Mekanlar mekan modeli — onboarding flow akış onayı) | ⏳ Omer | F4 + F5 ortak önkoşul |
| **Magic-link e-mail provider** (Supabase Auth default veya custom SMTP) | ⏳ Sercan | F5 P046 |

---

## §Council — R13 15. tur (B Grubu F5 taslağı, 2026-04-30)

| # | Üye | Verdict | Gerekçe (1 cümle) | RED/YELLOW ne istedi (1 cümle) |
|---|---|---|---|---|
| 1 | **Halüsinasyon Avcısı** | ✅ GREEN | Master §3 5-endpoint + §7 onboarding satır çelişkisi açıkça yakalandı, çözüm Supabase RLS upsert (B-001 §3 dondurulmuş üstün); SSE 5 event F3b §2'den birebir alıntı | — |
| 2 | **Akademik İsabet** | ✅ GREEN | E1 8 input HEDEF.md §2 ile birebir; KVKK consent SCD-2 ARCHITECTURE.md §6 + B-002 ile uyumlu; ORCID format regex sağlam | — |
| 3 | **Fayda-Maliyet Hakemi** | ✅ GREEN (revize) | Playwright E2E F7'ye ertelendi (-100 LOC); 9 commit ~1290 LOC 3 ekran için makul (ekran başı ~430) | — |
| 4 | **Daha İyisi Var Mı?** | ⚠️ YELLOW | SSE için EventSource yerine `fetch` streaming + ReadableStream tercihi modern (POST + JWT + abort) ✓; ama **React 19 `useOptimistic`** chat send sırasında kullanıcı mesajını anında render etmek için ideal — taslakta yok | İstiyor: P049'a `useOptimistic` notu eklensin (kullanıcı mesajı anında bubble + bot streaming paralel) |
| 5 | **Global Çözüm Mühendisi** | ⚠️ YELLOW | i18n 3 dil + RTL desteği yok; **Bahasa Indonesia** LTR yani sorun yok ama Arapça/Farsça gelirse Faz 2'de RTL gerekecek; F5 EN/TR/ID için yeterli ama **Türkçe karakter ş/ğ/ı/İ font subset** Crimson Pro/Lora desteği doğrulanmadı | İstiyor: P038 (F4) zaten font load yaptı, F5 P052 i18n string'inde TR karakter renderlama smoke (S2 senaryosuna ek "ş ğ İ" karakter check) |
| 6 | **Son Kullanıcı Avukatı** | ✅ GREEN | E1 8 input ~2 dk (HEDEF.md §2 hedefi); E2 multi-turn doğal akış; E3 modal "bu mu?" tören kartı akademisyen sezgisel; quota uyarı dürüst pozisyonlama | — |

**Karar (R13.5)**: 4 GREEN + 2 YELLOW (3+ değil, sınırın altında); bypass entry gerekmez. Düzeltme ile 6 GREEN'e çekilir:
1. ✅ Halüsinasyon Avcısı GREEN
2. ✅ Akademik İsabet GREEN
3. ✅ Fayda-Maliyet GREEN (revize)
4. **Düzeltme P049**: `useOptimistic` notu — kullanıcı mesajı anında bubble (optimistic UI), backend confirmation sonrası kalıcılaşır (Daha İyisi Var Mı? YELLOW → GREEN)
5. **Düzeltme P038 → F5 §4 S2 ek**: TR karakter render smoke ("şu an doğru bir şekilde görünüyor mu?" check) (Global Çözüm YELLOW → GREEN)
6. ✅ Son Kullanıcı GREEN

**Council 15 düzeltme uygulandı**: §3 P049 satırına `useOptimistic` notu + §4 S2'ye TR karakter check (aşağıda yansıdı):

- **P049 ek**: Token streaming render + **`useOptimistic`**: kullanıcı `Gönder` basınca user bubble anında görünür (optimistic), backend `event: session` dönmeden bot bubble bekliyor; SSE token akışı bot bubble'a düşer.
- **S2 ek**: `curl -H "Accept-Language: tr-TR" /tr/onboarding` → "Eğitim seviyesi" + "ş ğ ı İ Ç Ö Ü" karakterler doğru render (Crimson Pro Latin Extended subset ✓ kontrol)

---

**Final commitment**: Bu mini-plan onaylanırsa P044 commit'i F4 PASS + F3b PASS sonrası `feat/F5-onboarding-chat-top5` branch'inde 24 saat içinde açılır; verification S1+S2+S3 PASS ile P044 PR mergeable. Tam E1+E2+E3 (P044..P052) 4-5 günde browser'dan görünür çalışır (master §9 F5 süresi).
