"use client";

/**
 * F13-S11.2 — 4.3 Özgünlük Değerlendirmesi (gapatlas-3).
 * kaynak: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S11
 * sayfa:  Page_Design/Sayfa_Plani_v2/4.3_ozgunluk_degerlendirmesi.rtf
 *
 * Eski DisruptionBeautyPage statik mock idi; mock = ürün politikası gereği
 * gerçek API'ye bağlanır: GET /api/workshop/originality.
 *
 * UX:
 * - 2 tab: ★ Yıkıcı (disruption / cd_5) · ◆ Sleeping Beauty (b)
 * - Yıl aralığı + theme_id filtresi (opsiyonel)
 * - Sonuç: top 50 paper liste + skor görselleştirme
 */

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  Zap,
  Clock,
  Loader2,
  AlertTriangle,
  ArrowUpRight,
} from "lucide-react";
import { AdvisorBanner } from "@/components/project/AdvisorBanner";
import { DataVizCard } from "@/components/project/DataVizCard";
import { apiFetch, ApiError } from "@/lib/api";

const ZONE_TINT = "#0E4F4A";

type OriginalityType = "disruption" | "sleeping_beauty";

interface OriginalityPaper {
  paper_id: string;
  title: string | null;
  year: number | null;
  venue: string | null;
  cd_5: number | null;
  n_a: number | null;
  n_i: number | null;
  n_j: number | null;
  total_window_papers: number | null;
  b: number | null;
  t_m: number | null;
  c_max: number | null;
  total_cites: number | null;
}

interface OriginalityResponse {
  type: OriginalityType;
  papers: OriginalityPaper[];
  threshold_used: number;
  threshold_source: string;
  pool_size: number;
}

function cd5BarColor(score: number): string {
  if (score >= 0.75) return ZONE_TINT;
  if (score >= 0.55) return "#d97706";
  return "#a8a29e";
}

