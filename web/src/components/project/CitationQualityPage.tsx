"use client";

import { useCallback, useState } from "react";
import { useParams } from "next/navigation";
import {
  Search,
  ShieldCheck,
  FileText,
  Scale,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  AlertCircle,
  HelpCircle,
} from "lucide-react";
import { AdvisorBanner } from "@/components/project/AdvisorBanner";
import { apiFetch, ApiError } from "@/lib/api";

// F13-S3.5 — authoring-4 (5.4 Atıf & Stil Kılavuzu).
// V1-S17 P010 (KD-V1-S17-05): curation-1 → authoring-4 taşındı; eski
// ReferenceStylePage stub'i silindi, bu sayfa onun yerini aldı.
// 4 endpoint binding:
//   GET  /api/workshop/citation-search
//   POST /api/workshop/citation-verify
//   GET  /api/workshop/format-citation
//   POST /api/workshop/citation-balance

type CitationStyle = "apa" | "vancouver" | "ieee" | "chicago" | "mla";
type Lang = "tr" | "en" | "id";
type SentenceStatus = "ok" | "hallucinated" | "topic_mismatch" | "needs_citation";

interface CitationPaper {
  paper_id: string;
  title: string;
  authors: string[];
  year: number | null;
  venue: string | null;
  doi: string | null;
  citations_count: number;
}

interface CitationSearchResponse {
  papers: CitationPaper[];
  synonyms_tried: string[];
  total_results: number;
}

interface CitationFinding {
  raw: string;
  author_guess: string;
  year_guess: number | null;
  matched_paper_id: string | null;
}

interface SentenceVerification {
  index: number;
  text: string;
  citations: CitationFinding[];
  status: SentenceStatus;
}

interface CitationVerifyResponse {
  sentences: SentenceVerification[];
  total_citations: number;
  hallucinated_count: number;
  topic_mismatch_count: number;
  needs_citation_count: number;
}

interface FormatCitationResponse {
  paper_id: string;
  style: CitationStyle;
  formatted_citation: string;
  bibtex_entry: string;
}

interface CitationBalanceResponse {
  total: number;
  old_count: number;
  recent_count: number;
  old_pct: number;
  recent_pct: number;
  suggested_papers: CitationPaper[];
  balance_advice: string;
}

const STYLES: CitationStyle[] = ["apa", "vancouver", "ieee", "chicago", "mla"];
const LANGS: Lang[] = ["tr", "en", "id"];

const STATUS_CFG: Record<
  SentenceStatus,
  { label: string; color: string; icon: typeof CheckCircle2 }
> = {
  ok: { label: "Uygun", color: "bg-emerald-100 text-emerald-700", icon: CheckCircle2 },
  hallucinated: { label: "Hayalet", color: "bg-red-100 text-red-700", icon: XCircle },
  topic_mismatch: {
    label: "Konu uyumsuz",
    color: "bg-amber-100 text-amber-700",
    icon: AlertCircle,
  },
  needs_citation: {
    label: "Atıf gerek",
    color: "bg-blue-100 text-blue-700",
    icon: HelpCircle,
  },
};

