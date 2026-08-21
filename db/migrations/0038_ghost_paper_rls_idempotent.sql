-- 0038_ghost_paper_rls_idempotent.sql
--
-- Amaç: dim_ghost_paper üzerindeki RLS policy'lerini idempotent re-apply et.
-- 0001 init'te policy adı `ghost_read_authenticated` idi; 0003 DROP TABLE + yeni
-- `ghost_read_all` ile yeniden yarattı. Dev DB'lerinde 0003 öncesi state'te
-- kalmış (veya `ghost_read_all` eksik kalmış) ortamlarda re-run güvenli olsun:
-- mevcut policy'ler DROP, sonra CREATE.
--
-- (M-17 audit follow-up — 0003'te DROP TABLE ... CASCADE kullanıldığı için
-- env drift gözleniyordu; bu migration kalıcı çözüm değil, drift sigortası.)

BEGIN;

DROP POLICY IF EXISTS ghost_read_all          ON public.dim_ghost_paper;
DROP POLICY IF EXISTS ghost_read_authenticated ON public.dim_ghost_paper;
DROP POLICY IF EXISTS ghost_write_service     ON public.dim_ghost_paper;

CREATE POLICY ghost_read_all ON public.dim_ghost_paper
  FOR SELECT TO authenticated USING (true);

CREATE POLICY ghost_write_service ON public.dim_ghost_paper
  FOR ALL TO service_role USING (true) WITH CHECK (true);

INSERT INTO public.schema_migrations (version, description)
VALUES (
  '0038_ghost_paper_rls_idempotent',
  'dim_ghost_paper RLS policies (ghost_read_all, ghost_write_service) idempotent re-apply (M-17 env drift sigortası).'
)
ON CONFLICT (version) DO NOTHING;

COMMIT;
