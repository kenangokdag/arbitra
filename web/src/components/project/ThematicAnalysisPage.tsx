"use client";

import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { AdvisorBanner } from "@/components/project/AdvisorBanner";
import { DataVizCard } from "@/components/project/DataVizCard";
import { apiFetch } from "@/lib/api";

/* ---- API types (reuse gap-heatmap) ---- */
interface TopicItem { id: string; label: string; group: string; }
interface GapCellItem { method_id: string; topic_id: string; n_papers: number; gap_score: number; }
interface GapHeatmapResponse { methods: { id: string; label: string }[]; topics: TopicItem[]; cells: GapCellItem[]; }

const CLUSTER_COLORS = ["#4C78A8", "#54A24B", "#9D68B3", "#E45756", "#20B2AA", "#F58518", "#0E4F4A", "#E8A157"];

function seededRandom(seed: number): () => number {
  let s = seed;
  return () => {
    s = (s * 16807 + 0) % 2147483647;
    return s / 2147483647;
  };
}

interface ClusterDef { name: string; color: string; cx: number; cy: number; count: number; }

function buildClusters(topics: TopicItem[]): ClusterDef[] {
  const groupMap = new Map<string, number>();
  for (const t of topics) groupMap.set(t.group, (groupMap.get(t.group) ?? 0) + 1);

  const groups = [...groupMap.entries()].sort((a, b) => b[1] - a[1]);
  const rand = seededRandom(42);
  return groups.map(([name, count], i) => ({
    name,
    color: CLUSTER_COLORS[i % CLUSTER_COLORS.length]!,
    cx: 80 + (i % 3) * 200 + rand() * 60,
    cy: 80 + Math.floor(i / 3) * 160 + rand() * 40,
    count,
  }));
}

interface Dot { x: number; y: number; size: number; clusterIdx: number; }

function buildDots(clusters: ClusterDef[]): Dot[] {
  const rand = seededRandom(137);
  const dots: Dot[] = [];
  clusters.forEach((c, ci) => {
    for (let i = 0; i < Math.min(c.count * 2, 20); i++) {
      const angle = rand() * Math.PI * 2;
      const radius = rand() * 60 + 10;
      dots.push({
        x: Math.max(5, Math.min(590, c.cx + Math.cos(angle) * radius)),
        y: Math.max(5, Math.min(390, c.cy + Math.sin(angle) * radius)),
        size: 5 + rand() * 5,
        clusterIdx: ci,
      });
    }
  });
  return dots;
}

type ColorMode = "Tema" | "Yil" | "Atif";

