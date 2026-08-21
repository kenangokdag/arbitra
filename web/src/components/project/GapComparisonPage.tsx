"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import {
  Plus,
  Trash2,
  Scale,
  Loader2,
  AlertTriangle,
  BookOpen,
  Sparkles,
} from "lucide-react";
import { AdvisorBanner } from "@/components/project/AdvisorBanner";
import { DataVizCard } from "@/components/project/DataVizCard";
import { apiFetch, ApiError } from "@/lib/api";

// F13-S4.1 — 4.4 Çalışma Karşılaştırma (POST /api/workshop/compare).
// 2-5 gap hücresi + 5 boyutlu weights → CompareResponse + LLM önerisi.

const ZONE_TINT = "#0E4F4A";

const AXES: { key: keyof Weights; label: string }[] = [
  { key: "risk", label: "Risk" },
  { key: "disruption", label: "Yıkıcılık" },
  { key: "virgin", label: "Bakirlik" },
  { key: "sleeping_beauty", label: "Uyuyan Güzel" },
  { key: "publishability", label: "Yayımlanabilirlik" },
];

interface Weights {
  risk: number;
  disruption: number;
  virgin: number;
  sleeping_beauty: number;
  publishability: number;
}

interface GapCellRef {
  matrix_id: string;
  axis_x: string;
  axis_y: string;
}

interface GapAxisScores {
  risk: number;
  disruption: number;
  virgin: number;
  sleeping_beauty: number;
  publishability: number;
}

interface GapTopPaper {
  paper_id: string;
  title: string | null;
  year: number | null;
  venue: string | null;
  q_weak: number | null;
}

interface CompareGapRow {
  cell: GapCellRef;
  axes: GapAxisScores;
  weighted_score: number;
  top_papers: GapTopPaper[];
}

interface CompareResponse {
  gaps: CompareGapRow[];
  weights: Weights;
  recommendation_text: string | null;
}

const DEFAULT_WEIGHTS: Weights = {
  risk: 0.2,
  disruption: 0.2,
  virgin: 0.2,
  sleeping_beauty: 0.2,
  publishability: 0.2,
};

function scoreColor(score: number, inverted = false): string {
  const effective = inverted ? 1 - score : score;
  if (effective >= 0.7) return "#16a34a";
  if (effective >= 0.4) return "#d97706";
  return "#dc2626";
}

function ScoreBar({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between">
        <span className="text-xs font-medium text-stone-500">{label}</span>
        <span className="text-sm font-bold" style={{ color }}>
          {value.toFixed(2)}
        </span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-stone-100">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${Math.max(0, Math.min(1, value)) * 100}%`, background: color }}
        />
      </div>
    </div>
  );
}

