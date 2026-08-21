"use client";

import { useState } from "react";
import { ExternalLink, Plus, ChevronRight, Loader2 } from "lucide-react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { AdvisorBanner } from "@/components/project/AdvisorBanner";
import { DataVizCard } from "@/components/project/DataVizCard";
import { apiFetch } from "@/lib/api";

interface ConnectedPaper {
  paper_id: string;
  title: string;
  cosine_score: number;
  raw_count: number;
  rank: number;
}

interface ConnectedPapersResponse {
  source_paper_id: string;
  neighbors: ConnectedPaper[];
  total: number;
}

// V1-S17 P008 — proje anchor default: GET /api/project/{id}/cluster/status
interface ClusterStatusResponse {
  project_id: string;
  anchor_paper_id: string | null;
  cluster_status: "pending" | "expanding" | "ready" | "failed";
  cluster_size: number;
}

interface GraphNode {
  id: string;
  title: string;
  cosineScore: number;
  x: number;
  y: number;
}

const CX = 340;
const CY = 240;
const RADIUS = 200;

function buildGraphNodes(neighbors: ConnectedPaper[], maxNodes = 15): GraphNode[] {
  const visible = neighbors.slice(0, maxNodes);
  const angleStep = (2 * Math.PI) / (visible.length || 1);
  return visible.map((n, i) => {
    const angle = i * angleStep - Math.PI / 2;
    return {
      id: n.paper_id,
      title: n.title,
      cosineScore: n.cosine_score,
      x: CX + RADIUS * Math.cos(angle),
      y: CY + RADIUS * Math.sin(angle),
    };
  });
}

const CONNECTED_PAPERS_TOP_K = 15;

