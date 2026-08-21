# p-0 · Projelerim (Kabuk)

> Tezgah: **Kabuk** — proje seçim/oluşturma, anchor-nötr.
> Mock kanon: D-canon full-screen pilot (D9 + D14 + tier matrix + D5/D6 kart + D6 frontier rec + D16 empty-state + D15 FAB).

---

## KONUM
- **Mock:** `PaperMind_mock_v1.0.html:813-1047` (D-canon page + dc-spec techspec)
- **Sidebar:** `PaperMind_mock_v1.0.html:603-604` (Kabuk · 1 sayfa)
- **Bu md:** `Page_Design/Sayfa_Plani_v1/_kabuk/p-0_projelerim.md`

## ROL
Kullanıcı oturum açtıktan sonra **kapı**: hangi projeye dön, hangisine yeni başla. Tier matrisi → şeffaf paywall. Aylık öneri → sessiz öğrenmenin kanıtı (recommendation engine batch çıktısı). Kabuk seviyesinde danışman **uyur** — proje seçilmeden chat input disabled.

## BACKEND ✅ var
- `POST /api/project` → `api/routes/project.py:106-172` — create + onboarding miras kopyalama (`user_profile_fields` bridge → `inherited_field_ids`, `user_profile_subfields` bridge → `inherited_subfield_ids`, `user_profiles.metadata.research_focus_en` → `inherited_research_focus`)
- `GET /api/project` → `api/routes/project.py:175-201` — `list[ProjectListItem{id, name, status, current_stage, updated_at}]`, `updated_at DESC`
- `GET /api/project/{id}` → `api/routes/project.py:204-226` — full read, `anchor=None` placeholder (P094+ wire)
- **Defansif zırh:** Service role RLS bypass'a karşı manuel `.eq("user_id", uid)` (`project.py:14-15` uyarı + `218`)