export function GapComparisonPage() {
  const params = useParams<{ id: string }>();
  const projectId = params?.id;

  const [cells, setCells] = useState<GapCellRef[]>([
    { matrix_id: "M1", axis_x: "", axis_y: "" },
    { matrix_id: "M1", axis_x: "", axis_y: "" },
  ]);
  const [weights, setWeights] = useState<Weights>(DEFAULT_WEIGHTS);
  const [result, setResult] = useState<CompareResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function updateCell(index: number, patch: Partial<GapCellRef>) {
    setCells((prev) => prev.map((c, i) => (i === index ? { ...c, ...patch } : c)));
  }

  function addCell() {
    if (cells.length >= 5) return;
    setCells((prev) => [...prev, { matrix_id: "M1", axis_x: "", axis_y: "" }]);
  }

  function removeCell(index: number) {
    if (cells.length <= 2) return;
    setCells((prev) => prev.filter((_, i) => i !== index));
  }

  function updateWeight(key: keyof Weights, value: number) {
    setWeights((prev) => ({ ...prev, [key]: value }));
  }

  const canSubmit =
    !!projectId &&
    cells.length >= 2 &&
    cells.length <= 5 &&
    cells.every((c) => c.matrix_id.trim() && c.axis_x.trim() && c.axis_y.trim()) &&
    !busy;

  async function runCompare() {
    if (!projectId || !canSubmit) return;
    setBusy(true);
    setError(null);
    try {
      const data = await apiFetch<CompareResponse>("/api/workshop/compare", {
        method: "POST",
        body: { project_id: projectId, gap_cells: cells, weights },
      });
      setResult(data);
    } catch (e: unknown) {
      setError(e instanceof ApiError ? `Karşılaştırma hatası (${e.status})` : "Karşılaştırma hatası");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <AdvisorBanner message="Üç boşluğu yan yana koyalım — riski, yıkıcılığı, bakirliği karşılaştır." />

      {error && (
        <div className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Form: cells + weights */}
      <div className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="font-display mb-3 text-base font-semibold text-stone-800">
          Karşılaştırılacak boşluklar (2-5)
        </h3>
        <div className="space-y-2">
          {cells.map((c, i) => (
            <div key={i} className="flex flex-wrap items-center gap-2">
              <span className="w-6 text-xs font-mono text-stone-400">#{i + 1}</span>
              <input
                type="text"
                value={c.matrix_id}
                onChange={(e) => updateCell(i, { matrix_id: e.target.value })}
                placeholder="matrix_id"
                className="w-24 rounded-lg border border-stone-200 px-2 py-1.5 text-sm focus:border-stone-400 focus:outline-none"
              />
              <input
                type="text"
                value={c.axis_x}
                onChange={(e) => updateCell(i, { axis_x: e.target.value })}
                placeholder="axis_x (örn. TOPSIS)"
                className="flex-1 min-w-[150px] rounded-lg border border-stone-200 px-2 py-1.5 text-sm focus:border-stone-400 focus:outline-none"
              />
              <input
                type="text"
                value={c.axis_y}
                onChange={(e) => updateCell(i, { axis_y: e.target.value })}
                placeholder="axis_y (örn. ESG)"
                className="flex-1 min-w-[150px] rounded-lg border border-stone-200 px-2 py-1.5 text-sm focus:border-stone-400 focus:outline-none"
              />
              <button
                type="button"
                onClick={() => removeCell(i)}
                disabled={cells.length <= 2}
                aria-label={`hücre ${i + 1} sil`}
                className="rounded-lg p-1.5 text-stone-400 hover:text-red-600 disabled:opacity-30"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
        <button
          type="button"
          onClick={addCell}
          disabled={cells.length >= 5}
          className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-dashed border-stone-300 px-3 py-1.5 text-xs font-medium text-stone-600 hover:border-stone-400 disabled:opacity-30"
        >
          <Plus className="h-3.5 w-3.5" />
          Hücre ekle
        </button>

        <h4 className="font-display mt-5 mb-2 text-sm font-semibold text-stone-700">
          Ağırlıklar (5 eksen, 0-1)
        </h4>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-5">
          {AXES.map((a) => (
            <label key={a.key} className="flex flex-col gap-1 text-xs">
              <span className="text-stone-500">{a.label}</span>
              <input
                type="number"
                min={0}
                max={1}
                step={0.05}
                value={weights[a.key]}
                onChange={(e) => updateWeight(a.key, Number(e.target.value))}
                aria-label={`${a.label} ağırlığı`}
                className="rounded-lg border border-stone-200 px-2 py-1.5 text-sm focus:border-stone-400 focus:outline-none"
              />
            </label>
          ))}
        </div>

        <button
          type="button"
          onClick={runCompare}
          disabled={!canSubmit}
          className="mt-4 inline-flex items-center gap-2 rounded-xl px-6 py-2.5 text-sm font-semibold text-white shadow-sm transition-all hover:shadow-md disabled:opacity-40"
          style={{
            background: `linear-gradient(135deg, ${ZONE_TINT} 0%, #1A7D71 100%)`,
          }}
        >
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Scale className="h-4 w-4" />}
          Karşılaştır
        </button>
      </div>

      {/* Result cards */}
      {result && (
        <>
          <div
            className={`grid grid-cols-1 gap-6 ${result.gaps.length >= 3 ? "md:grid-cols-3" : "md:grid-cols-2"}`}
          >
            {result.gaps.map((row) => (
              <DataVizCard
                key={`${row.cell.matrix_id}-${row.cell.axis_x}-${row.cell.axis_y}`}
                title={`${row.cell.axis_x} × ${row.cell.axis_y}`}
                zoneTint={ZONE_TINT}
              >
                <div className="space-y-5">
                  <div className="space-y-3">
                    {AXES.map((a) => (
                      <ScoreBar
                        key={a.key}
                        label={a.label}
                        value={row.axes[a.key]}
                        color={scoreColor(row.axes[a.key], a.key === "risk")}
                      />
                    ))}
                  </div>

                  <div
                    className="rounded-xl p-3 text-center"
                    style={{ background: `${ZONE_TINT}08` }}
                  >
                    <p className="text-[11px] font-medium text-stone-400">Ağırlıklı skor</p>
                    <p
                      className="font-display text-2xl font-bold"
                      style={{ color: ZONE_TINT }}
                    >
                      {row.weighted_score.toFixed(2)}
                    </p>
                  </div>

                  {row.top_papers.length > 0 && (
                    <div className="space-y-2">
                      <p className="text-xs font-medium text-stone-500">
                        Öne çıkan makaleler
                      </p>
                      {row.top_papers.slice(0, 3).map((p) => (
                        <div
                          key={p.paper_id}
                          className="rounded-lg border border-stone-100 bg-stone-50/50 p-2.5"
                        >
                          <div className="flex items-start gap-2">
                            <BookOpen className="mt-0.5 h-3 w-3 flex-shrink-0 text-stone-400" />
                            <div className="min-w-0">
                              <p className="truncate font-display text-[11px] font-medium leading-snug text-stone-700">
                                {p.title ?? p.paper_id}
                              </p>
                              <p className="mt-0.5 text-[10px] text-stone-400">
                                {p.year ?? "?"}
                                {p.venue ? ` · ${p.venue}` : ""}
                              </p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </DataVizCard>
            ))}
          </div>

          {result.recommendation_text && (
            <div className="rounded-2xl border border-amber-200 bg-amber-50/40 p-4 shadow-sm">
              <div className="flex items-start gap-2">
                <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" />
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-amber-700">
                    Danışman önerisi
                  </p>
                  <p className="mt-1 whitespace-pre-wrap text-sm leading-relaxed text-stone-800">
                    {result.recommendation_text}
                  </p>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
