# Sercan Handoff Packet — F2 Sprint (Backend Code Complete)

> F2 Day 1-4 sprint kapanisi. Bu dosya Sercan'in post-hoc PR review batch'i icin hazirlanmistir.

---

## 1. Commit Zinciri Ozeti

### Day 1 (B-014): 8 commit — temel iskelet
- P000 uv+pyproject+Makefile+Python 3.12.13+ruff/mypy/pytest
- P001 FastAPI app + 3 middleware (auth+rate_limit+sentry)
- P002 Supabase+Pinecone+Redis client wrappers
- P003 5-katman ABC iskelet (Listener/Anchor/PoolRouter/Reranker/Curator)
- P005 PmidAnchor PMID 12-segment partial match
- P010 /api/search POST endpoint + Pydantic models + mock orchestration
- P010-fix Council 24 duzeltmeleri

### Day 2 (B-018): 6 commit — concrete services + skeleton endpoints
- P004 QwenListener concrete (HF httpx async + cold-start retry)
- P007 BgeReranker concrete (BAAI/bge-reranker-v2-m3 lazy-load)
- P009 DilSpesifikPresenter (LiteLLM async 3-dil router)
- P008 OutlinesCurator iskelet + faithfulness_gate ortak servis
- F3+F5 skeleton 6 endpoint (501 stubs)

### Day 3-4: 6 commit — Pinecone ince iscilik + routes concrete
- [P006] HybridPoolRouter concrete (2-pool RRF k=60 + Pinecone HARD filter)
- [P008-LVR] Curator LVR validate gercek (Pinecone neighbor query)
- [F3-routes] 6 endpoint 501->200 concrete (chat/summarize/enrich/reading-list/onboarding/top5)
- [calibration] faithfulness_calibration fixture (100 paper) + threshold tuning script
- [handoff] Bu dokuman + polish gate CI

