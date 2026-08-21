-- =====================================================================
-- PaperMind v4 — Migration 0037: cluster_expander observability + ESTRA
-- Plan: docs/plans/V1_S17_cascade_5rc.md §2 P002 + §3 KD-V1-S17-01/02
-- Bağımlılık: 0015 (project_anchor) + 0016 (project_cluster)
--
-- Eklenenler:
--   project_cluster.signals_13       jsonb  (ESTRA 13-sinyal sözlüğü)
--   project_cluster.anchor_paper_id  text   (cluster'ı doğuran çapa)
--   project_anchor.cluster_started_at    timestamptz  (BackgroundTask başı)
--   project_anchor.cluster_completed_at  timestamptz  (ready/failed transition)
--   project_anchor.cluster_error         jsonb        (failed durum gerekçesi)
--
-- 0015 COMMENT'i bu kolonları "P095/P096 cluster_expander migration ile
-- eklenir (YAGNI)" diye işaretliyordu — V1-S17 sprint açtı.
-- =====================================================================

BEGIN;

ALTER TABLE public.project_cluster
  ADD COLUMN IF NOT EXISTS signals_13 jsonb,
  ADD COLUMN IF NOT EXISTS anchor_paper_id text;

COMMENT ON COLUMN public.project_cluster.signals_13 IS
  'ESTRA 13-sinyal sözlüğü (Q_weak/MQ_Tier1/CD5/sentence_role_RES + 8 placeholder). curator._signals_13 reuse.';
COMMENT ON COLUMN public.project_cluster.anchor_paper_id IS
  'Bu cluster satırını doğuran çapa paper_id. project_anchor.anchor_paper_id snapshot — anchor değişirse yeni cluster_expander çalıştırması delete-then-insert ile bu sütunu da yeniler.';

ALTER TABLE public.project_anchor
  ADD COLUMN IF NOT EXISTS cluster_started_at   timestamptz,
  ADD COLUMN IF NOT EXISTS cluster_completed_at timestamptz,
  ADD COLUMN IF NOT EXISTS cluster_error        jsonb;

COMMENT ON COLUMN public.project_anchor.cluster_started_at IS
  'BackgroundTask Stage C başlangıç damgası (cluster_status=expanding'' set ile birlikte).';
COMMENT ON COLUMN public.project_anchor.cluster_completed_at IS
  'cluster_status terminal transition (ready|failed) damgası.';
COMMENT ON COLUMN public.project_anchor.cluster_error IS
  'cluster_status=failed iken hata gerekçesi (reason/exception_type/timestamp). HK-1 hata yutma yasak.';

INSERT INTO public.schema_migrations (version, description)
VALUES (
  '0037_cluster_expander_columns',
  'project_cluster.signals_13+anchor_paper_id ve project_anchor.cluster_started_at/completed_at/error (V1-S17 P002 Stage C observability)'
)
ON CONFLICT (version) DO NOTHING;

COMMIT;
