"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  ScrollText,
  FileText,
  Layers,
  Check,
  AlertTriangle,
  Loader2,
  Sparkles,
} from "lucide-react";
import { AdvisorBanner } from "@/components/project/AdvisorBanner";
import { apiFetch, ApiError } from "@/lib/api";

// F13-S3.3 — authoring-1 (5.1 Yayın Formatı).
// 2 endpoint binding:
//   GET  /api/workshop/maturity?project_id=&publication_type=
//   POST /api/workshop/advisor-summary

type PubType = "tez" | "makale" | "bildiri";
type ProgressStatus = "not_started" | "in_progress" | "completed";

interface MaturityStep {
  step_id: string;
  status: ProgressStatus;
  required: boolean;
  completed_at: string | null;
}

interface MaturityResponse {
  project_id: string;
  publication_type: PubType;
  steps: MaturityStep[];
  maturity_pct: number;
  button_active: boolean;
  required_total: number;
  required_completed: number;
}

interface AdvisorSummaryResponse {
  summary: string;
  publication_type: PubType;
  step_count_used: number;
  cache_hit: boolean;
}

const cards: {
  id: PubType;
  title: string;
  icon: typeof ScrollText;
  desc: string;
  sub: string;
}[] = [
  {
    id: "tez",
    title: "Tez",
    icon: ScrollText,
    desc: "Yuksek lisans veya doktora tezi",
    sub: "IMRaD + ek bolumler",
  },
  {
    id: "makale",
    title: "Makale",
    icon: FileText,
    desc: "Hakemli dergi makalesi",
    sub: "IMRaD standart",
  },
  {
    id: "bildiri",
    title: "Bildiri",
    icon: Layers,
    desc: "Konferans bildirisi",
    sub: "Kisa format + poster",
  },
];

const STATUS_LABELS: Record<ProgressStatus, string> = {
  not_started: "Başlanmadı",
  in_progress: "Devam ediyor",
  completed: "Tamamlandı",
};

const STATUS_COLOR: Record<ProgressStatus, string> = {
  not_started: "bg-stone-100 text-stone-600",
  in_progress: "bg-amber-100 text-amber-800",
  completed: "bg-emerald-100 text-emerald-800",
};