export function CitationQualityPage() {
  const params = useParams<{ id: string }>();
  const projectId = params?.id;

  // search panel
  const [searchQuery, setSearchQuery] = useState("");
  const [searchLang, setSearchLang] = useState<Lang>("tr");
  const [searchResult, setSearchResult] = useState<CitationSearchResponse | null>(null);
  const [searchBusy, setSearchBusy] = useState(false);

  // verify panel
  const [documentText, setDocumentText] = useState("");
  const [verifyStyle, setVerifyStyle] = useState<CitationStyle>("apa");
  const [verifyResult, setVerifyResult] = useState<CitationVerifyResponse | null>(null);
  const [verifyBusy, setVerifyBusy] = useState(false);

  // format panel
  const [formatPaperId, setFormatPaperId] = useState("");
  const [formatStyle, setFormatStyle] = useState<CitationStyle>("apa");
  const [formatResult, setFormatResult] = useState<FormatCitationResponse | null>(null);
  const [formatBusy, setFormatBusy] = useState(false);

  // balance panel
  const [balanceIds, setBalanceIds] = useState("");
  const [balanceResult, setBalanceResult] = useState<CitationBalanceResponse | null>(null);
  const [balanceBusy, setBalanceBusy] = useState(false);

  const [error, setError] = useState<string | null>(null);

  const runSearch = useCallback(async () => {
    if (!projectId || !searchQuery.trim()) return;
    setSearchBusy(true);
    setError(null);
    try {
      const data = await apiFetch<CitationSearchResponse>(
        `/api/workshop/citation-search?project_id=${encodeURIComponent(projectId)}&query=${encodeURIComponent(searchQuery.trim())}&lang=${searchLang}`,
        { method: "GET" },
      );
      setSearchResult(data);
    } catch (e: unknown) {
      setError(e instanceof ApiError ? `Arama hatasi (${e.status})` : "Arama hatasi");
    } finally {
      setSearchBusy(false);
    }
  }, [projectId, searchQuery, searchLang]);

  const runVerify = useCallback(async () => {
    if (!projectId || !documentText.trim()) return;
    setVerifyBusy(true);
    setError(null);
    try {
      const data = await apiFetch<CitationVerifyResponse>(
        "/api/workshop/citation-verify",
        {
          method: "POST",
          body: {
            project_id: projectId,
            document_text: documentText,
            citation_style: verifyStyle,
          },
        },
      );
      setVerifyResult(data);
    } catch (e: unknown) {
      setError(e instanceof ApiError ? `Dogrulama hatasi (${e.status})` : "Dogrulama hatasi");
    } finally {
      setVerifyBusy(false);
    }
  }, [projectId, documentText, verifyStyle]);

  const runFormat = useCallback(async () => {
    if (!formatPaperId.trim()) return;
    setFormatBusy(true);
    setError(null);
    try {
      const data = await apiFetch<FormatCitationResponse>(
        `/api/workshop/format-citation?paper_id=${encodeURIComponent(formatPaperId.trim())}&style=${formatStyle}`,
        { method: "GET" },
      );
      setFormatResult(data);
    } catch (e: unknown) {
      setError(e instanceof ApiError ? `Formatlama hatasi (${e.status})` : "Formatlama hatasi");
    } finally {
      setFormatBusy(false);
    }
  }, [formatPaperId, formatStyle]);

  const runBalance = useCallback(async () => {
    if (!projectId) return;
    const ids = balanceIds
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    if (ids.length === 0) return;
    setBalanceBusy(true);
    setError(null);
    try {
      const data = await apiFetch<CitationBalanceResponse>(
        "/api/workshop/citation-balance",
        {
          method: "POST",
          body: { project_id: projectId, citation_paper_ids: ids },
        },
      );
      setBalanceResult(data);
    } catch (e: unknown) {
      setError(e instanceof ApiError ? `Denge hatasi (${e.status})` : "Denge hatasi");
    } finally {
      setBalanceBusy(false);
    }
  }, [projectId, balanceIds]);

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <AdvisorBanner message="Atif kalitesi: havuzdan ara, metni dogrula, tek atifi formatla, eski-yeni dengeyi gor." />

      {error && (
        <div className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Panel 1 — Search */}
      <section className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
        <header className="mb-3 flex items-center gap-2">
          <Search className="h-4 w-4 text-stone-600" />
          <h3 className="font-display text-base font-semibold text-stone-800">
            Havuzdan ara
          </h3>
        </header>
        <div className="flex flex-wrap items-center gap-2">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Anahtar kelime veya iddia"
            className="flex-1 min-w-[260px] rounded-lg border border-stone-200 px-3 py-2 text-sm focus:border-stone-400 focus:outline-none"
          />
          <select
            value={searchLang}
            onChange={(e) => setSearchLang(e.target.value as Lang)}
            className="rounded-lg border border-stone-200 px-2 py-2 text-sm"
            aria-label="dil"
          >
            {LANGS.map((l) => (
              <option key={l} value={l}>
                {l.toUpperCase()}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={runSearch}
            disabled={!searchQuery.trim() || searchBusy}
            className="inline-flex items-center gap-2 rounded-lg bg-stone-800 px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
          >
            {searchBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
            Ara
          </button>
        </div>

        {searchResult && (
          <div className="mt-4 space-y-2">
            <p className="text-xs text-stone-500">
              {searchResult.total_results} sonuc
              {searchResult.synonyms_tried.length > 0
                ? ` · es anlamlilar: ${searchResult.synonyms_tried.join(", ")}`
                : ""}
            </p>
            <ul className="divide-y divide-stone-100 rounded-lg border border-stone-100">
              {searchResult.papers.map((p) => (
                <li key={p.paper_id} className="px-3 py-2">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-stone-800">
                        {p.title}
                      </p>
                      <p className="truncate text-xs text-stone-500">
                        {p.authors.join(", ")}
                        {p.year ? ` · ${p.year}` : ""}
                        {p.venue ? ` · ${p.venue}` : ""}
                      </p>
                    </div>
                    <span className="shrink-0 text-xs text-stone-500">
                      {p.citations_count} atıf
                    </span>
                  </div>
                  <p className="mt-1 font-mono text-[10px] text-stone-400">
                    {p.paper_id}
                  </p>
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>

      {/* Panel 2 — Verify */}
      <section className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
        <header className="mb-3 flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-stone-600" />
          <h3 className="font-display text-base font-semibold text-stone-800">
            Metni doğrula
          </h3>
        </header>
        <textarea
          value={documentText}
          onChange={(e) => setDocumentText(e.target.value)}
          placeholder="Metni buraya yapıştır (en fazla 50.000 karakter)"
          rows={6}
          className="w-full rounded-lg border border-stone-200 px-3 py-2 text-sm focus:border-stone-400 focus:outline-none"
        />
        <div className="mt-2 flex items-center gap-2">
          <select
            value={verifyStyle}
            onChange={(e) => setVerifyStyle(e.target.value as CitationStyle)}
            className="rounded-lg border border-stone-200 px-2 py-2 text-sm"
            aria-label="atif stili"
          >
            {STYLES.map((s) => (
              <option key={s} value={s}>
                {s.toUpperCase()}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={runVerify}
            disabled={!documentText.trim() || verifyBusy}
            className="inline-flex items-center gap-2 rounded-lg bg-stone-800 px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
          >
            {verifyBusy ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <ShieldCheck className="h-4 w-4" />
            )}
            Doğrula
          </button>
        </div>

        {verifyResult && (
          <div className="mt-4 space-y-3">
            <div className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
              <Stat label="Toplam atıf" value={verifyResult.total_citations} />
              <Stat label="Hayalet" value={verifyResult.hallucinated_count} tone="red" />
              <Stat
                label="Konu uyumsuz"
                value={verifyResult.topic_mismatch_count}
                tone="amber"
              />
              <Stat
                label="Atıf gerek"
                value={verifyResult.needs_citation_count}
                tone="blue"
              />
            </div>
            <ul className="space-y-2">
              {verifyResult.sentences.map((s) => {
                const cfg = STATUS_CFG[s.status];
                const Icon = cfg.icon;
                return (
                  <li
                    key={s.index}
                    className="rounded-lg border border-stone-100 p-3 text-sm"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <p className="flex-1 text-stone-800">{s.text}</p>
                      <span
                        className={`inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${cfg.color}`}
                      >
                        <Icon className="h-3 w-3" />
                        {cfg.label}
                      </span>
                    </div>
                    {s.citations.length > 0 && (
                      <p className="mt-1 text-xs text-stone-500">
                        {s.citations
                          .map(
                            (c) =>
                              `${c.author_guess}${c.year_guess ? ` ${c.year_guess}` : ""}${c.matched_paper_id ? ` ✓` : ""}`,
                          )
                          .join(" · ")}
                      </p>
                    )}
                  </li>
                );
              })}
            </ul>
          </div>
        )}
      </section>

      {/* Panel 3 — Format */}
      <section className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
        <header className="mb-3 flex items-center gap-2">
          <FileText className="h-4 w-4 text-stone-600" />
          <h3 className="font-display text-base font-semibold text-stone-800">
            Tek atıfı formatla
          </h3>
        </header>
        <div className="flex flex-wrap items-center gap-2">
          <input
            type="text"
            value={formatPaperId}
            onChange={(e) => setFormatPaperId(e.target.value)}
            placeholder="paper_id (örn. s2_1234)"
            className="flex-1 min-w-[220px] rounded-lg border border-stone-200 px-3 py-2 font-mono text-sm focus:border-stone-400 focus:outline-none"
          />
          <select
            value={formatStyle}
            onChange={(e) => setFormatStyle(e.target.value as CitationStyle)}
            className="rounded-lg border border-stone-200 px-2 py-2 text-sm"
            aria-label="format stili"
          >
            {STYLES.map((s) => (
              <option key={s} value={s}>
                {s.toUpperCase()}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={runFormat}
            disabled={!formatPaperId.trim() || formatBusy}
            className="inline-flex items-center gap-2 rounded-lg bg-stone-800 px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
          >
            {formatBusy ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <FileText className="h-4 w-4" />
            )}
            Formatla
          </button>
        </div>
        {formatResult && (
          <div className="mt-4 space-y-2">
            <div className="rounded-lg border border-stone-100 bg-stone-50 p-3">
              <p className="text-[10px] uppercase tracking-wide text-stone-500">
                {formatResult.style.toUpperCase()}
              </p>
              <p className="mt-1 text-sm text-stone-800">
                {formatResult.formatted_citation}
              </p>
            </div>
            <pre className="overflow-x-auto rounded-lg border border-stone-100 bg-stone-900 p-3 text-xs text-stone-100">
              {formatResult.bibtex_entry}
            </pre>
          </div>
        )}
      </section>

      {/* Panel 4 — Balance */}
      <section className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
        <header className="mb-3 flex items-center gap-2">
          <Scale className="h-4 w-4 text-stone-600" />
          <h3 className="font-display text-base font-semibold text-stone-800">
            Eski-yeni denge
          </h3>
        </header>
        <textarea
          value={balanceIds}
          onChange={(e) => setBalanceIds(e.target.value)}
          placeholder="paper_id listesi (virgülle ayır)"
          rows={3}
          className="w-full rounded-lg border border-stone-200 px-3 py-2 font-mono text-sm focus:border-stone-400 focus:outline-none"
        />
        <button
          type="button"
          onClick={runBalance}
          disabled={!balanceIds.trim() || balanceBusy}
          className="mt-2 inline-flex items-center gap-2 rounded-lg bg-stone-800 px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
        >
          {balanceBusy ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Scale className="h-4 w-4" />
          )}
          Dengele
        </button>

        {balanceResult && (
          <div className="mt-4 space-y-3">
            <div className="grid grid-cols-3 gap-2 text-xs">
              <Stat label="Toplam" value={balanceResult.total} />
              <Stat
                label="Eski (>10 yıl)"
                value={`${balanceResult.old_count} · %${Math.round(balanceResult.old_pct)}`}
                tone="amber"
              />
              <Stat
                label="Yeni (≤5 yıl)"
                value={`${balanceResult.recent_count} · %${Math.round(balanceResult.recent_pct)}`}
                tone="emerald"
              />
            </div>
            <p className="rounded-lg border border-stone-100 bg-amber-50/40 p-3 text-sm text-stone-800">
              {balanceResult.balance_advice}
            </p>
            {balanceResult.suggested_papers.length > 0 && (
              <div>
                <p className="mb-1 text-xs font-medium text-stone-600">
                  Önerilen yeni atıflar
                </p>
                <ul className="divide-y divide-stone-100 rounded-lg border border-stone-100">
                  {balanceResult.suggested_papers.map((p) => (
                    <li key={p.paper_id} className="px-3 py-2 text-sm">
                      <p className="truncate text-stone-800">{p.title}</p>
                      <p className="truncate text-xs text-stone-500">
                        {p.authors.join(", ")}
                        {p.year ? ` · ${p.year}` : ""}
                      </p>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: number | string;
  tone?: "red" | "amber" | "blue" | "emerald";
}) {
  const toneClass =
    tone === "red"
      ? "text-red-700"
      : tone === "amber"
      ? "text-amber-700"
      : tone === "blue"
      ? "text-blue-700"
      : tone === "emerald"
      ? "text-emerald-700"
      : "text-stone-800";
  return (
    <div className="rounded-lg border border-stone-100 bg-stone-50 px-3 py-2">
      <p className="text-[10px] uppercase tracking-wide text-stone-500">{label}</p>
      <p className={`text-base font-semibold ${toneClass}`}>{value}</p>
    </div>
  );
}
