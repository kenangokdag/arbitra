-- =====================================================================
-- PaperMind v4 — Supabase Migration 0001: schema_v1 (MVP)
-- =====================================================================
-- Karar referansı: F1_master_plan.md §5 (11 tablo MVP) + 5 mini-plan §1
-- Tarih: 2026-04-29  ·  Region: eu-central-1 (Frankfurt, KVKK)
-- Postgres: 17.6  ·  RLS: zorunlu her tabloda (DM_RULES R10)
-- =====================================================================

BEGIN;

-- 0. Extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;       -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pg_trgm;        -- title trigram search

-- =====================================================================
-- 1. Helper trigger function — updated_at auto-set
-- =====================================================================
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =====================================================================
-- 2. Enum types
-- =====================================================================
CREATE TYPE public.user_tier AS ENUM ('ogrenci', 'arastirmaci', 'profesyonel', 'takim');
CREATE TYPE public.paper_kind AS ENUM ('corpus', 'ghost');
CREATE TYPE public.reading_status AS ENUM ('to_read', 'reading', 'done');
CREATE TYPE public.lock_state AS ENUM ('suggested', 'accepted', 'released');
CREATE TYPE public.summary_mode AS ENUM ('abstract', 'detailed');
CREATE TYPE public.task_status AS ENUM ('queued', 'running', 'done', 'failed');

