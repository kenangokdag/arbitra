"use client";

/**
 * F13-S11.3 — 4.5 Akademik Etki Eğrisi (gapatlas-5).
 * kaynak: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S11
 * sayfa:  Page_Design/Sayfa_Plani_v2/4.5_akademik_etki_egrisi.rtf
 *
 * Eski SocialPulsePage statik 12 ay sahte trend + /api/search ile alakasız bir
 * "akademik nabız" gösteriyordu. Yeni: GET /api/workshop/impact-curve →
 *   - academic_series (yıllık yayın sayısı)
 *   - trends_series (V1'de boş; Pytrends kütüphanesi pyproject'te yok)
 *   - ★ noktalar: disruption (cd_5 > eşik) paper'lar
 *   - ♦ noktalar: sleeping_beauty paper'lar (publication_year → awakening_year)
 *   - momentum_color: yıllık slope'tan green/yellow/red/unknown
 *   - llm_comment: Gemini Flash 1-cümle yorum
 *
 * V1 fallback: trends_available=false → "trend verisi yok" rozeti.
 */

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  Loader2,
  TrendingUp,
  TrendingDown,
  Minus,
  AlertTriangle,
  Sparkles,
  Star,
  Diamond,
} from "lucide-react";
import { AdvisorBanner } from "@/components/project/AdvisorBanner";
import { DataVizCard } from "@/components/project/DataVizCard";
import { apiFetch, ApiError } from "@/lib/api";

const ZONE_TINT = "#0E4F4A";

type ImpactDimension = "topic" | "method";
type MomentumColor = "green" | "yellow" | "red" | "unknown";

interface ImpactPoint {
  year: number;
  value: number;
}

interface StarPoint {
  paper_id: string;
  title: string | null;
  year: number;
  cd_5: number;
}

interface BeautyPoint {
  paper_id: string;
  title: string | null;
  publication_year: number;
  awakening_year: number;
  b: number;
}

interface ImpactCurveResponse {
  dimension: ImpactDimension;
  value: string;
  academic_series: ImpactPoint[];
  trends_series: ImpactPoint[];
  trends_available: boolean;
  stars: StarPoint[];
  beauties: BeautyPoint[];
  academic_slope_pct: number | null;
  trends_slope: number | null;
  momentum_color: MomentumColor;
  llm_comment: string | null;
}

const MOMENTUM_CFG: Record<MomentumColor, { label: string; bg: string; fg: string; icon: typeof TrendingUp }> = {
  green: { label: "Yükselen", bg: "bg-emerald-50 border-emerald-200", fg: "text-emerald-700", icon: TrendingUp },
  yellow: { label: "Yatay", bg: "bg-amber-50 border-amber-200", fg: "text-amber-700", icon: Minus },
  red: { label: "Düşüş", bg: "bg-red-50 border-red-200", fg: "text-red-700", icon: TrendingDown },
  unknown: { label: "Belirsiz", bg: "bg-stone-50 border-stone-200", fg: "text-stone-500", icon: Minus },
};

