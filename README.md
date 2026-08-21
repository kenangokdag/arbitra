# PaperMind App

PaperMind ALI (Adaptive Literature Intelligence) MVP — TR akademisyen için akıllı literatür asistanı.

## Hızlı bakış

- **Backend:** FastAPI + Pinecone + Supabase + Redis + Celery + LiteLLM
- **Frontend:** Next.js 14 + TypeScript + Tailwind + shadcn/ui
- **Engine:** 5-katman (Listener → Anchor → Pool Router → Reranker → Curator) + ESTRA + 12-chip
- **LLM:** Dahili Qwen / YTU LLM (HuggingFace Inference Endpoint, Scale-to-Zero) + harici Claude (sadece son akademik TR rötuş)
- **Veri ambarı:** `~/Desktop/Papermind_V2/` (read-only referans, `reference/` altında özet)

## Klasör

| Yol | Ne |
|---|---|
| `api/` | FastAPI backend |
| `web/` | Next.js frontend |
| `engine/` | Saf core (5-katman + ESTRA + chip + LVR) |
| `tests/` | Unit + integration + e2e + perf + faithfulness |
| `docs/` | Plan + protokol + sprint manifest'leri |
| `deploy/` | Docker + HF + Pinecone + Supabase + monitoring |
| `scripts/` | Operasyonel utility |
| `reference/` | Read-only warehouse referansı (Papermind_V2 özeti) |

## Çalışmaya başlamak

1. `docs/CLAUDE.md` oku — oturum protokolü
2. `docs/STATE.md` oku — şu an nerede
3. `docs/NEXT_ACTION.md` oku — hemen sıradaki adım
4. `docs/DM_RULES.md` oku — kurallar (3-kontrol + sycophant yasak + plan-first)

## Mevcut faz

**Faz 0 — Hazırlık.** Klasör + skeleton oluşturuldu (2026-04-29). Sonraki: Faz 1 plan manifest yazımı.
