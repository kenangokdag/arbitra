"use client";

/**
 * F13-S11.1 — 3.4 Literatür Sentezi (curation-4).
 * kaynak: docs/plans/F13_sayfa_plani_v2_implementation.md §3 F13-S11
 * sayfa:  Page_Design/Sayfa_Plani_v2/3.4_literatur_sentezi.rtf
 *
 * V1 (paper-bazlı /api/summarize?paper_id=...) yerine proje-bazlı sentez:
 * - GET  /api/project/{id}/papers   → seed papers + metadata (lazy hydrated)
 * - POST /api/workshop/synthesize   → 1..25 paper_ids + mode + lang
 *
 * UX:
 * - Sol panel: paper list + checkbox (1..25 seçim)
 * - Mode toggle: neutral / critical / short
 * - Lang toggle: tr / en / id (boş = proje varsayılanı)
 * - "Sentezle" CTA → mutation
 * - Sonuç: synthesis_text + cümle-bazlı faithfulness badge (green/yellow/red)
 * - Sağ: references listesi (numaralı APA-style)
 */

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  BookOpen,
  CheckCircle2,
  AlertCircle,
  XCircle,
  Loader2,
  AlertTriangle,
  Sparkles,
} from "lucide-react";
import { AdvisorBanner } from "@/components/project/AdvisorBanner";
import { apiFetch, ApiError } from "@/lib/api";

type SynthMode = "neutral" | "critical" | "short";
type SynthLang = "tr" | "en" | "id";
type SynthFlag = "green" | "yellow" | "red";

interface ProjectPaper {
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
  papers: ProjectPaper[];
  hydrated_count: number;
}

interface SynthSentence {
  text: string;
  citations: string[];
  faithfulness_score: number;
  flag: SynthFlag;
}

interface SynthReference {
  index: number;
  paper_id: string;
  citation: string;
}

interface SynthesizeResponse {
  synthesis_text: string;
  sentences: SynthSentence[];
  references: SynthReference[];
  total_faithfulness: number;
  theme_warning: string | null;
  mode: SynthMode;
  lang: SynthLang;
}

const MODES: { key: SynthMode; label: string; hint: string }[] = [
  { key: "neutral", label: "Nötr", hint: "Dengeli özet" },
  { key: "critical", label: "Eleştirel", hint: "Çelişki + boşluk" },
  { key: "short", label: "Kısa", hint: "2-3 paragraf" },
];

const LANGS: { key: SynthLang; label: string }[] = [
  { key: "tr", label: "TR" },
  { key: "en", label: "EN" },
  { key: "id", label: "ID" },
];

const FLAG_CFG: Record<SynthFlag, { color: string; icon: typeof CheckCircle2; label: string }> = {
  green: { color: "bg-emerald-100 text-emerald-700 border-emerald-200", icon: CheckCircle2, label: "Sadık" },
  yellow: { color: "bg-amber-100 text-amber-700 border-amber-200", icon: AlertCircle, label: "Kısmen" },
  red: { color: "bg-red-100 text-red-700 border-red-200", icon: XCircle, label: "Şüpheli" },
};

