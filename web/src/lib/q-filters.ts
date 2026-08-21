// kaynak: docs/plans/V1_S10_vitrin_tek_sayfa.md §3 KD-V1-S10-07
// V1-S10-06: pure filter / sort / select-all helper'ları.
// PaperPreview field'larından üretilen — backend round-trip yok (year hariç,
// year /api/q'a gider).

import type { PaperPreviewApi } from "./q-api";

export type SortMode = "relevance" | "citations_desc" | "year_desc";

export type LocalFilters = {
  minCitations: number;
  hasAbstractOnly: boolean;
  sort: SortMode;
};

export const DEFAULT_LOCAL_FILTERS: LocalFilters = {
  minCitations: 0,
  hasAbstractOnly: false,
  sort: "relevance",
};

export function applyLocalFilters(
  papers: PaperPreviewApi[],
  filters: LocalFilters,
): PaperPreviewApi[] {
  const filtered = papers.filter((p) => {
    if (p.citedByCount < filters.minCitations) return false;
    if (filters.hasAbstractOnly && !p.abstract) return false;
    return true;
  });
  if (filters.sort === "citations_desc") {
    return [...filtered].sort((a, b) => b.citedByCount - a.citedByCount);
  }
  if (filters.sort === "year_desc") {
    return [...filtered].sort((a, b) => (b.year ?? 0) - (a.year ?? 0));
  }
  return filtered; // "relevance" = backend sıralaması korunur
}

/** Görünen listeden tier limit'e clamp ile ID set'i üret (anon=3, authed=25). */
export function selectAllClamped(
  visiblePapers: PaperPreviewApi[],
  maxSelect: number,
): Set<string> {
  return new Set(visiblePapers.slice(0, maxSelect).map((p) => p.id));
}

/** Görünen tümü işaretli mi? (clamp dahil — anon için ilk 3 yeterli). */
export function isAllVisibleSelected(
  visiblePapers: PaperPreviewApi[],
  selected: Set<string>,
  maxSelect: number,
): boolean {
  const expected = Math.min(visiblePapers.length, maxSelect);
  if (expected === 0) return false;
  return visiblePapers.slice(0, expected).every((p) => selected.has(p.id));
}
