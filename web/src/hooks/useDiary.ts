/**
 * F13-S1-P005 — diary React Query hooks.
 * kaynak: docs/plans/F13_sayfa_plani_v2_implementation.md §3 (F13-S1-P005)
 *
 * useQ / useLitReview patternı (V1-S8 / V1-S10).
 * Mutation onSuccess'ta timeline cache invalidation.
 */

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  createDiaryEvent,
  getDiaryTimeline,
  getPreAdvisorSummary,
  patchDiaryEvent,
  type DiaryEventCreateRequest,
  type DiaryEventPatchRequest,
  type DiaryTimelineFilters,
} from "@/lib/diary-api";

const TIMELINE_KEY = "diary-timeline";

function timelineKey(filters: DiaryTimelineFilters) {
  return [
    TIMELINE_KEY,
    filters.projectId ?? null,
    filters.pageSlug ?? null,
    filters.paperId ?? null,
    filters.cursor ?? null,
  ];
}

export function useDiaryTimeline(
  filters: DiaryTimelineFilters,
  options: { enabled?: boolean } = {},
) {
  return useQuery({
    queryKey: timelineKey(filters),
    queryFn: ({ signal }) => getDiaryTimeline(filters, signal),
    enabled: options.enabled ?? Boolean(filters.projectId),
  });
}

export function useCreateDiaryEvent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (req: DiaryEventCreateRequest) => createDiaryEvent(req),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [TIMELINE_KEY] });
    },
  });
}

export function usePatchDiaryEvent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { eventId: string; patch: DiaryEventPatchRequest }) =>
      patchDiaryEvent(vars.eventId, vars.patch),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [TIMELINE_KEY] });
    },
  });
}

export function usePreAdvisorSummary() {
  return useMutation({
    mutationFn: (projectId: string) => getPreAdvisorSummary(projectId),
  });
}