export function ThematicAnalysisPage() {
  const [selectedCluster, setSelectedCluster] = useState<number | null>(null);
  const [colorMode, setColorMode] = useState<ColorMode>("Tema");
  const [opacity, setOpacity] = useState(70);

  // V1-S17 P004: proje paper_id'leri ile gap-heatmap'i daralt
  const params = useParams<{ id: string }>();
  const projectId = params?.id ?? "";

  const { data, isLoading } = useQuery({
    queryKey: ["gap-heatmap-themes", projectId],
    queryFn: () => {
      const qs = `top_methods=14&top_topics=30${projectId ? `&project_id=${encodeURIComponent(projectId)}` : ""}`;
      return apiFetch<GapHeatmapResponse>(`/api/gap-heatmap?${qs}`);
    },
    staleTime: 3600_000,
  });

  const clusters = useMemo(() => {
    if (!data?.topics?.length) return [];
    return buildClusters(data.topics);
  }, [data]);

  const dots = useMemo(() => buildDots(clusters), [clusters]);

  // Paper counts per group from real cells
  const groupPaperCount = useMemo(() => {
    if (!data) return new Map<string, number>();
    const topicGroup = new Map(data.topics.map((t) => [t.id, t.group]));
    const counts = new Map<string, number>();
    for (const cell of data.cells) {
      const grp = topicGroup.get(cell.topic_id) ?? "Diger";
      counts.set(grp, (counts.get(grp) ?? 0) + cell.n_papers);
    }
    return counts;
  }, [data]);

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <AdvisorBanner message="Konunun temadaki yerini gosteriyorum — markeri goruyor musun, beraber bakalim." />

      <DataVizCard title="Tematik Harita" badge="fact_gap_matrix M1" zoneTint="#E8A157">
        {isLoading ? (
          <div className="flex h-64 items-center justify-center gap-2 text-sm text-stone-500">
            <Loader2 className="h-5 w-5 animate-spin" />
            Tema verileri yukleniyor...
          </div>
        ) : (
          <div className="flex gap-5">
            {/* Cluster list */}
            <div className="w-[280px] flex-shrink-0 space-y-2">
              <h4 className="font-display mb-3 text-sm font-semibold text-stone-700">
                Tema Gruplari ({clusters.length})
              </h4>
              {clusters.map((cluster, idx) => (
                <button
                  key={idx}
                  onClick={() => setSelectedCluster(selectedCluster === idx ? null : idx)}
                  className="flex w-full items-center gap-3 rounded-xl border px-3 py-2.5 text-left transition-all"
                  style={{
                    borderColor: selectedCluster === idx ? "#E8A157" : "#e7e5e4",
                    background: selectedCluster === idx ? "#E8A15708" : "white",
                  }}
                >
                  <span className="h-3 w-3 flex-shrink-0 rounded-full" style={{ background: cluster.color }} />
                  <span className="flex-1 text-[13px] font-medium text-stone-700">{cluster.name}</span>
                  <span className="text-[11px] text-stone-400">
                    {groupPaperCount.get(cluster.name)?.toLocaleString() ?? cluster.count * 10} makale
                  </span>
                </button>
              ))}
            </div>

            {/* Scatter plot */}
            <div className="flex-1">
              <div
                className="relative overflow-hidden rounded-xl border border-stone-100 bg-stone-50"
                style={{ width: "100%", height: 400 }}
              >
                {dots.map((dot, i) => {
                  const cluster = clusters[dot.clusterIdx];
                  if (!cluster) return null;
                  const dimmed = selectedCluster !== null && dot.clusterIdx !== selectedCluster;
                  return (
                    <div
                      key={i}
                      className="absolute rounded-full transition-opacity"
                      style={{
                        left: `${(dot.x / 600) * 100}%`,
                        top: `${(dot.y / 400) * 100}%`,
                        width: dot.size,
                        height: dot.size,
                        background: cluster.color,
                        opacity: dimmed ? 0.12 : opacity / 100,
                      }}
                    />
                  );
                })}

                {clusters.map((cluster, idx) => (
                  <span
                    key={`lbl-${idx}`}
                    className="pointer-events-none absolute text-[10px] font-medium"
                    style={{
                      left: `${(cluster.cx / 600) * 100}%`,
                      top: `${(cluster.cy / 400) * 100}%`,
                      transform: "translate(-50%, -180%)",
                      color: cluster.color,
                      opacity: selectedCluster !== null && selectedCluster !== idx ? 0.3 : 1,
                    }}
                  >
                    {cluster.name}
                  </span>
                ))}

                {/* Your topic marker */}
                <div
                  className="absolute"
                  style={{ left: "51%", top: "47%", transform: "translate(-50%, -50%)" }}
                >
                  <div className="relative flex items-center justify-center" style={{ width: 16, height: 16 }}>
                    <span
                      className="absolute rounded-full"
                      style={{ width: 16, height: 16, border: "2px solid #E8A157", animation: "umapPulse 2s ease-in-out infinite" }}
                    />
                    <span className="absolute rounded-full" style={{ width: 6, height: 6, background: "#E8A157" }} />
                  </div>
                  <span className="absolute left-5 top-0 whitespace-nowrap text-[11px] font-semibold" style={{ color: "#E8A157" }}>
                    Konunuz
                  </span>
                </div>

                <style>{`
                  @keyframes umapPulse {
                    0%, 100% { transform: scale(1); opacity: 1; }
                    50% { transform: scale(1.8); opacity: 0.3; }
                  }
                `}</style>
              </div>

              {/* Controls */}
              <div className="mt-4 flex items-center gap-6">
                <label className="flex items-center gap-2 text-[13px] text-stone-600">
                  Renklendir:
                  <select
                    value={colorMode}
                    onChange={(e) => setColorMode(e.target.value as ColorMode)}
                    className="rounded-lg border border-stone-200 bg-white px-3 py-1.5 text-[13px] text-stone-700 outline-none focus:border-amber-300"
                  >
                    <option>Tema</option>
                    <option>Yil</option>
                    <option>Atif</option>
                  </select>
                </label>
                <label className="flex items-center gap-2 text-[13px] text-stone-600">
                  Opasite:
                  <input
                    type="range" min={20} max={100} value={opacity}
                    onChange={(e) => setOpacity(Number(e.target.value))}
                    className="h-1.5 w-28 cursor-pointer accent-amber-500"
                  />
                  <span className="w-8 text-right text-[12px] text-stone-400">{opacity}%</span>
                </label>
              </div>
            </div>
          </div>
        )}
      </DataVizCard>
    </div>
  );
}