### Toplam
- ~20 commit (8 + 6 + 6)
- 152 test PASS
- 0 TODO(P markers in api/

---

## 2. PR Review Checklist

- [ ] HK-1: Pydantic `extra=forbid` tum request/response modellerde
- [ ] HK-2: Kod yorumlari dogru kaynak referansi (B-010, B-012, KD-NNN)
- [ ] HK-3: Smoke fixture'lar gercek servis response snapshot'i
- [ ] HK-4: Runtime assert'ler (PMID parse, signal count, gate threshold)
- [ ] HK-5: Manifest dogrulama (plan §6 commit boundary)
- [ ] HK-6: Type-strict (mypy strict 0 issue)
- [ ] HK-7: KVKK PII scrub (Sentry before_send + log filter)
- [ ] R13.11 dis servis empirik kanit (5 fixture dosyasi)
- [ ] ruff All checks passed
- [ ] pytest 152/152 PASS
- [ ] polish_gate (`grep -r 'TODO(P' api/ | wc -l`) == 0

---

## 3. Bilinen Borclar (Known Debt) — Sercan Priority

| ID | Konu | Oncelik | Faz |
|---|---|---|---|
| KD-2 | Sentry init runtime path test | Dusuk | F7 |
| KD-4 | Auth middleware prod JWKS (ES256 + cache 5dk) | Yuksek | F2+ |
| KD-9 | Tier-aware rate limit (4 tier dict) | Orta | F5 |
| KD-12 | MiniCheck NLI fine-tune + ALCE recall | Yuksek | F3c / Faz 3 |
| KD-14 | MiniCheck v2 5B HF endpoint | Yuksek | Faz 3 |
| KD-30 | Supabase abstract lazy-fill + reranker degraded mode | Orta | F2+ |
| KD-31 | LVR threshold 0.7 keyfi — calibration fixture ile guncellenir | Dusuk | F2 wrap |
| KD-32 | Cosmos TR endpoint setup (Qwen TR fallback aktif) | Orta | F3 |
| KD-33 | level=SUMMARY jsonschema+LVR cascade (MiniCheck Faz 3) | Dusuk | Faz 3 |

---

## 4. Production Hardening (Sercan Onceligi)

1. **JWT JWKS prod** (KD-4): `verify_signature=True` + JWKS endpoint cache 5dk
2. **Tier-aware rate limit** (KD-9): `RATE_LIMIT_BY_TIER` dict, B42-049 §1
3. **Sentry runtime smoke** (KD-2): mock DSN + `before_send` actual path test
4. **HF cold-start retry** empirik tuning: 502/503/504 retry count + backoff
5. **Cosmos TR endpoint** (KD-32): Qwen fallback -> Cosmos swap
6. **MiniCheck v2 5B** (KD-14): HF endpoint + faithfulness_gate level=SUMMARY

---

## 5. Dosya Haritasi (Degisen/Yeni)

### Services (api/services/)
| Dosya | LOC | Aciklama |
|---|---|---|
| listener.py | ~220 | QwenListener HF httpx async |
| pool_router.py | ~250 | HybridPoolRouter 2-pool RRF k=60 |
| reranker.py | ~175 | BgeReranker lazy-load |
| presenter.py | ~200 | DilSpesifikPresenter LiteLLM 3-dil |
| curator.py | ~237 | OutlinesCurator + signals_13 |
| faithfulness_gate.py | ~213 | FaithfulnessGate 2-kat SEARCH + LVR |
| _mocks.py | ~120 | MockListener/Anchor/PoolRouter/Reranker |
| anchor.py | ~90 | PmidAnchor 12-segment partial match |

### Routes (api/routes/)
| Dosya | Status | Aciklama |
|---|---|---|
| search.py | 200 concrete | 5-katman pipeline + Redis cache |
| chat.py | 200 placeholder | Mock response + Redis cache |
| summarize.py | 202+200 | In-memory task store + poll |
| enrich.py | 200 placeholder | Mock enrichment + Redis cache |
| reading_list.py | CRUD 200 | In-memory store, 4 method |
| onboarding.py | 200 placeholder | Mock profile creation |
| top5.py | 200 concrete | Mock papers + margin gate |

### Config
| Dosya | Aciklama |
|---|---|
| config/faithfulness_thresholds.yaml | LVR 0.7, jsonschema 100%, MiniCheck 0.7, ALCE 0.8 |
| config/litellm_models.yaml | 3-dil model routing (qwen-tr/en/id) |

### Tests
| Dizin | Test sayisi |
|---|---|
| tests/unit/ | ~130 |
| tests/integration/ | ~22 |
| **Toplam** | **152** |

### Fixtures
| Dosya | Icerik |
|---|---|
| hf_qwen_tr_query.json | HF Qwen endpoint smoke |
| pinecone_describe.json | Pinecone index stats |
| pinecone_query_sample.json | Pinecone query response |
| supabase_schema_migrations.json | Supabase smoke |
| faithfulness_calibration.json | 100 paper x ground-truth |

### Scripts
| Dosya | Aciklama |
|---|---|
| smoke_external_services.py | R13.11 dis servis fixture ureteci |
| calibrate_faithfulness.py | ROC analysis + threshold tuning |

---

## 6. Smoke Fixture Refresh Cadence

Servis swap veya version bump yapildiginda:
1. `uv run python scripts/smoke_external_services.py` calistir
2. Fixture diff'i review et (schema degisikligi var mi?)
3. Degisiklik varsa ilgili unit test guncelle
4. CI'da fixture timestamp kontrolu (30 gun eski ise warn)

---

## 7. Siradaki Sprint Pointer

F2 backend "code complete". Siradaki:
- **F4-S2** (Omer, frontend): Makale Ara wiring + Zustand store
- **F3 backend**: 6 endpoint gercek impl Sercan handoff (Cosmos/Celery/OpenAlex/Supabase RLS)
- **F7 Pilot**: Production hardening + 5 user pilot (~2026-05-30 hedef)
