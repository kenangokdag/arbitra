"use client";

// V1-S17 P010 (KD-V1-S17-05) — curation-1 yeni içerik: anchor + ESTRA top-5
// önerilen literatür. cluster_status'a göre 3-yol render: pending/expanding
// (spinner + 5s poll), failed (error banner), ready (PaperCard compact top-5).

import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ExternalLink, Loader2, AlertTriangle, Anchor } from "lucide-react";

import { AdvisorBanner } from "@/components/project/AdvisorBanner";
import { apiFetch } from "@/lib/api";

interface ClusterStatusResponse {
  project_id: string;
  anchor_paper_id: string | null;
  cluster_status: "pending" | "expanding" | "ready" | "failed";
  cluster_size: number;
  cluster_error?: Record<string, string> | null;
}

interface ProjectPaperItem {
  paper_id: string;
  title: string;
  abstract: string | null;
  authors: string[];
  year: number | null;
  venue: string | null;
  doi: string | null;
  citations_count: number;
}

interface ProjectPapersResponse {
  project_id: string;
  papers: ProjectPaperItem[];
  hydrated_count: number;
}

const POLL_INTERVAL_MS = 5_000;

export function AnchorRecommendationsPage() {
  const params = useParams<{ id: string }>();
  const projectId = params?.id ?? "";

  const statusQuery = useQuery({
    queryKey: ["cluster-status", projectId],
    queryFn: () =>
      apiFetch<ClusterStatusResponse>(`/api/project/${projectId}/cluster/status`),
    enabled: !!projectId,
    refetchInterval: (q) => {
      const s = q.state.data?.cluster_status;
      return s === "pending" || s === "expanding" ? POLL_INTERVAL_MS : false;
    },
  });

  const status = statusQuery.data?.cluster_status;
  const isReady = status === "ready";

  const papersQuery = useQuery({
    queryKey: ["project-papers-cluster", projectId, 5],
    queryFn: () =>
      apiFetch<ProjectPapersResponse>(
        `/api/project/${projectId}/papers?rank_max=5`,
      ),
    enabled: !!projectId && isReady,
    staleTime: 600_000,
  });

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <AdvisorBanner message="Cap'ana göre top-5 ilgili literatür. Stage C clustering tamamlandiktan sonra liste yenilenir." />

      {statusQuery.isLoading && (
        <div
          data-testid="anchor-recs-status-loading"
          className="flex items-center gap-2 rounded-2xl border border-stone-200 bg-white p-6 text-sm text-stone-500"
        >
          <Loader2 className="h-4 w-4 animate-spin" /> Çapa durumu kontrol ediliyor…
        </div>
      )}

      {statusQuery.isError && (
        <div
          data-testid="anchor-recs-status-error"
          className="rounded-2xl border border-red-200 bg-red-50 p-6 text-sm text-red-700"
        >
          Çapa durumu okunamadi. Sayfayi yenile.
        </div>
      )}

      {statusQuery.data && (status === "pending" || status === "expanding") && (
        <div
          data-testid="anchor-recs-pending"
          className="flex items-center gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-6"
        >
          <Loader2 className="h-5 w-5 animate-spin text-amber-700" />
          <div>
            <p className="text-sm font-semibold text-amber-800">
              Cluster genisliyor…
            </p>
            <p className="mt-1 text-xs text-amber-700">
              Anchor saptandi (
              <span className="font-mono">
                {statusQuery.data.anchor_paper_id ?? "—"}
              </span>
              ). Stage C 50 makale icin RRF + reranker calistiriyor (~3-5s).
            </p>
          </div>
        </div>
      )}

      {statusQuery.data && status === "failed" && (
        <div
          data-testid="anchor-recs-failed"
          className="rounded-2xl border border-red-200 bg-red-50 p-6"
        >
          <div className="flex items-center gap-2 text-sm font-semibold text-red-800">
            <AlertTriangle className="h-4 w-4" /> Cluster expand basarisiz
          </div>
          <p className="mt-2 text-xs text-red-700">
            {statusQuery.data.cluster_error?.reason ??
              "Bilinmeyen hata. discovery-1 'Arastirma Alani' adimindan tekrar capa sec."}
          </p>
          <Link
            href={`/project/${projectId}/discovery-1`}
            className="mt-3 inline-flex items-center gap-1 rounded-lg bg-red-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-700"
          >
            Capa secimine don
          </Link>
        </div>
      )}

      {statusQuery.data && isReady && (
        <div data-testid="anchor-recs-ready" className="space-y-4">
          <div
            className="rounded-2xl border-2 bg-white px-5 py-4"
            style={{ borderColor: "#E8A157" }}
          >
            <div className="flex items-center gap-2">
              <Anchor className="h-4 w-4 text-amber-700" />
              <span className="font-display text-sm font-semibold text-stone-800">
                Cap'a: {statusQuery.data.anchor_paper_id ?? "—"}
              </span>
            </div>
            <p className="mt-1 text-xs text-stone-500">
              Cluster boyutu: {statusQuery.data.cluster_size} makale (top-5
              gosteriliyor)
            </p>
          </div>

          {papersQuery.isLoading && (
            <div className="flex items-center gap-2 text-sm text-stone-500">
              <Loader2 className="h-4 w-4 animate-spin" /> Top-5 yukleniyor…
            </div>
          )}

          {papersQuery.data && papersQuery.data.papers.length === 0 && (
            <p
              data-testid="anchor-recs-empty"
              className="rounded-xl border border-stone-200 bg-stone-50 p-4 text-sm text-stone-500"
            >
              Cluster bos. discovery-1 capa secimini yeniden tetikle.
            </p>
          )}

          {papersQuery.data && papersQuery.data.papers.length > 0 && (
            <ul className="space-y-3">
              {papersQuery.data.papers.map((p, i) => (
                <li
                  key={p.paper_id}
                  className="rounded-xl border border-stone-200 bg-white p-4"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="font-mono text-[10px] text-stone-400">
                        #{i + 1} · {p.paper_id}
                      </p>
                      <h4 className="mt-0.5 font-display text-sm font-semibold leading-snug text-stone-800">
                        {p.title}
                      </h4>
                      <p className="mt-1 text-xs text-stone-500">
                        {p.authors.slice(0, 3).join(", ")}
                        {p.authors.length > 3 ? " et al." : ""}
                        {p.year ? ` · ${p.year}` : ""}
                        {p.venue ? ` · ${p.venue}` : ""}
                      </p>
                    </div>
                    <Link
                      href={`/paper/${p.paper_id}`}
                      className="flex flex-shrink-0 items-center gap-1 rounded-lg bg-amber-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-700"
                    >
                      <ExternalLink className="h-3 w-3" /> Incele
                    </Link>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