export function ImpactCurvePage() {
  const params = useParams<{ id: string }>();
  const projectId = params?.id;

  const [dimension, setDimension] = useState<ImpactDimension>("topic");
  const [value, setValue] = useState("");
  const [years, setYears] = useState(10);

  const [result, setResult] = useState<ImpactCurveResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runFetch = useCallback(async () => {
    if (!projectId || !value.trim()) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const qs = new URLSearchParams({
        project_id: projectId,
        dimension,
        value: value.trim(),
        years: String(years),
      });
      const data = await apiFetch<ImpactCurveResponse>(
        `/api/workshop/impact-curve?${qs.toString()}`,
      );
      setResult(data);
    } catch (e: unknown) {
      setError(
        e instanceof ApiError
          ? `Etki eğrisi alınamadı (${e.status})`
          : "Etki eğrisi alınamadı",
      );
    } finally {
      setBusy(false);
    }
  }, [projectId, dimension, value, years]);

  useEffect(() => {
    // Auto-run gerek yok — kullanıcı value girene kadar bekle
  }, []);

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <AdvisorBanner message="Bir konunun veya yöntemin akademik nabzı yıllar içinde nasıl değişmiş — birlikte bakalım." />

      {error && (
        <div className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-end gap-3 rounded-xl border border-stone-200 bg-white p-4">
        <label className="flex flex-col text-xs">
          <span className="text-stone-500">Boyut</span>
          <select
            value={dimension}
            onChange={(e) => setDimension(e.target.value as ImpactDimension)}
            aria-label="Boyut"
            className="mt-1 rounded-lg border border-stone-200 px-2 py-1.5 text-sm focus:border-stone-400 focus:outline-none"
          >
            <option value="topic">Konu (theme_id)</option>
            <option value="method">Yöntem (metod_id)</option>
          </select>
        </label>
        <label className="flex flex-1 flex-col text-xs">
          <span className="text-stone-500">Değer</span>
          <input
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder={dimension === "topic" ? "örn: T1234" : "örn: M5678"}
            aria-label="Değer"
            className="mt-1 rounded-lg border border-stone-200 px-2 py-1.5 text-sm focus:border-stone-400 focus:outline-none"
          />
        </label>
        <label className="flex flex-col text-xs">
          <span className="text-stone-500">Yıl penceresi</span>
          <input
            type="number"
            min={2}
            max={30}
            value={years}
            onChange={(e) => setYears(Number(e.target.value))}
            aria-label="Yıl penceresi"
            className="mt-1 w-24 rounded-lg border border-stone-200 px-2 py-1.5 text-sm focus:border-stone-400 focus:outline-none"
          />
        </label>
        <button
          type="button"
          onClick={runFetch}
          disabled={busy || !value.trim()}
          className="inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold text-white shadow-sm transition-all hover:shadow-md disabled:opacity-40"
          style={{ background: ZONE_TINT }}
        >
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
          Eğriyi getir
        </button>
      </div>

      {!result && !busy && (
        <p className="rounded-xl border border-dashed border-stone-200 bg-stone-50 p-6 text-center text-sm text-stone-500">
          Boyut + değer gir ve "Eğriyi getir"e bas.
        </p>
      )}

      {busy && (
        <p className="flex items-center gap-2 text-sm text-stone-500">
          <Loader2 className="h-4 w-4 animate-spin" />
          Eğri hazırlanıyor…
        </p>
      )}

      {result && (
        <>
          {/* Momentum + slope row */}
          <div className="flex flex-wrap items-center gap-3">
            <MomentumBadge color={result.momentum_color} />
            {result.academic_slope_pct !== null && (
              <span className="text-xs text-stone-500">
                Akademik eğim:{" "}
                <strong className="text-stone-700">
                  {result.academic_slope_pct.toFixed(1)}%/yıl
                </strong>
              </span>
            )}
            {!result.trends_available && (
              <span className="rounded-full bg-stone-100 px-2 py-0.5 text-[10px] text-stone-500">
                trend verisi yok (V1)
              </span>
            )}
          </div>

          {/* Chart */}
          <DataVizCard
            title="Yıllık yayın eğrisi"
            subtitle={`${result.dimension === "topic" ? "Konu" : "Yöntem"}: ${result.value}`}
            badge={`${result.academic_series.length} yıl`}
            zoneTint={ZONE_TINT}
          >
            <ImpactChart
              academic={result.academic_series}
              trends={result.trends_available ? result.trends_series : []}
              stars={result.stars}
              beauties={result.beauties}
            />
          </DataVizCard>

          {/* LLM comment */}
          {result.llm_comment && (
            <div className="rounded-xl border border-amber-200 bg-amber-50/40 p-3 text-sm text-stone-700">
              <div className="flex items-start gap-2">
                <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" />
                <p className="leading-relaxed">{result.llm_comment}</p>
              </div>
            </div>
          )}

          {/* Stars + Beauties lists */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="rounded-xl border border-stone-200 bg-white p-4">
              <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-stone-700">
                <Star className="h-4 w-4 text-amber-500" />
                Yıkıcı çalışmalar ({result.stars.length})
              </h3>
              {result.stars.length === 0 ? (
                <p className="text-xs text-stone-400">Bu pencerede yıkıcı çalışma yok.</p>
              ) : (
                <ul className="space-y-1.5">
                  {result.stars.map((s) => (
                    <li
                      key={s.paper_id}
                      data-testid="star-row"
                      className="rounded-lg border border-stone-100 p-2 text-xs"
                    >
                      <p className="line-clamp-2 font-medium text-stone-700">
                        {s.title ?? s.paper_id}
                      </p>
                      <p className="mt-0.5 text-[10px] text-stone-400">
                        {s.year} · CD₅ = {s.cd_5.toFixed(2)}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="rounded-xl border border-stone-200 bg-white p-4">
              <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-stone-700">
                <Diamond className="h-4 w-4 text-teal-600" />
                Uyuyan güzeller ({result.beauties.length})
              </h3>
              {result.beauties.length === 0 ? (
                <p className="text-xs text-stone-400">Bu pencerede uyanan paper yok.</p>
              ) : (
                <ul className="space-y-1.5">
                  {result.beauties.map((b) => (
                    <li
                      key={b.paper_id}
                      data-testid="beauty-row"
                      className="rounded-lg border border-stone-100 p-2 text-xs"
                    >
                      <p className="line-clamp-2 font-medium text-stone-700">
                        {b.title ?? b.paper_id}
                      </p>
                      <p className="mt-0.5 text-[10px] text-stone-400">
                        {b.publication_year} → {b.awakening_year} · B = {b.b.toFixed(2)}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function MomentumBadge({ color }: { color: MomentumColor }) {
  const cfg = MOMENTUM_CFG[color];
  const Icon = cfg.icon;
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium ${cfg.bg} ${cfg.fg}`}
      data-testid="momentum-badge"
    >
      <Icon className="h-3.5 w-3.5" />
      Momentum: {cfg.label}
    </span>
  );
}

interface ChartProps {
  academic: ImpactPoint[];
  trends: ImpactPoint[];
  stars: StarPoint[];
  beauties: BeautyPoint[];
}

function ImpactChart({ academic, trends, stars, beauties }: ChartProps) {
  if (academic.length === 0) {
    return <p className="p-4 text-center text-xs text-stone-400">Yıllık seri yok.</p>;
  }
  const years = academic.map((p) => p.year);
  const minYear = Math.min(...years);
  const maxYear = Math.max(...years);
  const allValues = [...academic.map((p) => p.value), ...trends.map((p) => p.value)];
  const maxValue = Math.max(...allValues, 1);

  const W = 720;
  const H = 200;
  const PAD_X = 40;
  const PAD_Y = 24;

  const xOf = (yr: number) =>
    PAD_X + ((yr - minYear) / Math.max(1, maxYear - minYear)) * (W - 2 * PAD_X);
  const yOf = (v: number) => H - PAD_Y - (v / maxValue) * (H - 2 * PAD_Y);

  const academicPath = academic
    .map((p, i) => `${i === 0 ? "M" : "L"} ${xOf(p.year)} ${yOf(p.value)}`)
    .join(" ");
  const trendsPath = trends
    .map((p, i) => `${i === 0 ? "M" : "L"} ${xOf(p.year)} ${yOf(p.value)}`)
    .join(" ");

  return (
    <div className="overflow-x-auto">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        width="100%"
        height={H}
        role="img"
        aria-label="Akademik etki eğrisi"
      >
        {/* gridlines */}
        {[0, 0.25, 0.5, 0.75, 1].map((g) => (
          <line
            key={g}
            x1={PAD_X}
            x2={W - PAD_X}
            y1={H - PAD_Y - g * (H - 2 * PAD_Y)}
            y2={H - PAD_Y - g * (H - 2 * PAD_Y)}
            stroke="#f5f5f4"
          />
        ))}

        {/* academic line */}
        {academicPath && (
          <path d={academicPath} fill="none" stroke={ZONE_TINT} strokeWidth={2} />
        )}

        {/* trends line (dashed) */}
        {trendsPath && (
          <path
            d={trendsPath}
            fill="none"
            stroke="#d97706"
            strokeWidth={2}
            strokeDasharray="4 3"
          />
        )}

        {/* x-axis years */}
        {academic.map((p, i) => (
          <text
            key={`yr-${i}`}
            x={xOf(p.year)}
            y={H - 6}
            textAnchor="middle"
            fontSize={10}
            fill="#a8a29e"
          >
            {p.year}
          </text>
        ))}

        {/* y-axis labels */}
        {[0, 0.5, 1].map((g) => (
          <text
            key={`val-${g}`}
            x={6}
            y={H - PAD_Y - g * (H - 2 * PAD_Y) + 3}
            fontSize={10}
            fill="#a8a29e"
          >
            {Math.round(maxValue * g)}
          </text>
        ))}

        {/* ★ stars */}
        {stars.map((s) => (
          <g key={`star-${s.paper_id}`}>
            <circle
              cx={xOf(s.year)}
              cy={yOf((academic.find((p) => p.year === s.year)?.value ?? maxValue) || 0)}
              r={6}
              fill="#f59e0b"
              fillOpacity={0.9}
            />
            <text
              x={xOf(s.year)}
              y={yOf((academic.find((p) => p.year === s.year)?.value ?? maxValue) || 0) + 3}
              textAnchor="middle"
              fontSize={9}
              fill="white"
            >
              ★
            </text>
          </g>
        ))}

        {/* ♦ beauties (awakening_year noktası) */}
        {beauties.map((b) => (
          <g key={`beauty-${b.paper_id}`}>
            <rect
              x={xOf(b.awakening_year) - 5}
              y={yOf((academic.find((p) => p.year === b.awakening_year)?.value ?? maxValue) || 0) - 5}
              width={10}
              height={10}
              transform={`rotate(45 ${xOf(b.awakening_year)} ${yOf((academic.find((p) => p.year === b.awakening_year)?.value ?? maxValue) || 0)})`}
              fill="#0d9488"
              fillOpacity={0.85}
            />
          </g>
        ))}
      </svg>

      <div className="mt-2 flex flex-wrap items-center gap-4 text-[11px] text-stone-500">
        <span className="inline-flex items-center gap-1.5">
          <span className="block h-0.5 w-4" style={{ background: ZONE_TINT }} />
          Akademik yayın
        </span>
        {trends.length > 0 && (
          <span className="inline-flex items-center gap-1.5">
            <span className="block h-0.5 w-4 border-t border-dashed border-amber-600" />
            Arama trendi
          </span>
        )}
        <span className="inline-flex items-center gap-1.5">
          <Star className="h-3 w-3 text-amber-500" />
          Yıkıcı
        </span>
        <span className="inline-flex items-center gap-1.5">
          <Diamond className="h-3 w-3 text-teal-600" />
          Uyuyan Güzel
        </span>
      </div>
    </div>
  );
}
