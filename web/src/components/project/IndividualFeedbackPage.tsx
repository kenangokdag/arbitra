"use client";

import { useCallback, useEffect, useState, useSyncExternalStore } from "react";
import { useParams } from "next/navigation";
import {
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  Loader2,
  MessageSquare,
  Sparkles,
} from "lucide-react";
import { AdvisorBanner } from "@/components/project/AdvisorBanner";
import { apiFetch, ApiError } from "@/lib/api";
import { getDefenseSessionId } from "@/lib/defenseSession";

// F13-S2.3 — defense-3 (6.3 Bireysel Kontrol).
// 4 endpoint binding:
//   GET  /api/workshop/checklist?doc_type=&lang=
//   PUT  /api/workshop/individual-check?doc_type=&lang=
//   GET  /api/workshop/journal-suggest?project_id=&field=
//   POST /api/workshop/personal-feedback

type DocType = "tez" | "makale";
type ChecklistLang = "tr" | "en";
type ChecklistResponse = "evet" | "hayir" | "yapamadim";

interface ChecklistItem {
  id: string;
  soru: string;
  aciklama: string;
  evet_metin: string;
  hayir_metin: string;
  yapamadim_metin: string;
  kritik: boolean;
  link: string | null;
}

interface ChecklistCategory {
  id: string;
  label: string;
  items: ChecklistItem[];
}

interface ChecklistResponseModel {
  version: string;
  language: ChecklistLang;
  doc_type: DocType;
  note: string | null;
  categories: ChecklistCategory[];
}

interface IndividualCheckCounters {
  session_id: string;
  total_items_answered: number;
  evet_count: number;
  hayir_count: number;
  yapamadim_count: number;
  critical_blocked: boolean;
}

interface JournalSuggestion {
  journal_id: string;
  name: string;
  indices: string[];
  sjr_quartile: string | null;
  scope_match: number | null;
  source: "dim_journal" | "hf_dergitarama" | "seed_json";
}

interface JournalSuggestResponse {
  journals: JournalSuggestion[];
  source_attribution: string[];
  fallback_used: boolean;
}

interface PersonalFeedbackResponse {
  session_id: string;
  feedback_paragraph: string;
  weak_areas: string[];
}

const RESPONSE_LABELS: Record<ChecklistLang, Record<ChecklistResponse, string>> = {
  tr: { evet: "Evet", hayir: "Hayır", yapamadim: "Yapamadım" },
  en: { evet: "Yes", hayir: "No", yapamadim: "Couldn't" },
};

const DOC_TYPE_LABELS: Record<DocType, string> = {
  tez: "Tez",
  makale: "Makale",
};

const LANG_LABELS: Record<ChecklistLang, string> = {
  tr: "Türkçe",
  en: "English",
};

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

