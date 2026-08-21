# P00 — Ürün Kimliği, Governance ve Çalışma Sözleşmesi

## Amaç

Marka, ürün felsefesi, agent çalışma düzeni ve repo gerçekliği netleşir. Daha başlamadan dağınıklık kesilir.

## Faz kapısı

North Star, state, docs ve marka sözleşmesi güncel; agent hangi dosyadan başlayacağını biliyor.

## İlgili spec dosyaları

- `docs/worldclass/SPECS/WORLDCLASS_NORTH_STAR.md`
- `docs/worldclass/SPECS/EXECUTION_PROTOCOL.md`

## Görevler

### P00-T01_BRAND_AND_PRODUCT_CONTRACT — Arbitra/PaperMind marka ve ürün sözleşmesini tekilleştir

**Öncelik:** P0  
**Bağımlılıklar:** Yok

**Dokunulacak dosyalar:**
- `web/src/lib/brand.ts`
- `web/src/components/review/ArbitraWordmark.tsx`
- `web/src/app/(marketing)/landing/page.tsx`
- `README.md`
- `docs/ARCHITECTURE.md`

**Uygulama adımları:**
1. Arbitra ana ürün, PaperMind suite/platform varsayımını kod ve docs içinde sözleşmeye bağla.
2. brand.ts içinde tek source-of-truth oluştur: productName, suiteName, tagline, confidentiality promise, review modes.
3. Landing ve review sayfalarındaki PaperMind/Arbitra karışıklığını inventory çıkarıp düzelt.
4. Docs içinde eski marka iddialarını yeni sözleşmeye göre güncelle.

**Test/doğrulama:**
- brand contract unit/snapshot test
- landing text smoke test

**Başarı tanımı:**
- Tek marka sözleşmesi var.
- UI copy çelişmiyor.
- Agent ve insan aynı product definition ile ilerliyor.

**Bir sonraki adıma geçiş:** Brand auditte çelişen ana ürün adı kalmadığında.

**Durdurma koşulları:**
- Ürün sahibi Arbitra/PaperMind rolünü farklı belirlerse docs güncellenmeden ilerleme.

---

### P00-T02_REPO_REALITY_DOC_SYNC — README/ARCHITECTURE/SECURITY gerçek kodla eşitlensin

**Öncelik:** P0  
**Bağımlılıklar:** P00-T01_BRAND_AND_PRODUCT_CONTRACT

**Dokunulacak dosyalar:**
- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/STATE.md`
- `docs/NEXT_ACTION.md`
- `pyproject.toml`
- `web/package.json`

**Uygulama adımları:**
1. README’de Next/FastAPI/worker/env iddialarını gerçek package ve kodla karşılaştır.
2. Celery/worker varsa gerçek implementation path yaz; yoksa roadmap olarak işaretle.
3. Docs içindeki outdated provider, env, deployment ve mock ifadelerini güncelle.
4. docs/worldclass/STATE.md içine mevcut gerçeklik snapshot’ı yaz.

**Test/doğrulama:**
- docs grep check for obsolete claims
- manual docs/code consistency checklist

**Başarı tanımı:**
- Ana docs gerçek kodu yansıtıyor.
- Hayali worker/provider iddiası yok.

**Bir sonraki adıma geçiş:** Yeni geliştirici README ile lokal/dev/prod farkını anlayabiliyorsa.

**Durdurma koşulları:**
- Docs ürün kabiliyetini olduğundan fazla iddia ediyorsa.

---

### P00-T03_AUTONOMOUS_STATE_AND_LEDGER — Otonom ilerleme state/ledger dosyalarını aktifleştir

**Öncelik:** P0  
**Bağımlılıklar:** P00-T02_REPO_REALITY_DOC_SYNC

**Dokunulacak dosyalar:**
- `docs/worldclass/STATE.md`
- `docs/worldclass/TASKS/backlog.csv`
- `docs/worldclass/TEMPLATES/pr_template.md`

**Uygulama adımları:**
1. STATE.md içinde active task, completed tasks, verification commands alanlarını agent için güncelle.
2. Backlog CSV/YAML task status alanını kullanılır hâle getir.
3. PR template ile task ID zorunluluğu getir.

**Test/doğrulama:**
- Manual: agent can pick next task from ROADMAP.yaml

**Başarı tanımı:**
- Her task sonunda güncellenecek tek state dosyası var.

**Bir sonraki adıma geçiş:** Agent hiçbir ek açıklama almadan P01 ilk taskını seçebildiğinde.

**Durdurma koşulları:**
- State ve roadmap task id’leri uyuşmuyorsa.

---