export function OriginalityPage() {
  const params = useParams<{ id: string }>();
  const projectId = params?.id;

  const [activeTab, setActiveTab] = useState<OriginalityType>("disruption");
  const [yearFrom, setYearFrom] = useState("");
  const [yearTo, setYearTo] = useState("");
  const [themeId, setThemeId] = useState("");

  const [data, setData] = useState<Record<OriginalityType, OriginalityResponse | null>>({
    disruption: null,
    sleeping_beauty: null,
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadTab = useCallback(
    async (type: OriginalityType) => {
      if (!projectId) return;
      setBusy(true);
      setError(null);
      try {
        const qs = new URLSearchParams();
        qs.set("project_id", projectId);
        qs.set("type", type);
        if (yearFrom) qs.set("year_from", yearFrom);
        if (yearTo) qs.set("year_to", yearTo);
        if (themeId) qs.set("theme_id", themeId);
        const resp = await apiFetch<OriginalityResponse>(
          `/api/workshop/originality?${qs.toString()}`,
        );
        setData((prev) => ({ ...prev, [type]: resp }));
      } catch (e: unknown) {
        setError(
          e instanceof ApiError
            ? `Özgünlük verisi alınamadı (${e.status})`
            : "Özgünlük verisi alınamadı",
        );
      } finally {
        setBusy(false);
      }
    },
    [projectId, yearFrom, yearTo, themeId],
  );

  // mount → aktif tab fetch
  useEffect(() => {
    if (projectId && data[activeTab] === null && !busy && !error) {
      void loadTab(activeTab);
    }
  }, [projectId, activeTab, data, busy, error, loadTab]);

  const current = data[activeTab];

  const applyFilters = () => {
    setData({ disruption: null, sleeping_beauty: null });
    setError(null);
  };

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <AdvisorBanner message="Proje çapanı iki açıdan tara — alanı sarsanlar ve yıllar sonra fark edilen uyuyan güzeller." />

      {error && (
        <div className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 border-b border-stone-200">
        <button
          type="button"
          onClick={() => setActiveTab("disruption")}
          aria-pressed={activeTab === "disruption"}
          className={`-mb-px inline-flex items-center gap-2 border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === "disruption"
              ? "border-amber-600 text-amber-700"
              : "border-transparent text-stone-500 hover:text-stone-700"
          }`}
        >
          <Zap className="h-4 w-4" />
          Yıkıcı (CD₅)
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("sleeping_beauty")}
          aria-pressed={activeTab === "sleeping_beauty"}
          className={`-mb-px inline-flex items-center gap-2 border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === "sleeping_beauty"
              ? "border-amber-600 text-amber-700"
              : "border-transparent text-stone-500 hover:text-stone-700"
          }`}
        >
          <Clock className="h-4 w-4" />
          Uyuyan Güzel (B)
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-end gap-3 rounded-xl border border-stone-200 bg-white p-4">
        <label className="flex flex-col text-xs">
          <span className="text-stone-500">Yıl başlangıç</span>
          <input
            type="number"
            min={1900}
            max={2100}
            value={yearFrom}
            onChange={(e) => setYearFrom(e.target.value)}
            placeholder="2010"
            aria-label="Yıl başlangıç"
            className="mt-1 w-28 rounded-lg border border-stone-200 px-2 py-1.5 text-sm focus:border-stone-400 focus:outline-none"
          />
        </label>
        <label className="flex flex-col text-xs">
          <span className="text-stone-500">Yıl bitiş</span>
          <input
            type="number"
            min={1900}
            max={2100}
            value={yearTo}
            onChange={(e) => setYearTo(e.target.value)}
            placeholder="2025"
            aria-label="Yıl bitiş"
            className="mt-1 w-28 rounded-lg border border-stone-200 px-2 py-1.5 text-sm focus:border-stone-400 focus:outline-none"
          />
        </label>
        <label className="flex flex-1 flex-col text-xs">
          <span className="text-stone-500">Tema ID (opsiyonel)</span>
          <input
            type="text"
            value={themeId}
            onChange={(e) => setThemeId(e.target.value)}
            placeholder="örn: T1234"
            aria-label="Tema filtresi"
            className="mt-1 rounded-lg border border-stone-200 px-2 py-1.5 text-sm focus:border-stone-400 focus:outline-none"
          />
        </label>
        <button
          type="button"
          onClick={applyFilters}
          className="rounded-lg border border-stone-200 bg-white px-4 py-2 text-sm font-medium text-stone-700 transition-colors hover:bg-stone-50"
        >
          Filtreyi uygula
        </button>
      </div>

      {/* Status row */}
      {current && (
        <div className="flex items-center gap-3 text-xs text-stone-500">
          <span>
            Havuz: <strong className="text-stone-700">{current.pool_size}</strong> makale
          </span>
          <span>·</span>
          <span>
            Eşik (
            {activeTab === "disruption" ? "CD₅" : "B"}): &gt; {current.threshold_used.toFixed(2)}
          </span>
          <span className="text-stone-400">({current.threshold_source})</span>
        </div>
      )}

      {busy && (
        <p className="flex items-center gap-2 text-sm text-stone-500">
          <Loader2 className="h-4 w-4 animate-spin" />
          Yükleniyor…
        </p>
      )}

      {current && !busy && (
        <DataVizCard
          title={activeTab === "disruption" ? "Alanı sarsan çalışmalar" : "Gecikmiş keşifler"}
          subtitle={
            activeTab === "disruption" ? "CD₅ Disruption Index" : "Sleeping Beauty Index (B)"
          }
          badge={`Top ${current.papers.length}`}
          zoneTint={ZONE_TINT}
        >
          {current.papers.length === 0 ? (
            <p className="rounded-lg border border-dashed border-stone-200 bg-stone-50 p-6 text-center text-sm text-stone-500">
              Eşiğin üzerinde makale yok. Filtreyi gevşet veya farklı tema dene.
            </p>
          ) : (
            <ul className="space-y-1">
              {current.papers.map((p, idx) => (
                <li
                  key={p.paper_id}
                  data-testid="originality-row"
                  className="flex gap-3 rounded-xl p-3 transition-colors hover:bg-stone-50"
                >
                  <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg bg-stone-100 text-xs font-bold text-stone-500">
                    #{idx + 1}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="font-display line-clamp-2 text-[13px] font-medium italic leading-snug text-stone-800">
                      {p.title ?? p.paper_id}
                    </p>
                    {activeTab === "disruption" ? (
                      <DisruptionRow paper={p} />
                    ) : (
                      <BeautyRow paper={p} />
                    )}
                    <p className="mt-1 text-[11px] text-stone-400">
                      {p.venue ?? "—"} · {p.year ?? "?"}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </DataVizCard>
      )}
    </div>
  );
}

function DisruptionRow({ paper }: { paper: OriginalityPaper }) {
  const cd = paper.cd_5 ?? 0;
  return (
    <div className="mt-1.5 flex items-center gap-3">
      <span className="text-[11px] text-stone-400">CD₅</span>
      <div className="flex items-center gap-1.5">
        <div className="h-1.5 w-24 overflow-hidden rounded-full bg-stone-100">
          <div
            className="h-full rounded-full"
            style={{
              width: `${Math.max(0, Math.min(1, (cd + 1) / 2)) * 100}%`,
              background: cd5BarColor(cd),
            }}
          />
        </div>
        <span className="text-[11px] font-medium" style={{ color: cd5BarColor(cd) }}>
          {cd.toFixed(2)}
        </span>
      </div>
      {paper.n_a !== null && paper.n_i !== null && paper.n_j !== null && (
        <span className="font-mono text-[10px] text-stone-400">
          Nₐ={paper.n_a} · Nᵢ={paper.n_i} · Nⱼ={paper.n_j}
        </span>
      )}
    </div>
  );
}

function BeautyRow({ paper }: { paper: OriginalityPaper }) {
  return (
    <div className="mt-1.5 flex items-center gap-3">
      <span className="text-[11px] text-stone-400">B</span>
      <span
        className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium"
        style={{
          background: `${ZONE_TINT}12`,
          color: ZONE_TINT,
          border: `1px solid ${ZONE_TINT}25`,
        }}
      >
        {paper.b !== null ? paper.b.toFixed(2) : "—"}
      </span>
      {paper.t_m !== null && (
        <span className="inline-flex items-center gap-1 text-[11px] text-stone-400">
          <ArrowUpRight className="h-3 w-3" />
          t_m = {paper.t_m}
        </span>
      )}
      {paper.c_max !== null && (
        <span className="font-mono text-[10px] text-stone-400">
          c_max={paper.c_max}
        </span>
      )}
    </div>
  );
}
