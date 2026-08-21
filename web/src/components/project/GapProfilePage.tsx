"use client";

import { useState } from "react";
import {
  TrendingUp,
  ArrowUpRight,
  Plus,
  Grid3X3,
  Loader2,
} from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { AdvisorBanner } from "@/components/project/AdvisorBanner";
import { DataVizCard } from "@/components/project/DataVizCard";
import { apiFetch } from "@/lib/api";

const ZONE_TINT = "#0E4F4A";

interface GapSegment { label: string; value: number; description: string; }
interface TrendPoint { year: number; paper_count: number; c_k: number | null; }
interface GapProfileResponse {
  method_id: string; topic_id: string; topic_label: string;
  gap_value: number; depth_norm: number; neighbor: number;
  e_value: number; feasibility: number; publishability: number;
  segments: GapSegment[]; trend: TrendPoint[];
}

function gapScoreColor(score: number): string {
  if (score >= 0.7) return "#16a34a";
  if (score >= 0.5) return "#d97706";
  return "#dc2626";
}

export function GapProfilePage() {
  const params = useSearchParams();
  const methodId = params.get("method_id") ?? "";
  const topicId = params.get("topic_id") ?? "";
  const [compareList, setCompareList] = useState<string[]>([]);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["gap-profile", methodId, topicId],
    queryFn: () => apiFetch<GapProfileResponse>(
      `/api/gap-profile?method_id=${encodeURIComponent(methodId)}&topic_id=${encodeURIComponent(topicId)}`
    ),
    enabled: !!(methodId && topicId),
    staleTime: 3600_000,
  });

  const maxCount = Math.max(1, ...(data?.trend ?? []).map((d) => d.paper_count));

  if (!methodId || !topicId) {
    return (
      <div className="mx-auto max-w-7xl space-y-6 p-6">
        <AdvisorBanner message="Bir hucre sec — 5 yillik trendini, komsularini, ESTRA skorunu acayim." />
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6 text-center text-sm text-amber-700">
          Gap profili icin URL'e ?method_id=...&amp;topic_id=... ekleyin<br />
          (orn. GapHeatmap sayfasından bir hücreye tıklayın)
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <AdvisorBanner message="Bir hucre sec — 5 yillik trendini, komsularini, ESTRA skorunu acayim." />

      {/* Selected cell header */}
      <div
        className="flex items-center justify-between rounded-2xl border border-stone-200 bg-white px-6 py-5"
        style={{ boxShadow: "0 1px 3px rgba(0,0,0,0.06)" }}
      >
        <div className="flex items-center gap-5">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl" style={{ background: `${ZONE_TINT}15` }}>
            <Grid3X3 className="h-5 w-5" style={{ color: ZONE_TINT }} />
          </div>
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-stone-400">Secili Hucre</p>
            <h2 className="font-display text-lg font-semibold text-stone-900">
              {methodId.replace("_", " ").toUpperCase()} &times; {data?.topic_label ?? topicId}
            </h2>
          </div>
        </div>
        {isLoading ? (
          <Loader2 className="h-6 w-6 animate-spin text-stone-400" />
        ) : data ? (
          <div className="text-right">
            <p className="text-xs font-medium uppercase tracking-wider text-stone-400">Bosluk Skoru</p>
            <p className="font-display text-3xl font-bold" style={{ color: gapScoreColor(data.gap_value) }}>
              {data.gap_value.toFixed(2)}
            </p>
          </div>
        ) : null}
      </div>

      {isError && (
        <div className="rounded-2xl border border-red-100 bg-red-50 p-4 text-sm text-red-600">
          Gap profili yuklenemedi. Supabase baglantısını kontrol edin.
        </div>
      )}

      {data && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Left 2/3 */}
          <div className="space-y-6 lg:col-span-2">
            {/* Year trend */}
            <DataVizCard title="Yillik Yayin Trendi" subtitle={`${data.trend[0]?.year ?? ""} — ${data.trend[data.trend.length - 1]?.year ?? ""}`} badge="Trend" zoneTint={ZONE_TINT}>
              {data.trend.length === 0 ? (
                <p className="py-8 text-center text-sm text-stone-400">Bu tema icin yillik veri yok</p>
              ) : (
                <>
                  <div className="flex items-end gap-3" style={{ height: 180 }}>
                    {data.trend.map((d) => {
                      const h = Math.max(4, (d.paper_count / maxCount) * 150);
                      return (
                        <div key={d.year} className="flex flex-1 flex-col items-center gap-1.5">
                          <span className="text-xs font-medium text-stone-600">{d.paper_count}</span>
                          <div
                            className="w-full rounded-t-lg"
                            style={{ height: h, background: `linear-gradient(180deg, ${ZONE_TINT} 0%, ${ZONE_TINT}90 100%)` }}
                          />
                          <span className="text-[11px] text-stone-400">{d.year}</span>
                        </div>
                      );
                    })}
                  </div>
                  {data.trend.length >= 2 && (
                    <div className="mt-3 flex items-center gap-1.5 text-xs text-green-600">
                      <ArrowUpRight className="h-3.5 w-3.5" />
                      <span>
                        {data.trend[data.trend.length - 1]!.paper_count > data.trend[0]!.paper_count ? "Artan trend" : "Azalan trend"}
                      </span>
                    </div>
                  )}
                </>
              )}
            </DataVizCard>

            {/* Gap component breakdown */}
            <DataVizCard title="Gap Bilesenleri" subtitle="fact_gap_matrix' ten" zoneTint={ZONE_TINT}>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-[13px]">
                  <thead>
                    <tr className="border-b border-stone-100 text-xs font-medium uppercase tracking-wider text-stone-400">
                      <th className="pb-2 pr-4">Bilesen</th>
                      <th className="pb-2 pr-4">Skor</th>
                      <th className="pb-2">Aciklama</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.segments.map((seg) => (
                      <tr key={seg.label} className="border-b border-stone-50 last:border-0">
                        <td className="py-2.5 pr-4 font-medium text-stone-700">{seg.label}</td>
                        <td className="py-2.5 pr-4">
                          <div className="flex items-center gap-2">
                            <div className="h-1.5 w-20 overflow-hidden rounded-full bg-stone-100">
                              <div
                                className="h-full rounded-full"
                                style={{ width: `${seg.value * 100}%`, background: ZONE_TINT }}
                              />
                            </div>
                            <span className="font-mono text-[12px] text-stone-600">{seg.value.toFixed(2)}</span>
                          </div>
                        </td>
                        <td className="py-2.5 text-[12px] text-stone-400">{seg.description}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </DataVizCard>
          </div>

          {/* Right 1/3 */}
          <div className="space-y-6">
            {/* ESTRA bar chart */}
            <DataVizCard title="Skor Dagalimi" zoneTint={ZONE_TINT}>
              <div className="space-y-3">
                {data.segments.map((seg, i) => {
                  const colors = ["#0E4F4A", "#14665D", "#1A7D71", "#2D9B8E", "#3DB5A6", "#5ECEC2"];
                  return (
                    <div key={seg.label} className="flex items-center gap-3">
                      <span className="w-24 truncate text-right text-[11px] font-medium text-stone-500">{seg.label}</span>
                      <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-stone-100">
                        <div
                          className="h-full rounded-full transition-all"
                          style={{ width: `${seg.value * 100}%`, background: colors[i % colors.length] }}
                        />
                      </div>
                      <span className="w-8 text-xs font-medium text-stone-600">{seg.value.toFixed(2)}</span>
                    </div>
                  );
                })}
              </div>
            </DataVizCard>

            {/* Raw values */}
            <DataVizCard title="Ham Degerler" zoneTint={ZONE_TINT}>
              <dl className="space-y-2 text-sm">
                {[
                  ["gap_value", data.gap_value],
                  ["depth_norm", data.depth_norm],
                  ["neighbor", data.neighbor],
                  ["e_value", data.e_value],
                  ["feasibility", data.feasibility],
                  ["publishability", data.publishability],
                ].map(([k, v]) => (
                  <div key={k as string} className="flex justify-between">
                    <dt className="font-mono text-xs text-stone-400">{k as string}</dt>
                    <dd className="font-mono text-xs font-semibold text-stone-700">{(v as number).toFixed(4)}</dd>
                  </div>
                ))}
              </dl>
            </DataVizCard>

            <button
              onClick={() => {
                const key = `${methodId} × ${topicId}`;
                if (compareList.length < 3 && !compareList.includes(key)) {
                  setCompareList([...compareList, key]);
                }
              }}
              disabled={compareList.length >= 3}
              className="flex w-full items-center justify-center gap-2 rounded-xl border border-stone-200 bg-white px-4 py-3 text-[13px] font-medium text-stone-600 transition-colors hover:bg-stone-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Plus className="h-4 w-4" />
              Karsilastirmaya ekle ({compareList.length}/3)
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
