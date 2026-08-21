// kaynak: docs/plans/V1_S10_vitrin_tek_sayfa.md §6 KD-V1-S10-03
// V1-S10-03: useMutation wrapper — kullanıcı "Literatür Özeti Üret" butonuna basınca tetiklenir.
// Otomatik fetch YASAK (kota patlar); useQuery değil useMutation.
//
// N-14 (2026-05-27): /api/q/literature-review 12-24sn LLM-bound. AbortController ile
// kullanıcıya iptal hakkı veriyoruz; UI istek devam ederken "İptal" butonu gösterir.
// Audit: AUDIT_REPORT.md §11 N-14 / finding-H-LATENCY-1.

"use client";

import { useRef } from "react";
import { useMutation } from "@tanstack/react-query";

import {
  generateLitReview,
  type LitReviewRequest,
  type LitReviewResponseApi,
} from "@/lib/lit-review-api";

export function useLitReview() {
  const abortRef = useRef<AbortController | null>(null);

  const mutation = useMutation<LitReviewResponseApi, Error, LitReviewRequest>({
    mutationFn: (req) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      return generateLitReview(req, controller.signal);
    },
  });

  function abort() {
    abortRef.current?.abort();
    abortRef.current = null;
    mutation.reset();
  }

  return Object.assign(mutation, { abort });
}
