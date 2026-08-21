-- =====================================================================
-- PaperMind v4 — Supabase Migration 0017:
-- waitlist: landing capture form (V1-S4 Scope A — Minimal)
-- =====================================================================
-- Plan referansı : docs/plans/V1_S4_waitlist_capture.md §1 (kontrat)
-- Tarih          : 2026-05-09
-- Postgres       : 17.6
-- Bağımlılık     : yok (tek-tablo, FK yok)
-- =====================================================================
-- Amaç: Landing'deki "Erken erişim" CTA'larından email + isim capture.
-- Onay e-postası YOK (V1 scope dışı). KVKK consent YOK (Scope A).
-- Anti-spam: honeypot (UI) + global RateLimitMiddleware (60/min/IP) +
--            email UNIQUE constraint (Postgres-seviye duplicate koruması).
-- =====================================================================

BEGIN;

CREATE TABLE public.waitlist (
  id          uuid         NOT NULL DEFAULT gen_random_uuid(),
  email       varchar(254) NOT NULL,
  name        varchar(100) NOT NULL,
  source      varchar(32)  NOT NULL,
  ip          inet,
  user_agent  text,
  created_at  timestamptz  NOT NULL DEFAULT now(),
  PRIMARY KEY (id),
  CONSTRAINT waitlist_email_unique UNIQUE (email),
  CONSTRAINT waitlist_source_check CHECK (source IN ('landing_hero', 'landing_pricing'))
);

CREATE INDEX waitlist_created_at_idx ON public.waitlist (created_at DESC);

-- RLS: zorunlu (DM_RULES R10). Sadece service-role insert/select edebilir;
--      anon/authenticated kullanıcı backend (api/routes/waitlist.py) üzerinden geçer.
ALTER TABLE public.waitlist ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE  public.waitlist           IS 'V1-S4 landing waitlist capture (Scope A, no consent).';
COMMENT ON COLUMN public.waitlist.email     IS 'RFC 5321 max 254 char. Backend lower-case normalize eder.';
COMMENT ON COLUMN public.waitlist.source    IS 'landing_hero | landing_pricing — V1-S4-02 frontend wire.';
COMMENT ON COLUMN public.waitlist.ip        IS 'Anti-fraud forensic; KVKK md.5 meşru menfaat. V2 anonimleştirme.';

INSERT INTO public.schema_migrations (version, description)
VALUES (
  '0017_waitlist_table',
  'V1-S4 landing waitlist capture (Scope A — Minimal, no consent).'
)
ON CONFLICT (version) DO NOTHING;

COMMIT;
