"use client";

import { useCallback, useEffect, useMemo, useState, useSyncExternalStore } from "react";
import { useParams } from "next/navigation";
import {
  AlertTriangle,
  CheckCircle2,
  Eye,
  Loader2,
  Microscope,
  Sparkles,
  Target,
} from "lucide-react";
import { AdvisorBanner } from "@/components/project/AdvisorBanner";
import { apiFetch, ApiError } from "@/lib/api";
import { getDefenseSessionId } from "@/lib/defenseSession";

// F13-S2.5 — defense-4 (6.4 Dergi Simülasyonu) yeni sayfa.
// 3 endpoint binding:
//   POST /api/workshop/defense/reviewer-3persona   → 3 persona x N soru
//   POST /api/workshop/defense/statcheck            → Nuijten p-value tutarlilik
//   GET  /api/workshop/defense/journal-calibration  → review-distribution + verdict

type PersonaKey = "skeptik" | "sempatik" | "yontemci";
type Verdict = "accept" | "minor" | "major" | "reject";
type StatcheckStatus = "green" | "yellow" | "red";
type ReviewerLang = "tr" | "en";

interface ReviewerQuestion {
  text: string;
  depth: number;
  follow_up: string | null;
  anchor: string | null;
}

interface ReviewerPersonaOutput {
  questions: ReviewerQuestion[];
}

interface Reviewer3PersonaResponse {
  session_id: string;
  skeptik: ReviewerPersonaOutput;
  sempatik: ReviewerPersonaOutput;
  yontemci: ReviewerPersonaOutput;
}

interface StatcheckResult {
  test_type: "t" | "F" | "chi2" | "r";
  reported: Record<string, number | string>;
  reported_p: number;
  computed_p: number;
  diff: number;
  status: StatcheckStatus;
  match_text: string;
}

interface StatcheckSummary {
  total: number;
  green: number;
  yellow: number;
  red: number;
}

interface StatcheckResponse {
  session_id: string;
  results: StatcheckResult[];
  summary: StatcheckSummary;
}

interface JournalDistribution {
  window_size: number;
  accept_pct: number;
  major_pct: number;
  minor_pct: number;
  reject_pct: number;
  source: "manual" | "kmkarakaya_hf" | "field_average_placeholder";
}

interface JournalCalibrationResponse {
  journal_id: string | null;
  journal_name: string | null;
  distribution: JournalDistribution;
  prediction: Verdict;
  confidence: number;
  fallback_used: boolean;
}

interface ManuscriptSection {
  section_type: string;
  content: string;
  word_count: number;
}

interface ManuscriptResponse {
  project_id: string;
  sections: ManuscriptSection[];
}

const PERSONA_LABELS: Record<PersonaKey, string> = {
  skeptik: "Şüpheci",
  sempatik: "Sempatik",
  yontemci: "Yöntemci",
};

const VERDICT_LABELS: Record<Verdict, string> = {
  accept: "Kabul",
  minor: "Küçük Revizyon",
  major: "Büyük Revizyon",
  reject: "Red",
};

const VERDICT_COLORS: Record<Verdict, string> = {
  accept: "rgb(22 101 52)",
  minor: "rgb(146 64 14)",
  major: "rgb(120 53 15)",
  reject: "rgb(153 27 27)",
};

const MIN_MANUSCRIPT_CHARS = 100;

function subscribeStorage(callback: () => void): () => void {
  if (typeof window === "undefined") return () => {};
  window.addEventListener("storage", callback);
  return () => window.removeEventListener("storage", callback);
}

function useSessionId(projectId: string | undefined): string | null {
  return useSyncExternalStore(
    subscribeStorage,
    () => (projectId ? getDefenseSessionId(projectId) : null),
    () => null,
  );
}

