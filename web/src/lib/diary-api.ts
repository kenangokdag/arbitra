/**
 * F13-S1-P005 — /api/diary/* client + backend↔frontend adapter.
 * kaynak: docs/plans/F13_sayfa_plani_v2_implementation.md §3 (F13-S1-P005)
 *
 * Backend Pydantic snake_case → frontend camelCase. POST/PATCH body snake_case.
 */

import { ApiError, apiFetch } from "./api";

export type DiaryEventType =
  | "kayit"
  | "danismana_sor"
  | "kutuphane_ekle"
  | "not";

// ── Backend (snake_case) ───────────────────────────────────────────────────
type BackendDiaryEvent = {
  id: string;
  project_id: string;
  user_id: string;
  page_slug: string;
  paper_id: string | null;
  event_type: DiaryEventType;
  payload: Record<string, unknown>;
  created_at: string;
  resolved_at: string | null;
};

type BackendTimeline = {
  items: BackendDiaryEvent[];
  next_cursor: string | null;
  count: number;
};

type BackendPreAdvisor = {
  summary: string;
  event_count: number;
  period_start: string;
  period_end: string;
};

// ── Frontend (camelCase) ───────────────────────────────────────────────────
export type DiaryEventApi = {
  id: string;
  projectId: string;
  userId: string;
  pageSlug: string;
  paperId: string | null;
  eventType: DiaryEventType;
  payload: Record<string, unknown>;
  createdAt: string;
  resolvedAt: string | null;
};

export type DiaryTimelineApi = {
  items: DiaryEventApi[];
  nextCursor: string | null;
  count: number;
};

export type DiaryPreAdvisorApi = {
  summary: string;
  eventCount: number;
  periodStart: string;
  periodEnd: string;
};

export type DiaryEventCreateRequest = {
  projectId: string;
  pageSlug: string;
  eventType: DiaryEventType;
  paperId?: string | null;
  payload?: Record<string, unknown>;
};

export type DiaryEventPatchRequest = {
  payload?: Record<string, unknown>;
  resolvedAt?: string | null;
};

export type DiaryTimelineFilters = {
  projectId?: string;
  pageSlug?: string;
  paperId?: string;
  cursor?: string;
};

// ── Adapters ───────────────────────────────────────────────────────────────
function adaptEvent(e: BackendDiaryEvent): DiaryEventApi {
  return {
    id: e.id,
    projectId: e.project_id,
    userId: e.user_id,
    pageSlug: e.page_slug,
    paperId: e.paper_id,
    eventType: e.event_type,
    payload: e.payload,
    createdAt: e.created_at,
    resolvedAt: e.resolved_at,
  };
}

// ── Calls ──────────────────────────────────────────────────────────────────
export async function createDiaryEvent(
  req: DiaryEventCreateRequest,
  signal?: AbortSignal,
): Promise<DiaryEventApi> {
  const body = {
    project_id: req.projectId,
    page_slug: req.pageSlug,
    event_type: req.eventType,
    paper_id: req.paperId ?? null,
    payload: req.payload ?? {},
  };
  const res = await apiFetch<BackendDiaryEvent>("/api/diary/event", {
    method: "POST",
    body,
    signal,
  });
  return adaptEvent(res);
}

export async function getDiaryTimeline(
  filters: DiaryTimelineFilters = {},
  signal?: AbortSignal,
): Promise<DiaryTimelineApi> {
  const params = new URLSearchParams();
  if (filters.projectId) params.set("project_id", filters.projectId);
  if (filters.pageSlug) params.set("page_slug", filters.pageSlug);
  if (filters.paperId) params.set("paper_id", filters.paperId);
  if (filters.cursor) params.set("cursor", filters.cursor);
  const query = params.toString();
  const path = query ? `/api/diary/timeline?${query}` : "/api/diary/timeline";
  const res = await apiFetch<BackendTimeline>(path, { signal });
  return {
    items: res.items.map(adaptEvent),
    nextCursor: res.next_cursor,
    count: res.count,
  };
}

export async function patchDiaryEvent(
  eventId: string,
  patch: DiaryEventPatchRequest,
  signal?: AbortSignal,
): Promise<DiaryEventApi> {
  const body: Record<string, unknown> = {};
  if (patch.payload !== undefined) body.payload = patch.payload;
  if (patch.resolvedAt !== undefined) body.resolved_at = patch.resolvedAt;
  const res = await apiFetch<BackendDiaryEvent>(
    `/api/diary/event/${eventId}`,
    { method: "PATCH", body, signal },
  );
  return adaptEvent(res);
}

export async function getPreAdvisorSummary(
  projectId: string,
  signal?: AbortSignal,
): Promise<DiaryPreAdvisorApi> {
  const res = await apiFetch<BackendPreAdvisor>(
    "/api/diary/pre-advisor-summary",
    { method: "POST", body: { project_id: projectId }, signal },
  );
  return {
    summary: res.summary,
    eventCount: res.event_count,
    periodStart: res.period_start,
    periodEnd: res.period_end,
  };
}

export { ApiError };
