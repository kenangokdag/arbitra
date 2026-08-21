"""F13-S14 Cron altyapısı — 6 scheduled job entry points.

Plan: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S14
Render type: cron (deploy/render.yaml)

Job'lar:
  1. completion_delete_expired  — KVKK 3-ay sil (S2)
  2. diary_unresolved_weekly    — 21+ gün açık event raporu (S1)
  3. diary_monthly_digest       — aylık defter özeti satırları (S1)
  4. method_centrality_refresh  — V1 method_centrality recompute trigger
  5. neighbor_bibcoupling_refresh — V1 neighbor_bibcoupling recompute trigger
  6. health_heartbeat           — /healthz ping + Sentry breadcrumb

Mail provider Q4 açık olduğundan job'lar mail GÖNDERMEZ; sadece DB sync + log
çıktısı üretir. Mail bağlama F13-S15+ iş.

Çalıştırma (manuel smoke):
    uv run python -m scripts.cron.<job_name> --dry-run
"""

__all__: list[str] = []