export function JournalSimulationPage() {
  const params = useParams<{ id: string }>();
  const projectId = params?.id;
  const sessionId = useSessionId(projectId);

  const [manuscript, setManuscript] = useState<ManuscriptResponse | null>(null);
  const [manuscriptError, setManuscriptError] = useState<string | null>(null);

  const [lang, setLang] = useState<ReviewerLang>("tr");
  const [journalId, setJournalId] = useState<string>("");

  const [reviewers, setReviewers] = useState<Reviewer3PersonaResponse | null>(null);
  const [loadingReviewers, setLoadingReviewers] = useState<boolean>(false);

  const [statcheck, setStatcheck] = useState<StatcheckResponse | null>(null);
  const [loadingStatcheck, setLoadingStatcheck] = useState<boolean>(false);

  const [calibration, setCalibration] = useState<JournalCalibrationResponse | null>(null);
  const [loadingCalibration, setLoadingCalibration] = useState<boolean>(false);

  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) return;
    const ctrl = new AbortController();
    apiFetch<ManuscriptResponse>(
      `/api/workshop/manuscript?project_id=${projectId}`,
      { method: "GET", signal: ctrl.signal },
    )
      .then((data) => {
        setManuscript(data);
        setManuscriptError(null);
      })
      .catch((e: unknown) => {
        if ((e as { name?: string })?.name === "AbortError") return;
        setManuscriptError(
          e instanceof ApiError ? e.message : "Manüskri yüklenemedi.",
        );
      });
    return () => ctrl.abort();
  }, [projectId]);

  const manuscriptText = useMemo(() => {
    if (!manuscript) return "";
    return manuscript.sections.map((s) => s.content).join("\n\n").trim();
  }, [manuscript]);

  const manuscriptShort = manuscriptText.length < MIN_MANUSCRIPT_CHARS;

  const runReviewers = useCallback(async () => {
    if (!projectId || !sessionId) {
      setError("Önce 5.1 Savunma Formatı'nda oturumu kaydedin.");
      return;
    }
    if (manuscriptShort) {
      setError(`Manüskri en az ${MIN_MANUSCRIPT_CHARS} karakter olmalı.`);
      return;
    }
    setLoadingReviewers(true);
    setError(null);
    try {
      const resp = await apiFetch<Reviewer3PersonaResponse>(
        "/api/workshop/defense/reviewer-3persona",
        {
          method: "POST",
          body: {
            project_id: projectId,
            session_id: sessionId,
            manuscript_text: manuscriptText,
            target_journal_id: journalId.trim() || null,
            lang,
          },
        },
      );
      setReviewers(resp);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Hakem simülasyonu başarısız.");
    } finally {
      setLoadingReviewers(false);
    }
  }, [projectId, sessionId, manuscriptText, manuscriptShort, journalId, lang]);

  const runStatcheck = useCallback(async () => {
    if (!sessionId) {
      setError("Önce 5.1 Savunma Formatı'nda oturumu kaydedin.");
      return;
    }
    if (!manuscriptText || manuscriptText.length < 20) {
      setError("Manüskri statcheck için çok kısa (min 20 karakter).");
      return;
    }
    setLoadingStatcheck(true);
    setError(null);
    try {
      const resp = await apiFetch<StatcheckResponse>(
        "/api/workshop/defense/statcheck",
        {
          method: "POST",
          body: {
            session_id: sessionId,
            manuscript_text: manuscriptText,
          },
        },
      );
      setStatcheck(resp);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Statcheck başarısız.");
    } finally {
      setLoadingStatcheck(false);
    }
  }, [sessionId, manuscriptText]);

  const runCalibration = useCallback(async () => {
    if (!sessionId) {
      setError("Önce 5.1 Savunma Formatı'nda oturumu kaydedin.");
      return;
    }
    setLoadingCalibration(true);
    setError(null);
    try {
      const q = journalId.trim()
        ? `?session_id=${sessionId}&journal_id=${encodeURIComponent(journalId.trim())}`
        : `?session_id=${sessionId}`;
      const resp = await apiFetch<JournalCalibrationResponse>(
        `/api/workshop/defense/journal-calibration${q}`,
        { method: "GET" },
      );
      setCalibration(resp);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Kalibrasyon başarısız.");
    } finally {
      setLoadingCalibration(false);
    }
  }, [sessionId, journalId]);

  return (
    <div data-zone="defense" className="mx-auto max-w-5xl space-y-6 p-6">
      <header className="space-y-2">
        <div
          className="font-mono uppercase"
          style={{
            fontSize: 10,
            letterSpacing: "0.12em",
            color: "var(--color-ink-faint, #64748b)",
          }}
        >
          Savunma - 5.4
        </div>
        <h1 className="font-display italic" style={{ fontSize: 26, lineHeight: 1.2 }}>
          Dergi simülasyonu
        </h1>
        <p style={{ fontSize: 14, color: "var(--color-ink-mute)", lineHeight: 1.5 }}>
          Manüskrini 3 hakem persona&apos;ya, p-değer kontrolüne ve dergi kalibrasyonuna sok.
        </p>
      </header>

      <AdvisorBanner
        zone="defense"
        message="Üç hakem persona aynı manüskri okur — şüpheci kırar, sempatik onarır, yöntemci ölçer."
      />

      {!sessionId && (
        <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>
            Önce <strong>5.1 Savunma Formatı</strong> sayfasında oturumu kaydedin.
          </span>
        </div>
      )}

      {manuscriptError && (
        <div className="flex items-start gap-3 rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-700">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{manuscriptError}</span>
        </div>
      )}

      {error && (
        <div className="flex items-start gap-3 rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-700">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <section
        aria-label="Manuscript durumu"
        className="rounded-xl p-4"
        style={{
          background: "var(--color-bg-card)",
          border: "1px solid var(--color-rule)",
        }}
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div
              className="font-mono uppercase"
              style={{
                fontSize: 10,
                letterSpacing: "0.1em",
                color: "var(--color-ink-faint)",
              }}
            >
              Manüskri
            </div>
            <div style={{ fontSize: 13.5, color: "var(--color-ink-mute)" }}>
              {manuscript
                ? `${manuscript.sections.length} bölüm · ${manuscriptText.length} karakter`
                : "Yükleniyor…"}
              {manuscriptShort && manuscript
                ? ` · en az ${MIN_MANUSCRIPT_CHARS} karakter gerekli`
                : ""}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span
              className="font-mono uppercase"
              style={{
                fontSize: 10,
                letterSpacing: "0.1em",
                color: "var(--color-ink-faint)",
              }}
            >
              Dil
            </span>
            {(["tr", "en"] as ReviewerLang[]).map((l) => (
              <button
                key={l}
                type="button"
                onClick={() => setLang(l)}
                aria-pressed={lang === l}
                className="rounded-md px-3 py-1 transition-colors"
                style={{
                  background: lang === l ? "var(--color-accent)" : "var(--color-bg)",
                  color: lang === l ? "var(--color-accent-fg)" : "var(--color-ink)",
                  border: "1px solid var(--color-rule)",
                  fontSize: 12.5,
                }}
              >
                {l.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      </section>

      <section
        aria-label="Hedef dergi"
        className="rounded-xl p-4"
        style={{
          background: "var(--color-bg-card)",
          border: "1px solid var(--color-rule)",
        }}
      >
        <label className="block">
          <span
            className="font-mono uppercase mb-1 block"
            style={{
              fontSize: 10,
              letterSpacing: "0.1em",
              color: "var(--color-ink-faint)",
            }}
          >
            Hedef dergi (opsiyonel)
          </span>
          <input
            type="text"
            value={journalId}
            onChange={(e) => setJournalId(e.target.value)}
            placeholder="Dergi ID veya boş bırak (alan ortalaması)"
            className="w-full rounded-md px-3 py-2"
            style={{
              background: "var(--color-bg)",
              border: "1px solid var(--color-rule)",
              fontSize: 13.5,
            }}
          />
        </label>
      </section>

      <section
        aria-label="3-persona hakem"
        className="rounded-xl p-5"
        style={{
          background: "var(--color-bg-card)",
          border: "1px solid var(--color-rule)",
        }}
      >
        <div className="mb-3 flex items-center justify-between gap-3">
          <h2
            className="font-display flex items-center gap-2"
            style={{ fontSize: 16, color: "var(--color-ink)" }}
          >
            <Eye className="h-4 w-4" />
            3-Persona Hakem
          </h2>
          <button
            type="button"
            onClick={() => void runReviewers()}
            disabled={loadingReviewers || !sessionId || manuscriptShort}
            className="flex items-center gap-2 rounded-md px-3 py-1.5 transition-colors disabled:opacity-50"
            style={{
              background: "var(--color-accent)",
              color: "var(--color-accent-fg)",
              fontSize: 13,
            }}
          >
            {loadingReviewers ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Sparkles className="h-3.5 w-3.5" />
            )}
            Hakem çalıştır
          </button>
        </div>
        {reviewers && (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            {(["skeptik", "sempatik", "yontemci"] as PersonaKey[]).map((p) => (
              <div
                key={p}
                className="rounded-md p-3"
                style={{
                  background: "var(--color-bg)",
                  border: "1px solid var(--color-rule-soft)",
                }}
              >
                <div className="mb-2 font-display" style={{ fontSize: 14 }}>
                  {PERSONA_LABELS[p]}
                </div>
                <ol className="ml-4 list-decimal space-y-1">
                  {reviewers[p].questions.map((q, i) => (
                    <li
                      key={i}
                      style={{
                        fontSize: 12.5,
                        color: "var(--color-ink-soft)",
                        lineHeight: 1.4,
                      }}
                    >
                      {q.text}
                      {q.follow_up && (
                        <div
                          className="ml-2 mt-1 border-l-2 pl-2"
                          style={{
                            borderColor: "var(--color-rule)",
                            fontSize: 11.5,
                            color: "var(--color-ink-mute)",
                          }}
                        >
                          ↳ {q.follow_up}
                        </div>
                      )}
                    </li>
                  ))}
                </ol>
              </div>
            ))}
          </div>
        )}
      </section>

      <section
        aria-label="Statcheck"
        className="rounded-xl p-5"
        style={{
          background: "var(--color-bg-card)",
          border: "1px solid var(--color-rule)",
        }}
      >
        <div className="mb-3 flex items-center justify-between gap-3">
          <h2
            className="font-display flex items-center gap-2"
            style={{ fontSize: 16, color: "var(--color-ink)" }}
          >
            <Microscope className="h-4 w-4" />
            P-değer Tutarlılık (Statcheck)
          </h2>
          <button
            type="button"
            onClick={() => void runStatcheck()}
            disabled={loadingStatcheck || !sessionId || !manuscriptText}
            className="flex items-center gap-2 rounded-md px-3 py-1.5 transition-colors disabled:opacity-50"
            style={{
              background: "var(--color-accent-pale)",
              color: "var(--color-accent)",
              fontSize: 13,
            }}
          >
            {loadingStatcheck ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Sparkles className="h-3.5 w-3.5" />
            )}
            Statcheck çalıştır
          </button>
        </div>
        {statcheck && (
          <>
            <div className="mb-3 flex flex-wrap items-center gap-3">
              <Chip label="Toplam" value={statcheck.summary.total} tone="neutral" />
              <Chip label="Green" value={statcheck.summary.green} tone="emerald" />
              <Chip label="Yellow" value={statcheck.summary.yellow} tone="amber" />
              <Chip label="Red" value={statcheck.summary.red} tone="red" />
            </div>
            {statcheck.results.length === 0 ? (
              <p style={{ fontSize: 13, color: "var(--color-ink-mute)" }}>
                Metinde p-değer ifadesi bulunamadı.
              </p>
            ) : (
              <ul className="space-y-2">
                {statcheck.results.map((r, i) => (
                  <li
                    key={i}
                    className="rounded-md p-3"
                    style={{
                      background: "var(--color-bg)",
                      border: "1px solid var(--color-rule-soft)",
                    }}
                  >
                    <div className="mb-1 flex items-center gap-2">
                      <span
                        className="font-mono"
                        style={{
                          fontSize: 11,
                          padding: "2px 8px",
                          borderRadius: 999,
                          background:
                            r.status === "green"
                              ? "rgb(220 252 231)"
                              : r.status === "yellow"
                                ? "rgb(254 243 199)"
                                : "rgb(254 226 226)",
                          color:
                            r.status === "green"
                              ? "rgb(22 101 52)"
                              : r.status === "yellow"
                                ? "rgb(146 64 14)"
                                : "rgb(153 27 27)",
                        }}
                      >
                        {r.status.toUpperCase()}
                      </span>
                      <span
                        className="font-mono"
                        style={{ fontSize: 11, color: "var(--color-ink-faint)" }}
                      >
                        {r.test_type} · raporlanan p={r.reported_p.toFixed(4)} · hesaplanan p={r.computed_p.toFixed(4)}
                      </span>
                    </div>
                    <div style={{ fontSize: 12.5, color: "var(--color-ink-soft)", lineHeight: 1.4 }}>
                      {r.match_text}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </section>

      <section
        aria-label="Journal calibration"
        className="rounded-xl p-5"
        style={{
          background: "var(--color-bg-card)",
          border: "1px solid var(--color-rule)",
        }}
      >
        <div className="mb-3 flex items-center justify-between gap-3">
          <h2
            className="font-display flex items-center gap-2"
            style={{ fontSize: 16, color: "var(--color-ink)" }}
          >
            <Target className="h-4 w-4" />
            Dergi Kalibrasyonu
          </h2>
          <button
            type="button"
            onClick={() => void runCalibration()}
            disabled={loadingCalibration || !sessionId}
            className="flex items-center gap-2 rounded-md px-3 py-1.5 transition-colors disabled:opacity-50"
            style={{
              background: "var(--color-accent-pale)",
              color: "var(--color-accent)",
              fontSize: 13,
            }}
          >
            {loadingCalibration ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <CheckCircle2 className="h-3.5 w-3.5" />
            )}
            Kalibrasyonu çalıştır
          </button>
        </div>
        {calibration && (
          <div
            className="rounded-md p-4"
            style={{
              background: "var(--color-bg)",
              border: "1px solid var(--color-rule-soft)",
            }}
          >
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="font-display" style={{ fontSize: 15 }}>
                  {calibration.journal_name ?? calibration.journal_id ?? "Alan ortalaması"}
                </div>
                <div style={{ fontSize: 12, color: "var(--color-ink-mute)" }}>
                  {calibration.distribution.window_size} son makale ·
                  kaynak: {calibration.distribution.source}
                  {calibration.fallback_used ? " · fallback" : ""}
                </div>
              </div>
              <div
                className="rounded-full font-mono"
                style={{
                  fontSize: 11,
                  padding: "3px 10px",
                  background: "rgb(254 243 199)",
                  color: VERDICT_COLORS[calibration.prediction],
                }}
              >
                {VERDICT_LABELS[calibration.prediction]} · güven{" "}
                {(calibration.confidence * 100).toFixed(0)}%
              </div>
            </div>
            <div className="grid grid-cols-4 gap-2">
              {(["accept", "minor", "major", "reject"] as Verdict[]).map((v) => {
                const pct =
                  v === "accept"
                    ? calibration.distribution.accept_pct
                    : v === "minor"
                      ? calibration.distribution.minor_pct
                      : v === "major"
                        ? calibration.distribution.major_pct
                        : calibration.distribution.reject_pct;
                return (
                  <div key={v} className="text-center">
                    <div
                      className="font-mono"
                      style={{
                        fontSize: 10,
                        letterSpacing: "0.08em",
                        color: "var(--color-ink-faint)",
                      }}
                    >
                      {VERDICT_LABELS[v].toUpperCase()}
                    </div>
                    <div
                      className="font-display"
                      style={{ fontSize: 18, color: VERDICT_COLORS[v] }}
                    >
                      {(pct * 100).toFixed(0)}%
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

function Chip({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "neutral" | "emerald" | "amber" | "red";
}) {
  const palette: Record<
    "neutral" | "emerald" | "amber" | "red",
    { bg: string; fg: string }
  > = {
    neutral: { bg: "var(--color-bg)", fg: "var(--color-ink)" },
    emerald: { bg: "rgb(220 252 231)", fg: "rgb(22 101 52)" },
    amber: { bg: "rgb(254 243 199)", fg: "rgb(146 64 14)" },
    red: { bg: "rgb(254 226 226)", fg: "rgb(153 27 27)" },
  };
  const p = palette[tone];
  return (
    <span
      className="font-mono rounded-full"
      style={{
        fontSize: 11,
        padding: "3px 10px",
        background: p.bg,
        color: p.fg,
        border: "1px solid var(--color-rule)",
      }}
    >
      {label}: {value}
    </span>
  );
}