export function ConnectedPapersPage() {
  const params = useSearchParams();
  const routeParams = useParams<{ id: string }>();
  const projectId = routeParams?.id ?? "";
  const urlPaperId = params.get("paper_id") ?? "";
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  // V1-S17 P008 RC3 — proje anchor default'u getir (cluster_status='ready' ise).
  const { data: cluster } = useQuery({
    queryKey: ["cluster-status", projectId],
    queryFn: () =>
      apiFetch<ClusterStatusResponse>(`/api/project/${projectId}/cluster/status`),
    enabled: !!projectId,
    staleTime: 60_000,
    retry: false,
  });

  const anchorPaperId = cluster?.anchor_paper_id ?? "";
  const paperId = urlPaperId || anchorPaperId;
  const isAnchorDefault = !urlPaperId && !!anchorPaperId;

  const { data, isLoading, isError } = useQuery({
    queryKey: ["connected-papers", paperId],
    queryFn: () => apiFetch<ConnectedPapersResponse>(`/api/connected-papers/${paperId}?top_k=${CONNECTED_PAPERS_TOP_K}`),
    enabled: !!paperId,
    staleTime: 3600_000,
  });

  const graphNodes = buildGraphNodes(data?.neighbors ?? []);

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <AdvisorBanner message="Bir paper sec — ona bagli diger calismalari graph olarak acayim. 833M atif baglantisinin ustunden." />

      {!paperId && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6 text-center text-sm text-amber-700">
          {projectId
            ? "Proje cap'asi henuz kilitlenmedi. Once 'Arastirma Alani' adimini tamamla veya URL'e ?paper_id=W... ekle."
            : "Paper baglantilari icin URL'e ?paper_id=W... ekleyin"}
        </div>
      )}

      {paperId && (
        <>
          {/* Source paper header */}
          <div
            className="rounded-2xl border-2 bg-white px-5 py-4"
            style={{ borderColor: "#E8A157", boxShadow: "0 1px 3px rgba(0,0,0,0.06)" }}
          >
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="font-display text-sm font-semibold text-stone-800">
                  {paperId}
                </p>
                <p className="mt-1 text-xs text-stone-500">
                  {data ? `${data.total} bibliographic coupling neighbor bulundu` : "Yuklenıyor..."}
                </p>
              </div>
              {/* V1-S17 P008 — picker affordance: anchor vs URL override hint */}
              {isAnchorDefault && (
                <span className="rounded-full bg-amber-50 px-2 py-1 text-[10px] font-medium text-amber-700">
                  proje capasi
                </span>
              )}
              {!isAnchorDefault && anchorPaperId && anchorPaperId !== paperId && (
                <Link
                  href={`/project/${projectId}/curation-2`}
                  className="rounded-full bg-stone-100 px-2 py-1 text-[10px] font-medium text-stone-600 transition-colors hover:bg-stone-200"
                >
                  capaya don ({anchorPaperId})
                </Link>
              )}
            </div>
          </div>

          {/* Graph + detail panel */}
          <div className="flex gap-6">
            <div className="flex-1">
              <DataVizCard title="Bibliographic Coupling Grafi" badge="fact_paper_bibcoupling_top50" zoneTint="#E8A157">
                {isLoading && (
                  <div className="flex h-64 items-center justify-center gap-2 text-sm text-stone-500">
                    <Loader2 className="h-5 w-5 animate-spin" />
                    Graf yukleniyor...
                  </div>
                )}

                {isError && (
                  <div className="flex h-32 items-center justify-center text-sm text-red-500">
                    Baglantili paper&apos;lar yuklenemedi
                  </div>
                )}

                {data && graphNodes.length > 0 && (
                  <svg viewBox="0 0 680 480" className="w-full" style={{ minHeight: 420 }}>
                    {/* Lines */}
                    {graphNodes.map((n) => (
                      <line
                        key={`line-${n.id}`}
                        x1={CX} y1={CY} x2={n.x} y2={n.y}
                        stroke="#5EAAA8"
                        strokeWidth={hoveredId === n.id ? 2.5 : 1.2}
                        strokeOpacity={hoveredId === n.id ? 0.8 : Math.max(0.2, n.cosineScore)}
                      />
                    ))}

                    {/* Center node */}
                    <circle cx={CX} cy={CY} r={38} fill="#FFF7ED" stroke="#E8A157" strokeWidth={3} />
                    <foreignObject x={CX - 32} y={CY - 24} width={64} height={48}>
                      <div className="flex h-full flex-col items-center justify-center text-center">
                        <span className="font-display text-[8px] font-semibold leading-tight text-stone-800">
                          {paperId.length > 12 ? paperId.slice(0, 12) : paperId}
                        </span>
                        <span className="mt-0.5 text-[7px] text-stone-500">kaynak</span>
                      </div>
                    </foreignObject>

                    {/* Neighbor nodes */}
                    {graphNodes.map((n) => {
                      const r = hoveredId === n.id ? 28 : 24;
                      const score = Math.round(n.cosineScore * 100);
                      return (
                        <g
                          key={n.id}
                          onMouseEnter={() => setHoveredId(n.id)}
                          onMouseLeave={() => setHoveredId(null)}
                          onClick={() => setSelectedNode(n)}
                          className="cursor-pointer"
                        >
                          <circle
                            cx={n.x} cy={n.y} r={r}
                            fill="#E8F5F4"
                            stroke="#5EAAA8"
                            strokeWidth={hoveredId === n.id ? 2.5 : 1.5}
                          />
                          <foreignObject x={n.x - 22} y={n.y - 18} width={44} height={36}>
                            <div className="flex h-full flex-col items-center justify-center text-center">
                              <span className="text-[7px] font-medium leading-tight text-stone-700">
                                {n.title.length > 22 ? n.title.slice(0, 22) + "…" : n.title}
                              </span>
                              <span className="text-[7px] text-stone-400">{score}%</span>
                            </div>
                          </foreignObject>
                        </g>
                      );
                    })}

                    {/* Hover tooltip */}
                    {hoveredId && (() => {
                      const node = graphNodes.find((n) => n.id === hoveredId);
                      if (!node) return null;
                      const tx = node.x > CX ? node.x - 140 : node.x + 32;
                      const ty = Math.max(10, node.y - 36);
                      return (
                        <foreignObject x={tx} y={ty} width={148} height={72}>
                          <div className="rounded-lg border border-stone-200 bg-white p-2 text-[10px] shadow-md">
                            <p className="font-semibold text-stone-800">{node.title.slice(0, 60)}</p>
                            <p className="text-stone-500">Cosine: {Math.round(node.cosineScore * 100)}%</p>
                            <p className="text-stone-400 font-mono">{node.id}</p>
                          </div>
                        </foreignObject>
                      );
                    })()}
                  </svg>
                )}
              </DataVizCard>
            </div>

            {/* Detail panel */}
            <div className="w-[280px] flex-shrink-0">
              <div
                className="sticky top-6 rounded-2xl border border-stone-200 bg-white p-5"
                style={{ boxShadow: "0 1px 3px rgba(0,0,0,0.06)" }}
              >
                {selectedNode ? (
                  <>
                    <h4 className="font-display text-sm font-semibold text-stone-800">
                      {selectedNode.title}
                    </h4>
                    <p className="mt-1 font-mono text-xs text-stone-400">{selectedNode.id}</p>
                    <p className="mt-0.5 text-xs text-stone-500">
                      Cosine benzerlik: {Math.round(selectedNode.cosineScore * 100)}%
                    </p>

                    <div className="mt-4">
                      <div className="mb-1 text-[11px] text-stone-500">Bibliographic coupling gücü</div>
                      <div className="h-2 overflow-hidden rounded-full bg-stone-100">
                        <div
                          className="h-full rounded-full"
                          style={{ width: `${Math.round(selectedNode.cosineScore * 100)}%`, background: "#5EAAA8" }}
                        />
                      </div>
                    </div>

                    {/* V1-S17 P009 RC5 — "Incele" Link aktif: /paper/{paper_id} */}
                    <div className="mt-5 flex gap-2">
                      <Link
                        href={`/paper/${selectedNode.id}`}
                        className="flex flex-1 items-center justify-center gap-1 rounded-lg py-2 text-xs font-medium text-white transition-colors hover:opacity-90"
                        style={{ background: "#E8A157" }}
                      >
                        <ExternalLink className="h-3 w-3" /> Incele
                      </Link>
                      <button className="flex flex-1 items-center justify-center gap-1 rounded-lg border border-stone-200 bg-white py-2 text-xs font-medium text-stone-600 transition-colors hover:bg-stone-50">
                        <Plus className="h-3 w-3" /> Listeme ekle
                      </button>
                    </div>
                  </>
                ) : (
                  <div className="flex flex-col items-center justify-center py-10 text-center">
                    <ChevronRight className="mb-2 h-6 w-6 text-stone-300" />
                    <p className="text-xs text-stone-400">Detay gormek icin grafikteki bir dugume tikla</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