export function PublicationTypePage() {
  const params = useParams<{ id: string }>();
  const projectId = params?.id;

  const [selectedType, setSelectedType] = useState<PubType | null>(null);
  const [maturity, setMaturity] = useState<MaturityResponse | null>(null);
  const [summary, setSummary] = useState<AdvisorSummaryResponse | null>(null);
  const [summaryBusy, setSummaryBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const maturityBusy = selectedType !== null && maturity === null && error === null;

  function handleSelect(t: PubType) {
    setSelectedType(t);
    setMaturity(null);
    setSummary(null);
    setError(null);
  }

  useEffect(() => {
    if (!projectId || !selectedType) return;
    const ctrl = new AbortController();
    apiFetch<MaturityResponse>(
      `/api/workshop/maturity?project_id=${encodeURIComponent(projectId)}&publication_type=${selectedType}`,
      { method: "GET", signal: ctrl.signal },
    )
      .then((data) => {
        setMaturity(data);
      })
      .catch((e: unknown) => {
        if ((e as { name?: string })?.name === "AbortError") return;
        const msg =
          e instanceof ApiError
            ? `Olgunluk yuklenemedi (${e.status})`
            : "Olgunluk yuklenemedi";
        setError(msg);
      });
    return () => ctrl.abort();
  }, [projectId, selectedType]);

  const runAdvisorSummary = useCallback(async () => {
    if (!projectId || !selectedType) return;
    setSummaryBusy(true);
    setError(null);
    try {
      const data = await apiFetch<AdvisorSummaryResponse>(
        "/api/workshop/advisor-summary",
        {
          method: "POST",
          body: { project_id: projectId, publication_type: selectedType },
        },
      );
      setSummary(data);
    } catch (e: unknown) {
      const msg =
        e instanceof ApiError ? `Ozet uretilemedi (${e.status})` : "Ozet uretilemedi";
      setError(msg);
    } finally {
      setSummaryBusy(false);
    }
  }, [projectId, selectedType]);

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <AdvisorBanner message="Yazim turunu secelim once: tez, makale, bildiri. Iskelet bundan sonra sekillenir." />

      {error && (
        <div className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        {cards.map((card) => {
          const isSelected = selectedType === card.id;
          const Icon = card.icon;
          return (
            <div
              key={card.id}
              className={`relative flex h-[200px] flex-col items-center justify-center rounded-2xl border-2 p-6 text-center transition-all ${
                isSelected
                  ? "border-[#E8A157] bg-amber-50/40 shadow-sm"
                  : "border-stone-200 bg-white hover:border-stone-300"
              }`}
            >
              {isSelected && (
                <span className="absolute right-3 top-3 flex items-center gap-1 rounded-full bg-[#E8A157] px-2.5 py-0.5 text-xs font-medium text-white">
                  <Check className="h-3 w-3" />
                  Secildi
                </span>
              )}
              <Icon className="mb-3 h-12 w-12 text-stone-500" />
              <h3 className="font-display text-lg font-semibold text-stone-800">
                {card.title}
              </h3>
              <p className="mt-1 text-sm text-stone-600">{card.desc}</p>
              <p className="mt-0.5 text-xs text-stone-400">{card.sub}</p>
              <button
                onClick={() => handleSelect(card.id)}
                className={`mt-4 rounded-lg px-6 py-2 text-sm font-medium transition-all ${
                  isSelected
                    ? "bg-stone-200 text-stone-500"
                    : "bg-gradient-to-r from-[#E8A157] to-amber-500 text-white shadow-sm hover:shadow"
                }`}
              >
                {isSelected ? "Secildi" : "Sec"}
              </button>
            </div>
          );
        })}
      </div>

      {selectedType && (
        <div className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <h3 className="font-display text-base font-semibold text-stone-800">
              Olgunluk · {selectedType}
            </h3>
            {maturity && (
              <span className="text-sm font-medium text-stone-700">
                %{Math.round(maturity.maturity_pct)} · {maturity.required_completed}/
                {maturity.required_total} zorunlu
              </span>
            )}
          </div>

          {maturityBusy && (
            <div className="mt-3 flex items-center gap-2 text-sm text-stone-500">
              <Loader2 className="h-4 w-4 animate-spin" /> Olgunluk hesaplanıyor…
            </div>
          )}

          {maturity && (
            <>
              <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-stone-100">
                <div
                  className="h-full rounded-full bg-emerald-500 transition-all"
                  style={{ width: `${maturity.maturity_pct}%` }}
                />
              </div>

              <ul className="mt-4 space-y-2">
                {maturity.steps.map((s) => (
                  <li
                    key={s.step_id}
                    className="flex items-center justify-between rounded-lg border border-stone-100 px-3 py-2 text-sm"
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs text-stone-500">
                        {s.step_id}
                      </span>
                      {s.required && (
                        <span className="rounded-full bg-stone-100 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-stone-600">
                          zorunlu
                        </span>
                      )}
                    </div>
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLOR[s.status]}`}
                    >
                      {STATUS_LABELS[s.status]}
                    </span>
                  </li>
                ))}
              </ul>

              <div className="mt-4 flex flex-col gap-2">
                <button
                  type="button"
                  onClick={runAdvisorSummary}
                  disabled={!maturity.button_active || summaryBusy}
                  className="inline-flex items-center justify-center gap-2 rounded-lg bg-stone-800 px-4 py-2 text-sm font-medium text-white hover:bg-stone-900 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {summaryBusy ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Sparkles className="h-4 w-4" />
                  )}
                  Danışmana Gitmeden Evvel
                </button>
                {!maturity.button_active && (
                  <p className="text-xs text-stone-500">
                    Tüm zorunlu adımlar tamamlanınca özet butonu açılır.
                  </p>
                )}
              </div>
            </>
          )}
        </div>
      )}

      {summary && (
        <div className="rounded-2xl border border-stone-200 bg-stone-50 p-5">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="font-display text-base font-semibold text-stone-800">
              Danışman Özeti
            </h3>
            <span className="text-xs text-stone-500">
              {summary.step_count_used} adım · {summary.cache_hit ? "cache" : "yeni"}
            </span>
          </div>
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-stone-800">
            {summary.summary}
          </p>
        </div>
      )}
    </div>
  );
}