-- =====================================================================
-- 3. papers — corpus PaperCard mirror (on-demand cache, partial cols)
--    Not: full 24.87M warehouse Pinecone'da; bu tablo sadece UI render için lazy mirror.
-- =====================================================================
CREATE TABLE public.papers (
  paper_id              text PRIMARY KEY,                  -- W123 (OpenAlex Work id)
  doi                   text,
  title                 text NOT NULL,
  abstract              text,
  authors               jsonb,                             -- [{name, orcid?, affiliation?}]
  year                  int,
  year_verified         boolean NOT NULL DEFAULT false,    -- K1 enforce
  venue                 text,
  publication_type      text,                              -- article|review|conf|book
  lang                  text,                              -- ISO 639-1
  citations_count       int DEFAULT 0,
  pmid_segments         jsonb,                             -- 12-segment D.F.S.T1.T2.T3.Y.Q.I.L.R.V
  metadata              jsonb DEFAULT '{}'::jsonb,
  created_at            timestamptz NOT NULL DEFAULT now(),
  updated_at            timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_papers_doi ON public.papers(doi) WHERE doi IS NOT NULL;
CREATE INDEX idx_papers_year ON public.papers(year) WHERE year_verified = true;
CREATE INDEX idx_papers_title_trgm ON public.papers USING gin (title gin_trgm_ops);
CREATE TRIGGER trg_papers_updated_at BEFORE UPDATE ON public.papers
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.papers ENABLE ROW LEVEL SECURITY;
CREATE POLICY papers_read_all ON public.papers
  FOR SELECT TO authenticated USING (true);            -- her authenticated user okur
CREATE POLICY papers_write_service ON public.papers
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- =====================================================================
-- 4. dim_ghost_paper — non-corpus paper (cited by corpus papers ≥3)
-- =====================================================================
CREATE TABLE public.dim_ghost_paper (
  ghost_id              text PRIMARY KEY,                  -- GHOST_OA_W4567
  doi                   text,
  title                 text NOT NULL,
  abstract              text,
  authors               jsonb,
  year                  int,
  year_verified         boolean NOT NULL DEFAULT false,    -- K1 enforce
  venue                 text,
  lang                  text,
  n_corpus_citers       int NOT NULL DEFAULT 0,            -- K8 enforce: ≥3 görünür
  enrichment_status     text DEFAULT 'pending',            -- pending|enriched|failed
  enriched_at           timestamptz,
  metadata              jsonb DEFAULT '{}'::jsonb,
  created_at            timestamptz NOT NULL DEFAULT now(),
  updated_at            timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_ghost_n_citers ON public.dim_ghost_paper(n_corpus_citers) WHERE n_corpus_citers >= 3;
CREATE TRIGGER trg_ghost_updated_at BEFORE UPDATE ON public.dim_ghost_paper
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.dim_ghost_paper ENABLE ROW LEVEL SECURITY;
CREATE POLICY ghost_read_authenticated ON public.dim_ghost_paper
  FOR SELECT TO authenticated USING (n_corpus_citers >= 3);   -- K8 runtime gate
CREATE POLICY ghost_write_service ON public.dim_ghost_paper
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- =====================================================================
-- 5. dim_theme — 4516 theme dimension
-- =====================================================================
CREATE TABLE public.dim_theme (
  theme_id              text PRIMARY KEY,
  name_tr               text NOT NULL,
  name_en               text,
  slug                  text UNIQUE NOT NULL,
  parent_theme_id       text REFERENCES public.dim_theme(theme_id),
  level                 int NOT NULL DEFAULT 1,
  metadata              jsonb DEFAULT '{}'::jsonb,
  created_at            timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_theme_parent ON public.dim_theme(parent_theme_id);
CREATE INDEX idx_theme_slug_trgm ON public.dim_theme USING gin (slug gin_trgm_ops);

ALTER TABLE public.dim_theme ENABLE ROW LEVEL SECURITY;
CREATE POLICY theme_read_all ON public.dim_theme
  FOR SELECT TO authenticated USING (true);
CREATE POLICY theme_write_service ON public.dim_theme
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- =====================================================================
-- 6. user_profiles — kullanıcı ek profil (auth.users 1:1)
-- =====================================================================
CREATE TABLE public.user_profiles (
  user_id               uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  display_name          text,
  orcid_hash            text,                              -- KVKK: hash+salt, raw değil
  field_primary         text,                              -- ana alan (psikoloji, makine öğrenmesi, vb.)
  language_pref         text NOT NULL DEFAULT 'tr',
  tier                  public.user_tier NOT NULL DEFAULT 'ogrenci',
  onboarding_completed  boolean NOT NULL DEFAULT false,
  metadata              jsonb DEFAULT '{}'::jsonb,
  created_at            timestamptz NOT NULL DEFAULT now(),
  updated_at            timestamptz NOT NULL DEFAULT now()
);
CREATE TRIGGER trg_user_profiles_updated_at BEFORE UPDATE ON public.user_profiles
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY profile_self_read ON public.user_profiles
  FOR SELECT TO authenticated USING (auth.uid() = user_id);
CREATE POLICY profile_self_insert ON public.user_profiles
  FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
CREATE POLICY profile_self_update ON public.user_profiles
  FOR UPDATE TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- Auto-create profile on auth.users INSERT
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.user_profiles (user_id) VALUES (NEW.id) ON CONFLICT DO NOTHING;
  INSERT INTO public.user_quota (user_id) VALUES (NEW.id) ON CONFLICT DO NOTHING;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =====================================================================
-- 7. user_quota — tier kuotası (B42-049 §1)
-- =====================================================================
CREATE TABLE public.user_quota (
  user_id               uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  llm_tokens_used       bigint NOT NULL DEFAULT 0,
  llm_tokens_limit      bigint NOT NULL DEFAULT 50000,     -- Öğrenci default 50K/ay
  reading_list_count    int NOT NULL DEFAULT 0,
  reading_list_limit    int NOT NULL DEFAULT 50,           -- Öğrenci default 50 paper
  reset_at              timestamptz NOT NULL DEFAULT (date_trunc('month', now()) + interval '1 month'),
  updated_at            timestamptz NOT NULL DEFAULT now()
);
CREATE TRIGGER trg_user_quota_updated_at BEFORE UPDATE ON public.user_quota
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.user_quota ENABLE ROW LEVEL SECURITY;
CREATE POLICY quota_self_read ON public.user_quota
  FOR SELECT TO authenticated USING (auth.uid() = user_id);
CREATE POLICY quota_service_write ON public.user_quota
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- =====================================================================
-- 8. chat_sessions
-- =====================================================================
CREATE TABLE public.chat_sessions (
  id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id               uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  title                 text,
  intent_pmid           jsonb,                             -- partial PMID extraction state
  topic_lock_id         uuid,                              -- topic_locks.id (nullable)
  created_at            timestamptz NOT NULL DEFAULT now(),
  updated_at            timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_chat_sessions_user ON public.chat_sessions(user_id, updated_at DESC);
CREATE TRIGGER trg_chat_sessions_updated_at BEFORE UPDATE ON public.chat_sessions
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.chat_sessions ENABLE ROW LEVEL SECURITY;
CREATE POLICY chat_sessions_self_all ON public.chat_sessions
  FOR ALL TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- =====================================================================
-- 9. chat_messages
-- =====================================================================
CREATE TABLE public.chat_messages (
  id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id            uuid NOT NULL REFERENCES public.chat_sessions(id) ON DELETE CASCADE,
  user_id               uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  role                  text NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content               text NOT NULL,
  tokens                int,
  metadata              jsonb DEFAULT '{}'::jsonb,         -- citations, intent_pmid, faithfulness_meta
  created_at            timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_chat_messages_session ON public.chat_messages(session_id, created_at);

ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;
CREATE POLICY chat_messages_self_all ON public.chat_messages
  FOR ALL TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- =====================================================================
-- 10. topic_locks — B42-049 lifecycle (MVP: 3-state suggested→accepted→released)
-- =====================================================================
CREATE TABLE public.topic_locks (
  id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id               uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  session_id            uuid REFERENCES public.chat_sessions(id) ON DELETE SET NULL,
  topic_name            text NOT NULL,
  pmid_segments         jsonb,                             -- locked PMID
  state                 public.lock_state NOT NULL DEFAULT 'suggested',
  accepted_at           timestamptz,
  released_at           timestamptz,
  metadata              jsonb DEFAULT '{}'::jsonb,
  created_at            timestamptz NOT NULL DEFAULT now(),
  updated_at            timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_topic_locks_user ON public.topic_locks(user_id, state);
CREATE TRIGGER trg_topic_locks_updated_at BEFORE UPDATE ON public.topic_locks
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.topic_locks ENABLE ROW LEVEL SECURITY;
CREATE POLICY topic_locks_self_all ON public.topic_locks
  FOR ALL TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- chat_sessions.topic_lock_id FK (cyclic dep — eklenir)
ALTER TABLE public.chat_sessions
  ADD CONSTRAINT chat_sessions_topic_lock_fk
  FOREIGN KEY (topic_lock_id) REFERENCES public.topic_locks(id) ON DELETE SET NULL;

-- =====================================================================
-- 11. user_reading_list — F3e (M52)
-- =====================================================================
CREATE TABLE public.user_reading_list (
  id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id               uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  paper_id              text NOT NULL,                     -- W123 veya GHOST_OA_W4567
  paper_kind            public.paper_kind NOT NULL,
  note                  text CHECK (length(note) <= 2000),
  tags                  text[] DEFAULT '{}',
  status                public.reading_status NOT NULL DEFAULT 'to_read',
  pinned                boolean NOT NULL DEFAULT false,
  pinned_order          int,
  added_at              timestamptz NOT NULL DEFAULT now(),
  updated_at            timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, paper_id)
);
CREATE INDEX idx_reading_list_user_status ON public.user_reading_list(user_id, status);
CREATE INDEX idx_reading_list_user_pinned ON public.user_reading_list(user_id, pinned, pinned_order);
CREATE TRIGGER trg_reading_list_updated_at BEFORE UPDATE ON public.user_reading_list
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.user_reading_list ENABLE ROW LEVEL SECURITY;
CREATE POLICY reading_list_self_all ON public.user_reading_list
  FOR ALL TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- Trigger: paper_id existence check (papers veya dim_ghost_paper)
CREATE OR REPLACE FUNCTION public.check_reading_list_paper_exists()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.paper_kind = 'corpus' THEN
    IF NOT EXISTS (SELECT 1 FROM public.papers WHERE paper_id = NEW.paper_id) THEN
      RAISE EXCEPTION 'paper_not_found: corpus paper_id=% does not exist', NEW.paper_id
        USING ERRCODE = 'foreign_key_violation';
    END IF;
  ELSIF NEW.paper_kind = 'ghost' THEN
    IF NOT EXISTS (SELECT 1 FROM public.dim_ghost_paper WHERE ghost_id = NEW.paper_id) THEN
      RAISE EXCEPTION 'paper_not_found: ghost_id=% does not exist', NEW.paper_id
        USING ERRCODE = 'foreign_key_violation';
    END IF;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_reading_list_paper_check
  BEFORE INSERT OR UPDATE OF paper_id, paper_kind ON public.user_reading_list
  FOR EACH ROW EXECUTE FUNCTION public.check_reading_list_paper_exists();

-- =====================================================================
-- 12. summary_cache — F3c (paper_id + mode → SummaryDoc, TTL 24h)
-- =====================================================================
CREATE TABLE public.summary_cache (
  paper_id              text NOT NULL,
  paper_kind            public.paper_kind NOT NULL,
  mode                  public.summary_mode NOT NULL,
  task_id               uuid,                              -- Celery task
  status                public.task_status NOT NULL DEFAULT 'queued',
  summary_doc           jsonb,                             -- {sections, citations_lvr, faithfulness_meta, model_chain}
  faithfulness_meta     jsonb,                             -- {jsonschema_pct, minicheck_nli, alce_recall}
  error_msg             text,
  expires_at            timestamptz NOT NULL DEFAULT (now() + interval '24 hours'),
  created_at            timestamptz NOT NULL DEFAULT now(),
  updated_at            timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (paper_id, mode)
);
CREATE INDEX idx_summary_cache_status ON public.summary_cache(status, created_at) WHERE status IN ('queued', 'running');
CREATE INDEX idx_summary_cache_expires ON public.summary_cache(expires_at);
CREATE TRIGGER trg_summary_cache_updated_at BEFORE UPDATE ON public.summary_cache
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.summary_cache ENABLE ROW LEVEL SECURITY;
CREATE POLICY summary_cache_read_authenticated ON public.summary_cache
  FOR SELECT TO authenticated USING (true);             -- cache shared
CREATE POLICY summary_cache_write_service ON public.summary_cache
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- =====================================================================
-- 13. enrichment_log — F3d audit + idempotency
-- =====================================================================
CREATE TABLE public.enrichment_log (
  id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  ghost_id              text NOT NULL REFERENCES public.dim_ghost_paper(ghost_id) ON DELETE CASCADE,
  user_id               uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  task_id               uuid,
  source                text NOT NULL CHECK (source IN ('openalex', 'semantic_scholar', 'manual')),
  depth                 int NOT NULL DEFAULT 1 CHECK (depth IN (1, 2)),
  status                public.task_status NOT NULL DEFAULT 'queued',
  fields_updated        jsonb,                             -- {doi, year_verified, abstract, ...}
  error_msg             text,
  created_at            timestamptz NOT NULL DEFAULT now(),
  completed_at          timestamptz
);
CREATE INDEX idx_enrichment_ghost ON public.enrichment_log(ghost_id, created_at DESC);
CREATE INDEX idx_enrichment_status ON public.enrichment_log(status, created_at) WHERE status IN ('queued', 'running');

ALTER TABLE public.enrichment_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY enrichment_log_read_authenticated ON public.enrichment_log
  FOR SELECT TO authenticated USING (true);
CREATE POLICY enrichment_log_write_service ON public.enrichment_log
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- =====================================================================
-- Bitiş — versiyon tablo
-- =====================================================================
CREATE TABLE IF NOT EXISTS public.schema_migrations (
  version               text PRIMARY KEY,
  applied_at            timestamptz NOT NULL DEFAULT now(),
  description           text
);
INSERT INTO public.schema_migrations (version, description)
VALUES ('0001_init_schema_v1', 'F1_master_plan §5 — 11 tablo MVP + RLS + triggers')
ON CONFLICT (version) DO NOTHING;

COMMIT;