export function IndividualFeedbackPage() {
  const params = useParams<{ id: string }>();
  const projectId = params?.id;

  const [docType, setDocType] = useState<DocType>("tez");
  const [lang, setLang] = useState<ChecklistLang>("tr");
  const sessionId = useSessionId(projectId);

  const [checklist, setChecklist] = useState<ChecklistResponseModel | null>(null);
  const [responses, setResponses] = useState<Record<string, ChecklistResponse>>({});
  const [counters, setCounters] = useState<IndividualCheckCounters | null>(null);
  const [savingItemId, setSavingItemId] = useState<string | null>(null);

  const [field, setField] = useState<string>("");
  const [suggestions, setSuggestions] = useState<JournalSuggestion[]>([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState<boolean>(false);

  const [manuscriptSummary, setManuscriptSummary] = useState<string>("");
  const [feedback, setFeedback] = useState<PersonalFeedbackResponse | null>(null);
  const [loadingFeedback, setLoadingFeedback] = useState<boolean>(false);

  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    apiFetch<ChecklistResponseModel>(
      `/api/workshop/checklist?doc_type=${docType}&lang=${lang}`,
      { method: "GET", signal: ctrl.signal },
    )
      .then((data) => {
        setChecklist(data);
        setResponses({});
        setCounters(null);
        setError(null);
      })
      .catch((e: unknown) => {
        if ((e as { name?: string })?.name === "AbortError") return;
        setError(e instanceof ApiError ? e.message : "Kontrol listesi alınamadı.");
      });
    return () => ctrl.abort();
  }, [docType, lang]);

  const loadingChecklist = checklist === null && error === null;

  const handleResponse = useCallback(
    async (
      categoryId: string,
      itemId: string,
      response: ChecklistResponse,
    ) => {
      setResponses((prev) => ({ ...prev, [itemId]: response }));
      if (!sessionId) {
        setError("Önce 5.1 Savunma Formatı'nda oturumu kaydedin.");
        return;
      }
      setSavingItemId(itemId);
      setError(null);
      try {
        const next = await apiFetch<IndividualCheckCounters>(
          `/api/workshop/individual-check?doc_type=${docType}&lang=${lang}`,
          {
            method: "PUT",
            body: {
              session_id: sessionId,
              checklist_id: categoryId,
              item_id: itemId,
              response,
            },
          },
        );
        setCounters(next);
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "Cevap kaydedilemedi.");
      } finally {
        setSavingItemId(null);
      }
    },
    [sessionId, docType, lang],
  );

  const loadSuggestions = useCallback(async () => {
    if (!projectId) return;
    setLoadingSuggestions(true);
    setError(null);
    try {
      const q = field.trim()
        ? `?project_id=${projectId}&field=${encodeURIComponent(field.trim())}`
        : `?project_id=${projectId}`;
      const resp = await apiFetch<JournalSuggestResponse>(
        `/api/workshop/journal-suggest${q}`,
        { method: "GET" },
      );
      setSuggestions(resp.journals);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Dergi önerileri alınamadı.");
    } finally {
      setLoadingSuggestions(false);
    }
  }, [projectId, field]);

  const loadFeedback = useCallback(async () => {
    if (!projectId || !sessionId) {
      setError("Geri-bildirim için önce oturumu kaydedin.");
      return;
    }
    setLoadingFeedback(true);
    setError(null);
    try {
      const resp = await apiFetch<PersonalFeedbackResponse>(
        "/api/workshop/personal-feedback",
        {
          method: "POST",
          body: {
            project_id: projectId,
            session_id: sessionId,
            doc_type: docType,
            lang,
            manuscript_summary: manuscriptSummary.trim() || null,
          },
        },
      );
      setFeedback(resp);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Geri-bildirim alınamadı.");
    } finally {
      setLoadingFeedback(false);
    }
  }, [projectId, sessionId, docType, lang, manuscriptSummary]);

  const responseLabels = RESPONSE_LABELS[lang];

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
          Savunma - 5.3
        </div>
        <h1 className="font-display italic" style={{ fontSize: 26, lineHeight: 1.2 }}>
          Bireysel kontrol
        </h1>
        <p style={{ fontSize: 14, color: "var(--color-ink-mute)", lineHeight: 1.5 }}>
          Her maddeyi yanıtla; kritik eksiklik varsa kırmızı kapı açılır.
        </p>
      </header>

      <AdvisorBanner
        zone="defense"
        message="Kontrol listesi senaryona göre değişir. Eksikleri birlikte göreceğiz."
      />

      {!sessionId && (
        <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>
            Önce <strong>5.1 Savunma Formatı</strong> sayfasında oturumu kaydedin.
            Cevaplarınız o oturuma bağlanacak.
          </span>
        </div>
      )}

      <section
        aria-label="Doc-type ve dil"
        className="flex flex-wrap items-center gap-4 rounded-xl p-4"
        style={{
          background: "var(--color-bg-card)",
          border: "1px solid var(--color-rule)",
        }}
      >
        <div className="flex items-center gap-2">
          <span
            className="font-mono uppercase"
            style={{ fontSize: 10, letterSpacing: "0.1em", color: "var(--color-ink-faint)" }}
          >
            Tür
          </span>
          {(["tez", "makale"] as DocType[]).map((dt) => (
            <button
              key={dt}
              type="button"
              onClick={() => setDocType(dt)}
              aria-pressed={docType === dt}
              className="rounded-md px-3 py-1 transition-colors"
              style={{
                background: docType === dt ? "var(--color-accent)" : "var(--color-bg)",
                color: docType === dt ? "var(--color-accent-fg)" : "var(--color-ink)",
                border: "1px solid var(--color-rule)",
                fontSize: 13,
              }}
            >
              {DOC_TYPE_LABELS[dt]}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <span
            className="font-mono uppercase"
            style={{ fontSize: 10, letterSpacing: "0.1em", color: "var(--color-ink-faint)" }}
          >
            Dil
          </span>
          {(["tr", "en"] as ChecklistLang[]).map((l) => (
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
                fontSize: 13,
              }}
            >
              {LANG_LABELS[l]}
            </button>
          ))}
        </div>
      </section>

      {error && (
        <div className="flex items-start gap-3 rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-700">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {counters?.critical_blocked && (
        <div
          role="alert"
          className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800"
        >
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>
            <strong>Kritik kapı kapalı.</strong> En az bir kritik maddeye “hayır”
            veya “yapamadım” verdiniz. Savunmaya çıkmadan önce çözmeniz öneriliyor.
          </span>
        </div>
      )}

      {counters && (
        <section
          aria-label="Sayim"
          className="grid grid-cols-3 gap-3"
        >
          <Stat label={responseLabels.evet} value={counters.evet_count} color="emerald" />
          <Stat label={responseLabels.hayir} value={counters.hayir_count} color="red" />
          <Stat label={responseLabels.yapamadim} value={counters.yapamadim_count} color="amber" />
        </section>
      )}

      {loadingChecklist && (
        <div className="flex items-center gap-2 text-sm text-stone-500">
          <Loader2 className="h-4 w-4 animate-spin" /> Kontrol listesi yükleniyor…
        </div>
      )}

      {checklist?.categories.map((cat) => (
        <section
          key={cat.id}
          aria-label={`Kategori: ${cat.label}`}
          className="rounded-xl p-5"
          style={{
            background: "var(--color-bg-card)",
            border: "1px solid var(--color-rule)",
          }}
        >
          <h2
            className="font-display mb-3 flex items-center gap-2"
            style={{ fontSize: 16, color: "var(--color-ink)" }}
          >
            <BookOpen className="h-4 w-4" />
            {cat.label}
          </h2>
          <ul className="space-y-3">
            {cat.items.map((item) => {
              const current = responses[item.id];
              const isSaving = savingItemId === item.id;
              return (
                <li
                  key={item.id}
                  className="rounded-md p-3"
                  style={{
                    background: "var(--color-bg)",
                    border: "1px solid var(--color-rule-soft)",
                  }}
                >
                  <div className="mb-2 flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <div style={{ fontSize: 14, color: "var(--color-ink)", lineHeight: 1.4 }}>
                        {item.soru}
                        {item.kritik && (
                          <span
                            className="ml-2 rounded-full px-2 py-0.5 align-middle font-mono"
                            style={{
                              fontSize: 10,
                              background: "rgb(254 226 226)",
                              color: "rgb(153 27 27)",
                            }}
                          >
                            kritik
                          </span>
                        )}
                      </div>
                      <div
                        style={{
                          fontSize: 12.5,
                          color: "var(--color-ink-mute)",
                          marginTop: 4,
                          lineHeight: 1.5,
                        }}
                      >
                        {item.aciklama}
                      </div>
                    </div>
                    {isSaving && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    {(["evet", "hayir", "yapamadim"] as ChecklistResponse[]).map((r) => {
                      const active = current === r;
                      return (
                        <button
                          key={r}
                          type="button"
                          onClick={() => void handleResponse(cat.id, item.id, r)}
                          disabled={isSaving}
                          aria-pressed={active}
                          className="rounded-md px-3 py-1 transition-colors disabled:opacity-50"
                          style={{
                            background: active
                              ? r === "evet"
                                ? "rgb(220 252 231)"
                                : r === "hayir"
                                  ? "rgb(254 226 226)"
                                  : "rgb(254 243 199)"
                              : "var(--color-bg-card)",
                            color: active
                              ? r === "evet"
                                ? "rgb(22 101 52)"
                                : r === "hayir"
                                  ? "rgb(153 27 27)"
                                  : "rgb(146 64 14)"
                              : "var(--color-ink-mute)",
                            border: "1px solid var(--color-rule)",
                            fontSize: 12.5,
                          }}
                        >
                          {responseLabels[r]}
                        </button>
                      );
                    })}
                  </div>
                </li>
              );
            })}
          </ul>
        </section>
      ))}

      <section
        aria-label="Dergi onerisi"
        className="rounded-xl p-5"
        style={{
          background: "var(--color-bg-card)",
          border: "1px solid var(--color-rule)",
        }}
      >
        <h2 className="font-display mb-3" style={{ fontSize: 16, color: "var(--color-ink)" }}>
          Dergi Önerisi
        </h2>
        <div className="flex flex-wrap items-center gap-2">
          <input
            type="text"
            value={field}
            onChange={(e) => setField(e.target.value)}
            placeholder="Alan (opsiyonel) — örn. operasyon arastirmasi"
            className="min-w-[260px] flex-1 rounded-md px-3 py-2"
            style={{
              background: "var(--color-bg)",
              border: "1px solid var(--color-rule)",
              fontSize: 13.5,
            }}
          />
          <button
            type="button"
            onClick={() => void loadSuggestions()}
            disabled={loadingSuggestions}
            className="flex items-center gap-2 rounded-md px-3 py-2 transition-colors disabled:opacity-50"
            style={{
              background: "var(--color-accent-pale)",
              color: "var(--color-accent)",
              fontSize: 13,
            }}
          >
            {loadingSuggestions ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Sparkles className="h-3.5 w-3.5" />
            )}
            Dergi öner
          </button>
        </div>
        {suggestions.length > 0 && (
          <ul className="mt-3 space-y-2">
            {suggestions.map((j) => (
              <li
                key={j.journal_id}
                className="flex items-center justify-between gap-3 rounded-md p-3"
                style={{
                  background: "var(--color-bg)",
                  border: "1px solid var(--color-rule-soft)",
                }}
              >
                <div className="min-w-0 flex-1">
                  <div className="font-display" style={{ fontSize: 14 }}>
                    {j.name}
                  </div>
                  <div style={{ fontSize: 12, color: "var(--color-ink-mute)" }}>
                    {j.sjr_quartile ?? "—"}
                    {j.indices.length > 0 ? ` · ${j.indices.join(", ")}` : ""}
                    {" · "}kaynak: {j.source}
                  </div>
                </div>
                {j.scope_match != null && (
                  <span
                    className="font-mono"
                    style={{
                      fontSize: 11,
                      color: "var(--color-accent)",
                      background: "var(--color-accent-pale)",
                      padding: "2px 6px",
                      borderRadius: 999,
                    }}
                  >
                    {(j.scope_match * 100).toFixed(0)}% scope
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section
        aria-label="Kisisel geri bildirim"
        className="rounded-xl p-5"
        style={{
          background: "var(--color-bg-card)",
          border: "1px solid var(--color-rule)",
        }}
      >
        <h2
          className="font-display mb-3 flex items-center gap-2"
          style={{ fontSize: 16, color: "var(--color-ink)" }}
        >
          <MessageSquare className="h-4 w-4" />
          Kişisel Geri-Bildirim
        </h2>
        <textarea
          value={manuscriptSummary}
          onChange={(e) => setManuscriptSummary(e.target.value)}
          placeholder="Manüskri özetinizi (opsiyonel) yapıştırın — geri-bildirim daha hedefli olur."
          rows={3}
          className="w-full rounded-md px-3 py-2"
          style={{
            background: "var(--color-bg)",
            border: "1px solid var(--color-rule)",
            fontSize: 13.5,
          }}
        />
        <button
          type="button"
          onClick={() => void loadFeedback()}
          disabled={loadingFeedback || !sessionId}
          className="mt-3 flex items-center gap-2 rounded-md px-4 py-2 transition-colors disabled:opacity-50"
          style={{
            background: "var(--color-accent)",
            color: "var(--color-accent-fg)",
            fontSize: 13.5,
          }}
        >
          {loadingFeedback ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <CheckCircle2 className="h-4 w-4" />
          )}
          {loadingFeedback ? "Hazırlanıyor…" : "Geri-bildirim al"}
        </button>

        {feedback && (
          <div className="mt-4 rounded-md p-4" style={{ background: "var(--color-bg)" }}>
            <p style={{ fontSize: 14, lineHeight: 1.6, color: "var(--color-ink)" }}>
              {feedback.feedback_paragraph}
            </p>
            {feedback.weak_areas.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2">
                {feedback.weak_areas.map((w) => (
                  <span
                    key={w}
                    className="rounded-full font-mono"
                    style={{
                      fontSize: 11,
                      background: "rgb(254 243 199)",
                      color: "rgb(146 64 14)",
                      padding: "3px 10px",
                    }}
                  >
                    {w}
                  </span>
                ))}
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
  color,
}: {
  label: string;
  value: number;
  color: "emerald" | "red" | "amber";
}) {
  const palette: Record<
    "emerald" | "red" | "amber",
    { bg: string; fg: string }
  > = {
    emerald: { bg: "rgb(220 252 231)", fg: "rgb(22 101 52)" },
    red: { bg: "rgb(254 226 226)", fg: "rgb(153 27 27)" },
    amber: { bg: "rgb(254 243 199)", fg: "rgb(146 64 14)" },
  };
  const p = palette[color];
  return (
    <div
      className="rounded-md px-4 py-3"
      style={{ background: p.bg, color: p.fg }}
    >
      <div className="font-mono" style={{ fontSize: 10, letterSpacing: "0.1em" }}>
        {label.toUpperCase()}
      </div>
      <div className="font-display" style={{ fontSize: 22, lineHeight: 1.1 }}>
        {value}
      </div>
    </div>
  );
}
