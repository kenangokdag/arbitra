-- =====================================================================
-- 0024 PLACEHOLDER — numara atlama (no-op)
-- =====================================================================
-- Bu numara üretim sırasında atlanmıştır; karşılık gelen DDL yoktur.
-- schema_migrations'a sentinel kayıt insert eder; idempotent (re-run safe).
-- =====================================================================

BEGIN;

INSERT INTO public.schema_migrations (version, description)
VALUES (
  '0024_placeholder_gap_only',
  'PLACEHOLDER — number gap; intentionally empty (N-1 audit follow-up).'
)
ON CONFLICT (version) DO NOTHING;

COMMIT;
