/**
 * V1-S8 + V1-S10 Q preview API client + backend↔frontend adapter.
 * kaynak: docs/plans/V1_S10_vitrin_tek_sayfa.md §5 (KD-V1-S10-01: 25 mk sabit)
 *
 * Backend `/api/q` QResponse → frontend QResponseApi.
 * LLM YOK; sadece OpenAlex polite-pool preview, 25 makale (tier-bağımsız liste boyutu).
 * Günlük kota: anon=3, authed=5 (tier_gate.py).
 */

import { ApiError, apiFetch } from "./api";

export type QLang = "tr" | "en" | "id";

export type QRequest = {
  query: string;
  lang?: QLang;
  yearFrom?: number;
  yearTo?: number;
};

type BackendPaperPreview = {
  openalex_id: string;
  doi: string | null;
  title: string;
  abstract: string | null;
  year: number | null;
  venue: string | null;
  authors: string[];
  cited_by_count: number;
  mini_summary: string | null;
};

type BackendQueryTranslation = {
  original: string;
  detected_lang: "tr" | "en" | "id" | "other";
  english_query: string;
};

type BackendQResponse = {
  papers: BackendPaperPreview[];
  translation: BackendQueryTranslation | null;
  quota_remaining: number;
  quota_reset: string;
};

export type PaperPreviewApi = {
  id: string;
  doi: string | null;
  title: string;
  abstract: string | null;
  year: number | null;
  venue: string | null;
  authors: string[];
  authorsLabel: string;
  citedByCount: number;
};

export type QueryTranslationApi = {
  original: string;
  detectedLang: "tr" | "en" | "id" | "other";
  englishQuery: string;
};

export type QResponseApi = {
  papers: PaperPreviewApi[];
  translation: QueryTranslationApi | null;
  quotaRemaining: number;
  quotaReset: string;
};

const SHORT_ABSTRACT_MAX = 220;

function truncate(text: string, max: number): string {
  if (text.length <= max) return text;
  return `${text.slice(0, max - 1).trimEnd()}…`;
}

function authorsLabel(authors: string[]): string {
  if (authors.length === 0) return "—";
  if (authors.length <= 3) return authors.join("; ");
  return `${authors[0]} et al.`;
}

function adaptPaper(p: BackendPaperPreview): PaperPreviewApi {
  return {
    id: p.openalex_id,
    doi: p.doi,
    title: p.title,
    abstract: p.abstract ? truncate(p.abstract, SHORT_ABSTRACT_MAX) : null,
    year: p.year,
    venue: p.venue,
    authors: p.authors,
    authorsLabel: authorsLabel(p.authors),
    citedByCount: p.cited_by_count,
  };
}

export async function fetchQ(
  req: QRequest,
  signal?: AbortSignal,
): Promise<QResponseApi> {
  const lang: QLang = req.lang ?? "tr";
  // Backend Pydantic forbid extra → snake_case zorunlu
  const body: Record<string, unknown> = {
    query: req.query,
    lang,
    ...(req.yearFrom !== undefined ? { year_from: req.yearFrom } : {}),
    ...(req.yearTo !== undefined ? { year_to: req.yearTo } : {}),
  };

  const res = await apiFetch<BackendQResponse>("/api/q", {
    method: "POST",
    body,
    signal,
  });

  return {
    papers: res.papers.map(adaptPaper),
    translation: res.translation
      ? {
          original: res.translation.original,
          detectedLang: res.translation.detected_lang,
          englishQuery: res.translation.english_query,
        }
      : null,
    quotaRemaining: res.quota_remaining,
    quotaReset: res.quota_reset,
  };
}

export { ApiError };