export function LiteratureSummaryPage() {
  const params = useParams<{ id: string }>();
  const projectId = params?.id;

  const [papers, setPapers] = useState<ProjectPaper[] | null>(null);
  const [papersBusy, setPapersBusy] = useState(false);
  const [papersError, setPapersError] = useState<string | null>(null);

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [mode, setMode] = useState<SynthMode>("neutral");
  const [lang, setLang] = useState<SynthLang | "">("");

  const [result, setResult] = useState<SynthesizeResponse | null>(null);
  const [synthBusy, setSynthBusy] = useState(false);
  const [synthError, setSynthError] = useState<string | null>(null);

  const loadPapers = useCallback(async () => {
    if (!projectId) return;
    setPapersBusy(true);
    setPapersError(null);
    try {
      const data = await apiFetch<ProjectPapersResponse>(
        `/api/project/${encodeURIComponent(projectId)}/papers`,
      );
      setPapers(data.papers);
    } catch (e: unknown) {
      setPapersError(
        e instanceof ApiError
          ? `Makaleler alınamadı (${e.status})`
          : "Makaleler alınamadı",
      );
    } finally {
      setPapersBusy(false);
    }
  }, [projectId]);

  useEffect(() => {
    if (projectId && papers === null && !papersBusy && !papersError) {
      void loadPapers();
    }
  }, [projectId, papers, papersBusy, papersError, loadPapers]);

  function toggleSelect(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else if (next.size < 25) {
        next.add(id);
      }
      return next;
    });
  }

  function selectAll() {
    if (!papers) return;
    const first25 = papers.slice(0, 25).map((p) => p.paper_id);
    setSelectedIds(new Set(first25));
  }

  function clearSelection() {
    setSelectedIds(new Set());
  }

  const canSubmit =
    !!projectId && selectedIds.size >= 1 && selectedIds.size <= 25 && !synthBusy;

  const runSynthesize = useCallback(async () => {
    if (!projectId || !canSubmit) return;
    setSynthBusy(true);
    setSynthError(null);
    setResult(null);
    try {
      const body: Record<string, unknown> = {
        project_id: projectId,
        paper_ids: Array.from(selectedIds),
        mode,
      };
      if (lang) body.lang = lang;
      const data = await apiFetch<SynthesizeResponse>("/api/workshop/synthesize", {
        method: "POST",
        body,
      });
      setResult(data);
    } catch (e: unknown) {
      setSynthError(
        e instanceof ApiError
          ? `Sentez hatası (${e.status})`
          : "Sentez hatası",
      );
    } finally {
      setSynthBusy(false);
    }
  }, [projectId, canSubmit, selectedIds, mode, lang]);

  const paragraphs = (result?.synthesis_text ?? "").split(/\n{2,}/).filter(Boolean);

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <AdvisorBanner message="Proje çapanı tek sayfaya damıt — 1..25 makale, mod seç, sentez al." />

      {synthError && (
        <div className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{synthError}</span>
        </div>
      )}

      <div className="flex flex-col gap-6 md:flex-row">
        {/* Left — paper picker + controls */}
        <div className="md:w-[360px] md:flex-shrink-0">
          <div className="space-y-3 rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <h3 className="font-display text-sm font-semibold text-stone-800">
                Sentezlenecek makaleler
              </h3>
              <span className="text-xs text-stone-500">{selectedIds.size}/25</span>
            </div>

            {papersBusy && (
              <p className="flex items-center gap-2 text-xs text-stone-400">
                <Loader2 className="h-3 w-3 animate-spin" />
                Çapa yükleniyor…
              </p>
            )}
            {papersError && (
              <p className="text-xs text-red-600" role="alert">
                {papersError}
              </p>
            )}

            {papers && papers.length === 0 && (
              <p className="rounded-lg border border-dashed border-stone-200 bg-stone-50 p-3 text-xs text-stone-500">
                Bu projenin çapasında makale yok. Q sayfasından makale seçerek başla.
              </p>
            )}

            {papers && papers.length > 0 && (
              <>
                <div className="flex gap-2 text-xs">
                  <button
                    type="button"
                    onClick={selectAll}
                    className="text-stone-500 hover:text-stone-700"
                  >
                    Tümünü seç (ilk 25)
                  </button>
                  <span className="text-stone-300">·</span>
                  <button
                    type="button"
                    onClick={clearSelection}
                    className="text-stone-500 hover:text-stone-700"
                  >
                    Temizle
                  </button>
                </div>

                <ul
                  className="max-h-[420px] space-y-1.5 overflow-y-auto"
                  aria-label="Proje makaleleri"
                >
                  {papers.map((p) => {
                    const checked = selectedIds.has(p.paper_id);
                    return (
                      <li key={p.paper_id}>
                        <label
                          className={`flex cursor-pointer items-start gap-2 rounded-lg border p-2 transition-colors ${
                            checked
                              ? "border-amber-300 bg-amber-50"
                              : "border-stone-100 hover:bg-stone-50"
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={() => toggleSelect(p.paper_id)}
                            aria-label={`${p.title} seç`}
                            className="mt-1"
                          />
                          <div className="min-w-0 flex-1">
                            <p className="line-clamp-2 text-xs font-medium leading-snug text-stone-700">
                              {p.title}
                            </p>
                            <p className="mt-0.5 text-[10px] text-stone-400">
                              {p.year ?? "?"} · {p.venue ?? "—"}
                            </p>
                          </div>
                        </label>
                      </li>
                    );
                  })}
                </ul>
              </>
            )}

            {/* Mode */}
            <div className="border-t border-stone-100 pt-3">
              <p className="mb-1.5 text-xs font-medium text-stone-500">Mod</p>
              <div className="flex gap-1.5">
                {MODES.map((m) => (
                  <button
                    key={m.key}
                    type="button"
                    onClick={() => setMode(m.key)}
                    aria-pressed={mode === m.key}
                    className={`flex-1 rounded-lg px-2 py-1.5 text-xs font-medium transition-colors ${
                      mode === m.key
                        ? "bg-stone-800 text-white"
                        : "bg-stone-100 text-stone-600 hover:bg-stone-200"
                    }`}
                  >
                    {m.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Lang */}
            <div>
              <p className="mb-1.5 text-xs font-medium text-stone-500">Dil</p>
              <div className="flex gap-1.5">
                <button
                  type="button"
                  onClick={() => setLang("")}
                  aria-pressed={lang === ""}
                  className={`flex-1 rounded-lg px-2 py-1.5 text-xs font-medium transition-colors ${
                    lang === ""
                      ? "bg-stone-800 text-white"
                      : "bg-stone-100 text-stone-600 hover:bg-stone-200"
                  }`}
                >
                  Otomatik
                </button>
                {LANGS.map((l) => (
                  <button
                    key={l.key}
                    type="button"
                    onClick={() => setLang(l.key)}
                    aria-pressed={lang === l.key}
                    className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                      lang === l.key
                        ? "bg-stone-800 text-white"
                        : "bg-stone-100 text-stone-600 hover:bg-stone-200"
                    }`}
                  >
                    {l.label}
                  </button>
                ))}
              </div>
            </div>

            <button
              type="button"
              onClick={runSynthesize}
              disabled={!canSubmit}
              className="mt-2 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-amber-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-all hover:bg-amber-700 disabled:opacity-40"
            >
              {synthBusy ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4" />
              )}
              Sentezle
            </button>
          </div>
        </div>

        {/* Right — synthesis result */}
        <div className="min-w-0 flex-1">
          <div className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="font-display text-lg font-semibold text-stone-800">
                Literatür Sentezi
              </h2>
              {result && (
                <span className="inline-flex items-center gap-1 rounded-full bg-stone-100 px-3 py-1 text-[11px] font-medium text-stone-600">
                  <BookOpen className="h-3 w-3" />
                  Sadakat {(result.total_faithfulness * 100).toFixed(0)}%
                </span>
              )}
            </div>

            {!result && !synthBusy && (
              <p className="rounded-xl border border-dashed border-stone-200 bg-stone-50 p-6 text-center text-sm text-stone-500">
                Soldan makale seç, modu belirle ve "Sentezle"ye bas.
              </p>
            )}

            {synthBusy && (
              <p className="flex items-center gap-2 text-sm text-stone-500">
                <Loader2 className="h-4 w-4 animate-spin" />
                Sentez hazırlanıyor…
              </p>
            )}

            {result && (
              <>
                {result.theme_warning && (
                  <div className="mb-4 flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
                    <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                    <span>{result.theme_warning}</span>
                  </div>
                )}

                {/* Synthesis text */}
                <div className="space-y-4">
                  {paragraphs.map((para, i) => (
                    <p
                      key={i}
                      className="font-display text-base leading-[1.8] text-stone-700"
                    >
                      {para}
                    </p>
                  ))}
                </div>

                {/* Sentence-level faithfulness */}
                {result.sentences.length > 0 && (
                  <div className="mt-6 border-t border-stone-100 pt-4">
                    <p className="mb-2 text-xs font-medium uppercase tracking-wide text-stone-400">
                      Cümle sadakati
                    </p>
                    <ul className="space-y-2">
                      {result.sentences.map((s, idx) => {
                        const cfg = FLAG_CFG[s.flag];
                        const Icon = cfg.icon;
                        return (
                          <li
                            key={idx}
                            data-testid="synth-sentence"
                            className="rounded-lg border border-stone-100 bg-stone-50/40 p-2.5"
                          >
                            <div className="flex items-start gap-2">
                              <span
                                className={`inline-flex shrink-0 items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium ${cfg.color}`}
                              >
                                <Icon className="h-3 w-3" />
                                {cfg.label}
                              </span>
                              <p className="text-xs leading-relaxed text-stone-600">
                                {s.text}
                              </p>
                            </div>
                            {s.citations.length > 0 && (
                              <p className="mt-1 ml-1 font-mono text-[10px] text-stone-400">
                                {s.citations.join(", ")}
                              </p>
                            )}
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                )}

                {/* References */}
                {result.references.length > 0 && (
                  <div className="mt-6 border-t border-stone-100 pt-4">
                    <p className="mb-2 text-xs font-medium uppercase tracking-wide text-stone-400">
                      Kaynaklar
                    </p>
                    <ol className="space-y-1.5">
                      {result.references.map((ref) => (
                        <li
                          key={ref.index}
                          className="flex gap-2 text-xs text-stone-600"
                        >
                          <span className="font-mono text-stone-400">
                            [{String(ref.index).padStart(2, "0")}]
                          </span>
                          <span>{ref.citation}</span>
                        </li>
                      ))}
                    </ol>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
