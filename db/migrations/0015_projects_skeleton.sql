-- =====================================================================
-- PaperMind v4 — Supabase Migration 0015: projects skeleton (F9 P091)
-- =====================================================================
-- Plan: docs/plans/F9_kesif_workbench.md §6 (canon)
-- Brain: K-029 (F9 1.1 Araştırma Alanı kanonu)
-- Bağlı kararlar: B-021/B-022 (proje bazlı pivot), K-023 (user_vectors pgvector
--                 — bu plan'da kullanılmaz, F10/F11 önkoşulu),
--                 B-024 (background canon — UI tarafı, schema etkilemez)
-- Tarih: 2026-05-05 · PG: 17.6
-- Bağımlılık: 0001 (auth.users + papers + schema_migrations + public.set_updated_at()),
--             0014 (en son uygulanan migration)
-- =====================================================================

BEGIN;

-- ============================================================================
-- 1. projects — proje kök tablosu, onboarding miras dahil
-- ============================================================================
CREATE TABLE public.projects (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  name            text NOT NULL CHECK (char_length(name) BETWEEN 1 AND 200),
  status          text NOT NULL DEFAULT 'active'
                  CHECK (status IN ('active','archived')),
  current_stage   text NOT NULL DEFAULT '1.1'
                  CHECK (current_stage ~ '^[1-5]\.[1-6]$'),

  -- Onboarding miras (snapshot — projeyi açtığı andaki kullanıcı profili)
  inherited_field_ids       text[] NOT NULL DEFAULT '{}',
  inherited_subfield_ids    text[] NOT NULL DEFAULT '{}',
  inherited_research_focus  text,

  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_projects_user_status
  ON public.projects (user_id, status);

-- updated_at: shared trigger function 0001:16'dan kullan (8 tablo paylaşımı)
CREATE TRIGGER trg_projects_updated_at
  BEFORE UPDATE ON public.projects
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;

CREATE POLICY projects_owner_select ON public.projects FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY projects_owner_insert ON public.projects FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY projects_owner_update ON public.projects FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY projects_owner_delete ON public.projects FOR DELETE
  USING (auth.uid() = user_id);

COMMENT ON TABLE public.projects IS
  'F9 P091: proje kök tablosu. Her proje sequential workbench (5 tezgah × 25 sayfa). Onboarding miras kolonları proje açılışındaki user_profile snapshot.';

-- ============================================================================
-- 2. project_chat_messages — Kütüphaneci sohbet log (1.1 Stage A)
-- ============================================================================
CREATE TABLE public.project_chat_messages (
  id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id            uuid NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
  attempt_no            smallint NOT NULL DEFAULT 1
                        CHECK (attempt_no >= 1 AND attempt_no <= 10),
  turn_no               smallint NOT NULL
                        CHECK (turn_no >= 1 AND turn_no <= 4),
  role                  text NOT NULL
                        CHECK (role IN ('user','adviser')),
  content               text NOT NULL CHECK (char_length(content) BETWEEN 1 AND 4000),
  parsed_understanding  jsonb,  -- {focuses:[3], field, subfield, interdisc, confidence}
  created_at            timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_chatmsg_project_attempt_turn
  ON public.project_chat_messages (project_id, attempt_no, turn_no);

ALTER TABLE public.project_chat_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY chatmsg_owner ON public.project_chat_messages FOR ALL
  USING (project_id IN (SELECT id FROM public.projects WHERE user_id = auth.uid()))
  WITH CHECK (project_id IN (SELECT id FROM public.projects WHERE user_id = auth.uid()));

COMMENT ON TABLE public.project_chat_messages IS
  'F9 P091: 1.1 Araştırma Alanı Stage A Kütüphaneci sohbet log. attempt_no = uyumsuzluk reset sayısı, turn_no = aynı attempt içindeki tur (max 4).';

-- ============================================================================
-- 3. project_anchor — çapa seçimi + uyumsuzluk hafızası + cluster status
-- ============================================================================
CREATE TABLE public.project_anchor (
  project_id        uuid PRIMARY KEY REFERENCES public.projects(id) ON DELETE CASCADE,
  anchor_paper_id   text,
  candidates_meta   jsonb,                 -- 3 aday + skor + rationale + packet_p/s
  rejected_anchors  jsonb NOT NULL DEFAULT '[]'::jsonb,
  reject_reasons    jsonb NOT NULL DEFAULT '[]'::jsonb,
  locked_at         timestamptz,
  cluster_status    text NOT NULL DEFAULT 'pending'
                    CHECK (cluster_status IN ('pending','expanding','ready','failed'))
);

ALTER TABLE public.project_anchor ENABLE ROW LEVEL SECURITY;

CREATE POLICY anchor_owner ON public.project_anchor FOR ALL
  USING (project_id IN (SELECT id FROM public.projects WHERE user_id = auth.uid()))
  WITH CHECK (project_id IN (SELECT id FROM public.projects WHERE user_id = auth.uid()));

COMMENT ON TABLE public.project_anchor IS
  'F9 P091: 1.1 Araştırma Alanı Stage B/C — çapa paper_id + 3 aday meta + uyumsuzluk hafızası (rejected_anchors+reject_reasons Gemini sistem prompt context). cluster_status background job state machine. Operational debugging metadata (cluster_error/started_at/completed_at) P095/P096 cluster_expander migration ile eklenir (YAGNI).';

-- ============================================================================
-- 4. papers.title_tsv — BÖLÜM 2 lexical havuz (KD-23 KAPANIR, manifest §6 L219-222)
-- ============================================================================
-- Manifest §11 #11: papers.title_tsv YOK → P091'de inline materialize.
-- 24.87M satır × ~200 byte ≈ 5 GB ek disk + ~10-15 dk migration süresi.
-- Supabase compute 2XL ZORUNLU (manifest §14 #5). Pro tier $25/ay limiti içinde.
-- Bir kez yazılır; sonraki INSERT'ler GENERATED ile trigger'sız otomatik.

ALTER TABLE public.papers
  ADD COLUMN IF NOT EXISTS title_tsv tsvector
    GENERATED ALWAYS AS (to_tsvector('simple', coalesce(title, ''))) STORED;

CREATE INDEX IF NOT EXISTS idx_papers_title_tsv
  ON public.papers USING gin (title_tsv);

COMMENT ON COLUMN public.papers.title_tsv IS
  'F9 P091 KD-23: BÖLÜM 2 lexical havuz tsvector (simple config). GIN index ile @@ plainto_tsquery O(log n).';

-- ============================================================================
-- 5. schema_migrations log
-- ============================================================================
INSERT INTO public.schema_migrations (version, description)
VALUES (
  '0015_projects_skeleton',
  'projects + project_chat_messages + project_anchor (F9 1.1) + papers.title_tsv (KD-23 lexical)'
)
ON CONFLICT (version) DO NOTHING;

COMMIT;
