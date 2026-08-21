// F14 Hakemlik — TanStack Query hook'ları.
// useReviewStatus: done/failed olana kadar ~2sn poll; sonra durur.
// useReviewReport: status === "done" iken raporu çeker (enabled gate).

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  fetchAdminJobs,
  fetchAdminStats,
  fetchReviewReport,
  fetchReviewStatus,
  fetchTheme,
  fetchVersionComparison,
  updateTheme,
  type AdminJobsResponse,
  type AdminStats,
  type ReviewReportResponse,
  type ReviewStatusResponse,
  type ThemeSettings,
  type ThemeUpdate,
  type VersionComparisonResponse,
} from "@/lib/review-api";

export const THEME_QUERY_KEY = ["app-theme"] as const;

const TERMINAL = new Set(["done", "failed"]);

export function useReviewStatus(jobId: string, enabled = true) {
  return useQuery<ReviewStatusResponse, Error>({
    queryKey: ["review-status", jobId],
    queryFn: ({ signal }) => fetchReviewStatus(jobId, signal),
    enabled: enabled && jobId.length > 0,
    // Terminal duruma gelince poll'ü durdur.
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status && TERMINAL.has(status)) return false;
      return 2000;
    },
    staleTime: 0,
    gcTime: 0,
  });
}

export function useReviewReport(jobId: string, enabled: boolean) {
  return useQuery<ReviewReportResponse, Error>({
    queryKey: ["review-report", jobId],
    queryFn: ({ signal }) => fetchReviewReport(jobId, signal),
    enabled: enabled && jobId.length > 0,
    staleTime: Infinity,
  });
}

/** VERSIYON_KARSILASTIRMA_FAZ1_2026-08-17 §3.4 — useReviewReport'un BİREBİR
 *  aynı deseni. ReviewReportView kendi içinde useQuery ÇAĞIRMAZ (mevcut 41
 *  testin hiçbiri QueryClientProvider'sız render ediyor) — veri burada
 *  çekilip prop olarak geçilir. */
export function useVersionComparison(jobId: string, enabled: boolean) {
  return useQuery<VersionComparisonResponse, Error>({
    queryKey: ["review-comparison", jobId],
    queryFn: ({ signal }) => fetchVersionComparison(jobId, signal),
    enabled: enabled && jobId.length > 0,
    staleTime: Infinity,
  });
}

export function useAdminJobs() {
  return useQuery<AdminJobsResponse, Error>({
    queryKey: ["review-admin-jobs"],
    queryFn: ({ signal }) => fetchAdminJobs(signal),
    refetchInterval: 5000,
    staleTime: 0,
  });
}

export function useAdminStats() {
  return useQuery<AdminStats, Error>({
    queryKey: ["review-admin-stats"],
    queryFn: ({ signal }) => fetchAdminStats(signal),
    refetchInterval: 5000,
    staleTime: 0,
  });
}

// --- global tema ----------------------------------------------------------

/** Açılışta tek sefer okunur (public GET); 5 dk taze sayılır → gereksiz refetch yok. */
export function useTheme() {
  return useQuery<ThemeSettings, Error>({
    queryKey: THEME_QUERY_KEY,
    queryFn: ({ signal }) => fetchTheme(signal),
    staleTime: 5 * 60 * 1000,
  });
}

/** Admin formu — PATCH; başarıda cache'i yeni temayla günceller + invalidate eder
 *  (ThemeProvider yeniden uygular). */
export function useUpdateTheme() {
  const queryClient = useQueryClient();
  return useMutation<ThemeSettings, Error, ThemeUpdate>({
    mutationFn: (body) => updateTheme(body),
    onSuccess: (data) => {
      queryClient.setQueryData(THEME_QUERY_KEY, data);
      void queryClient.invalidateQueries({ queryKey: THEME_QUERY_KEY });
    },
  });
}