## DB ✅ var
- `projects` → `db/migrations/0015_projects_skeleton.sql:19-58` (uuid id, user_id FK, name 1-200, status `active|archived`, **`current_stage` CHECK regex `^[1-5]\.[1-6]$`**, `inherited_field_ids text[]`, `inherited_subfield_ids text[]`, `inherited_research_focus text`, RLS owner-only 4 policy)
- `project_anchor` → `0015:95-110` (P094+ wire — bu sayfada None placeholder)
- `project_cluster` → `db/migrations/0016_project_cluster.sql:9-22` (RRF çıktısı + ESTRA skor; kart üstündeki "cluster N alt-tema" chip için)
- `project_chat_messages` → `0015:66-90` (Kabuk'ta uyur — proje sayfalarında aktif)

## PİLOT
- **LLM:** Yok (sayfa LLM-free; sadece rec batch çıktısı render)
- **Recommendation engine:** Batch — `summary_cache` veya benzer batch çıktısı (mock'ta `dc-rec-h` → "batch 2026-05-01"). **Çalışan endpoint kanıtı YOK** (atölye süreci ileri faz)

## BAĞIMLILIK
- Onboarding tamam (`onboarding.py` + `0012_user_profile_fields_and_tier_refactor.sql` + `0014_user_profile_subfields_bridge.sql`)
- Auth middleware (`request.state.user_id`)
- Default tier `ogrenci` (3-tier enum `0012`: ogrenci/arastirmaci/profesyonel — DM-046 Anon vs Pro canon)

---

## SAYFA YAPISI (ASCII)

```
┌──────────────────────────────────────────────────────────────────────┐
│ D9 sidebar 260px      │  D14 pusula rotası (5-node, dim — proje yok) │
│ ┌─────────────────┐   │  ┌────────────────────────────────────────┐  │
│ │ P  PaperMind    │   │  │ D ─ C ─ G ─ A ─ S    ⌕ ara   [O]      │  │
│ │ omerren27·öğrenci│  │  └────────────────────────────────────────┘  │
│ ├─────────────────┤   │                                              │
│ │ Henüz proje yok │   │  Projelerim                       [＋ Yeni] │
│ │ 3/3 · sağdan aç │   │  Hangisine dön, hangisine yeni başla?       │
│ ├─────────────────┤   │                                              │
│ │ 5 Tezgah · 25   │   │  ┌── Tier · erişim matrisi ── öğrenci ──┐  │
│ │ ▪ Discovery 1.x │   │  │  Anon       Vitrin Q sadece           │  │
│ │ ▪ Curation 2.x  │   │  │■ Öğrenci    + Kabuk · D · C · G       │← │
│ │ ▪ Gap 3.x       │   │  │  Araştırmacı + Authoring · Defense    │  │
│ │ ▪ Auth 4.x 🔒   │   │  │  Profesyonel + Gemini 2.5 Pro · sınrsz│  │
│ │ ▪ Defense 5.x🔒 │   │  └────────────────────────────────────────┘  │
│ └─────────────────┘   │                                              │
│                       │                                              │
│ ⚙ Ayarlar             │  Aktif projeler          3/3 · öğrenci sınırı│
│ ↗ Çıkış               │  ┌──────────────┐  ┌──────────────┐         │
│                       │  │ α · 2.3 Cur. │  │ β · 3.4 Gap  │         │
│                       │  │ b-amber band │  │ b-teal band  │         │
│                       │  │ D─C●─G─A─S   │  │ D─C─G●─A─S   │         │
│                       │  │ [2.3'e dön→] │  │ [3.4'e dön→] │         │
│                       │  └──────────────┘  └──────────────┘         │
│                       │  ┌──────────────┐  ┌─ ＋ Yeni proje ─┐      │
│                       │  │ γ · 1.2 Disc.│  │ dashed CTA      │      │
│                       │  │ inactive 2hf │  └─────────────────┘      │
│                       │  └──────────────┘                            │
│                       │                                              │
│                       │  ┌── Bu ay senin için (rec batch) ──┐       │
│                       │  │ b-frontier band · cesur · derin    │       │
│                       │  │ "Geçen ay 3'ten 2'sini havuza..."  │       │
│                       │  └────────────────────────────────────┘     │
│                       │                                              │
│ ┌─ D16 chatbox ─┐     │                                              │
│ │ Danışman · ✦  │     │                                  [✎ Hızlı   │
│ │ uyur · proje  │     │                                   not] D15  │
│ │ seçilmeden    │     │                                              │
│ │ mesaj yok     │     │                                              │
│ └───────────────┘     │                                              │
└──────────────────────────────────────────────────────────────────────┘
```

---

## TASARIM DETAYI

### Front (D-canon)
- **D9 sidebar 260px:** workspace block (avatar + ad + tier) + proje slot (Kabuk'ta dim) + 5 tezgah · 25 sayfa listesi (Auth/Defense öğrenci'de 🔒)
- **D14 pusula rotası:** 5-node (D-C-G-A-S), Kabuk'ta `opacity:.4` (proje yok = silüet)
- **Tier matrisi:** 4 satır (Anon + 3-tier auth) D5/D6 stili, aktif tier `act` class
- **Proje kartları (D5/D6 band-canon):** stage chip + mini-route 5-nokta + tier-locked CTA. Bant renk kuralı: amber=Curation/Auth, teal=Gap, gold=Defense, frontier=rec
- **Aylık öneri panel (D6 frontier band):** `dc-rec` blok + chip `acc deneysel` + monolog quote
- **D16 chatbox empty-state:** ✦ ikon + "Bir projeye gir, sohbet orada başlar" + disabled input
- **D15 sticky note FAB:** sağ-alt sabit `✎ Hızlı not`

### Back
- `GET /api/project` (list, updated_at DESC) → projeler grid
- `POST /api/project` (yeni proje) → onboarding miras kopyala → URL `/project/{id}` → 1.1'e yönlendir
- `GET /api/project/{id}` → tek proje detayı (kart click)
- **Recommendation:** batch'ten okur (somut endpoint açık soru — bkz. AÇIK SORULAR)

### Veri akışı
1. Kullanıcı login → `request.state.user_id` set
2. Sayfa mount → `GET /api/project` (3 satır)
3. Her satır: `current_stage` parse (`X.Y` → mini-route active node `X`'inci)
4. `cluster N alt-tema` chip için: `project_cluster` count (project_id'ye göre `rank_final IS NOT NULL`)
5. "＋ Yeni" → modal → `POST /api/project` → 201 → push `/project/{new_id}`
6. Aylık öneri → batch tablosundan tek satır (dış: `summary_cache` veya benzer)

---

## TIER (DM-046 · 3-tier `user_tier`)
- **Anon:** sayfaya gelmez (vitrin Q'da kalır)
- **Öğrenci (`ogrenci`, default):** 3 proje slot, Auth/Defense kilitli (matrix'te 🔒)
- **Araştırmacı (`arastirmaci`):** 5+ proje, Authoring + Defense açık
- **Profesyonel (`profesyonel`):** ek olarak Gemini 2.5 Pro (uzun bağlam) + sınırsız quota

> Backend enum: `0012_user_profile_fields_and_tier_refactor.sql` — `user_tier` ENUM (`ogrenci`,`arastirmaci`,`profesyonel`), default `ogrenci`. Mock'taki eski T0-T4 visual revize edildi.

---

## AÇIK SORULAR
1. **Recommendation engine endpoint adı?** Mock `dc-rec-h` "batch 2026-05-01" diyor ama `api/routes/` içinde rec route YOK. Öneri: `GET /api/recommendation/monthly?project_id=` → `summary_cache`'den batch çıktısı; F12+ planı bekliyor.
2. **`cluster N alt-tema` chip kaynağı?** `project_cluster` row count mu, yoksa cluster_status='ready' işareti mi? `0016` schema'da `rank_final` var — chip için `WHERE rank_final IS NOT NULL` agregasyonu mantıklı.
3. **2 hafta inaktif** chip kuralı? `now() - updated_at > 14d` — mock'ta sabit string. Front-end hesaplaması yeterli.
4. **Mock revize:** mock `PaperMind_mock_v1.0.html` hâlâ 5-tier görsel kullanıyor — md'lerde 3-tier'e geçildi, mock güncelleme ayrı iş.
5. **"3/3 · öğrenci sınırı"** — quota tablosu (`user_quota`) henüz schema'da yok. Limit nerede enforce edilir? Şimdilik ön-yüzde sayım + backend `POST /api/project` 4. proje denemesinde 403 dönmeli — yok.

---

## §Kaynak Listesi (file:line)

| # | İddia | Dosya | Satır |
|---|---|---|---|
| 1 | Sidebar order Kabuk · 1 sayfa | `PaperMind_mock_v1.0.html` | 603-604 |
| 2 | D-canon page block (sayfa 0) | `PaperMind_mock_v1.0.html` | 813-1047 |
| 3 | Tier matrisi (mock 5 satır eski; md 4 satır 3-tier'e revize) | `PaperMind_mock_v1.0.html` | 875-883 |
| 4 | 3 proje kartı + dashed yeni | `PaperMind_mock_v1.0.html` | 891-965 |
| 5 | Aylık öneri panel | `PaperMind_mock_v1.0.html` | 969-988 |
| 6 | dc-spec techspec | `PaperMind_mock_v1.0.html` | 1010-1045 |
| 7 | `POST /api/project` create + miras | `api/routes/project.py` | 106-172 |
| 8 | `GET /api/project` list | `api/routes/project.py` | 175-201 |
| 9 | `GET /api/project/{id}` read | `api/routes/project.py` | 204-226 |
| 10 | RLS bypass defansif `.eq("user_id")` | `api/routes/project.py` | 14-15, 218 |
| 11 | `projects` tablo + CHECK regex stage | `db/migrations/0015_projects_skeleton.sql` | 19-35 |
| 12 | RLS 4 policy owner | `db/migrations/0015_projects_skeleton.sql` | 45-58 |
| 13 | `project_anchor` (P094+ wire) | `db/migrations/0015_projects_skeleton.sql` | 95-110 |
| 14 | `project_chat_messages` | `db/migrations/0015_projects_skeleton.sql` | 66-90 |
| 15 | `project_cluster` RRF + ESTRA | `db/migrations/0016_project_cluster.sql` | 9-22 |
| 16 | Vitrin canon (Anon vs Pro tier) | `Page_Design/Sayfa_Plani_v1/_envanter_felsefe.md` | §11 |
