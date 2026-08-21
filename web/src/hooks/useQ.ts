// kaynak: docs/plans/V1_S8_q_wire.md §4 + V1_S10_vitrin_tek_sayfa.md §3 KD-V1-S10-07
// V1-S8-01: Q preview TanStack Query wrapper.
// V1-S10-06: yearFrom/yearTo opsiyonel — UI'da yıl filter form submit'te /api/q'a gider.
// `enabled = false` → query<2 char için fetch atılmaz; staleTime 5dk Q1/Q3 simetrisi.

"use client";

import { useQuery } from "@tanstack/react-query";

import { fetchQ, type QLang, type QResponseApi } from "@/lib/q-api";

type UseQArgs = {
  query: string;
  lang?: QLang;
  yearFrom?: number;
  yearTo?: number;
  enabled: boolean;
};

export function useQ(args: UseQArgs) {
  const { query, lang = "tr", yearFrom, yearTo, enabled } = args;
  return useQuery<QResponseApi, Error>({
    queryKey: ["q-preview", query, lang, yearFrom ?? null, yearTo ?? null],
    queryFn: ({ signal }) =>
      fetchQ({ query, lang, yearFrom, yearTo }, signal),
    enabled: enabled && query.length >= 2,
    staleTime: 5 * 60 * 1000,
  });
}
