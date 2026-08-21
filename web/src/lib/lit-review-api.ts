/**
 * V1-S10 literature-review API client + backend↔frontend adapter.
 * kaynak: docs/plans/V1_S10_vitrin_tek_sayfa.md §6
 *
 * Backend `/api/q/literature-review` LiteratureReviewResponse → frontend LitReviewResponseApi.
 * Pydantic forbid → snake_case body (paper_ids, lang).
 */

import { ApiError, apiFetch } from "./api";

export type LitReviewLang = "tr" | "en" | "id";

export type LitReviewRequest = {
  paperIds: string[];
  lang?: LitReviewLang;
};

export type ReferenceApi = {
  index: number;
  citation: string;
};

export type LiteratureReviewApi = {
  content: string;
  references: ReferenceApi[];
};

export type LitReviewResponseApi = {
  review: LiteratureReviewApi;
  quotaRemaining: number;
  quotaReset: string;
};

type BackendReference = {
  index: number;
  citation: string;
};

type BackendLiteratureReview = {
  content: string;
  references: BackendReference[];
};

type BackendLitReviewResponse = {
  review: BackendLiteratureReview;
  quota_remaining: number;
  quota_reset: string;
};

function adaptReview(r: BackendLiteratureReview): LiteratureReviewApi {
  return {
    content: r.content,
    references: r.references.map((ref) => ({
      index: ref.index,
      citation: ref.citation,
    })),
  };
}

export async function generateLitReview(
  req: LitReviewRequest,
  signal?: AbortSignal,
): Promise<LitReviewResponseApi> {
  const lang: LitReviewLang = req.lang ?? "tr";
  const body = {
    paper_ids: req.paperIds,
    lang,
  };
  const res = await apiFetch<BackendLitReviewResponse>(
    "/api/q/literature-review",
    { method: "POST", body, signal },
  );
  return {
    review: adaptReview(res.review),
    quotaRemaining: res.quota_remaining,
    quotaReset: res.quota_reset,
  };
}

export { ApiError };
