"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { useParams } from "next/navigation";
import {
  Loader2,
  MessageSquare,
  Send,
  SkipForward,
  Clock,
  Sparkles,
  AlertTriangle,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { AdvisorBanner } from "@/components/project/AdvisorBanner";
import { apiFetch, ApiError } from "@/lib/api";

// F13-S2.1 — 6.5 Jüri Simülasyonu: 5 backend endpoint binding.
// Plan: Page_Design/Sayfa_Plani_v2/6.5_juri_simulasyonu.rtf
// Endpoints (api/routes/workshop.py:744-825):
//   defense/session, defense/jury-question, defense/hyde-fanout-rerank,
//   defense/answer-score, defense/consistency-check, defense/jury-decision-band.

const TIMER_SECONDS = 60;
const MIN_MANUSCRIPT_CHARS = 100;
const DEFAULT_SESSION_CONFIG = {
  session_type: "tez" as const,
  jury_size: 5,
  title: "Tez Savunması",
  field: "Genel",
  preferred_lang: "tr" as const,
};

type Phase =
  | "idle"
  | "starting"
  | "questioning"
  | "scoring"
  | "finalizing"
  | "final"
  | "error";

type PersonaKey =
  | "canli"
  | "anti_tez"
  | "yontemci"
  | "dis_disiplin"
  | "pratisyen";

type JuryReaction = "satisfied" | "probing" | "dissatisfied";

interface JuryQuestion {
  persona: PersonaKey;
  idx: number;
  text: string;
  depth: number;
  parent_idx: number | null;
  anchor: string | null;
}

interface JuryQuestionResponse {
  session_id: string;
  questions: JuryQuestion[];
  active_idx: number;
  timer_seconds: number;
}

interface HydeChunk {
  paper_id: string;
  chunk_idx: number;
  sentence: string;
  score: number;
}

interface HydeFanoutResponse {
  hyde_hypotheticals: string[];
  rerank_top: HydeChunk[];
  missing_concepts: string[];
  fanout_used: boolean;
  rerank_used: boolean;
}

interface AnswerScoreResponse {
  session_id: string;
  question_idx: number;
  evidence_coverage: number;
  depth_score: number;
  clarity_score: number;
  weighted_score: number;
  jury_reaction: JuryReaction;
  missing_concepts: string[];
  follow_up_triggered: boolean;
}

interface ConsistencyConflict {
  q_idx_a: number;
  q_idx_b: number;
  conflict_text: string;
}

interface ConsistencyCheckResponse {
  session_id: string;
  conflicts: ConsistencyConflict[];
  summary: string;
}

interface JuryDecisionBandResponse {
  session_id: string;
  prediction: "accept" | "minor_revision" | "major_revision" | "reject";
  confidence: number;
  score_summary: Record<string, number>;
  advice: string;
}

interface DefenseSession {
  id: string;
  project_id: string;
  session_type: string;
  jury_size: number;
  title: string;
  field: string;
  preferred_lang: string;
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

interface HistoryEntry {
  question: JuryQuestion;
  answer: string;
  score: AnswerScoreResponse;
}

const PERSONA_LABEL: Record<PersonaKey, string> = {
  canli: "Jüri Başkanı",
  anti_tez: "Anti-Tez",
  yontemci: "Yöntemci",
  dis_disiplin: "Dış Disiplin",
  pratisyen: "Pratisyen",
};

const REACTION_STYLE: Record<JuryReaction, { label: string; cls: string }> = {
  satisfied: { label: "Memnun", cls: "text-emerald-700 bg-emerald-50 border-emerald-200" },
  probing: { label: "Sorgulayıcı", cls: "text-amber-700 bg-amber-50 border-amber-200" },
  dissatisfied: { label: "Memnun Değil", cls: "text-red-700 bg-red-50 border-red-200" },
};

const VERDICT_LABEL: Record<JuryDecisionBandResponse["prediction"], string> = {
  accept: "Kabul",
  minor_revision: "Küçük Düzeltme",
  major_revision: "Büyük Düzeltme",
  reject: "Red",
};

function joinManuscript(sections: ManuscriptSection[]): string {
  return sections.map((s) => s.content?.trim() ?? "").filter(Boolean).join("\n\n");
}

export function JurySimulationPage() {
  const params = useParams<{ id: string }>();
  const projectId = params?.id ?? "";

  const [phase, setPhase] = useState<Phase>("idle");
  const [error, setError] = useState<string | null>(null);

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [manuscriptText, setManuscriptText] = useState<string>("");

  const [questions, setQuestions] = useState<JuryQuestion[]>([]);
  const [activeIdx, setActiveIdx] = useState<number>(0);

  const [hydeStore, setHydeStore] = useState<{ idx: number; data: HydeFanoutResponse } | null>(null);

  const [answer, setAnswer] = useState<string>("");
  const [timer, setTimer] = useState<number>(TIMER_SECONDS);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const submittedRef = useRef<boolean>(false);

  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [consistency, setConsistency] = useState<ConsistencyCheckResponse | null>(null);
  const [decision, setDecision] = useState<JuryDecisionBandResponse | null>(null);

  const active = questions[activeIdx];
  const hyde = hydeStore && active && hydeStore.idx === active.idx ? hydeStore.data : null;
  const hydeLoading = phase === "questioning" && active != null && hyde == null;

  // ── Session + manuscript bootstrap ────────────────────────────────────────
  const startSimulation = useCallback(async () => {
    if (!projectId) {
      setError("Proje kimliği bulunamadı.");
      setPhase("error");
      return;
    }
    setError(null);
    setPhase("starting");
    setHistory([]);
    setConsistency(null);
    setDecision(null);
    setActiveIdx(0);
    setAnswer("");

    try {
      const session = await apiFetch<DefenseSession>(
        "/api/workshop/defense/session",
        {
          method: "POST",
          body: { project_id: projectId, ...DEFAULT_SESSION_CONFIG },
        },
      );

      const manuscript = await apiFetch<ManuscriptResponse>(
        `/api/workshop/manuscript?project_id=${projectId}`,
        { method: "GET" },
      );
      const text = joinManuscript(manuscript.sections);
      if (text.length < MIN_MANUSCRIPT_CHARS) {
        setError(
          `Önce "Yayın İçeriği" sayfasında en az ${MIN_MANUSCRIPT_CHARS} karakter yazın (şu an ${text.length}).`,
        );
        setPhase("error");
        return;
      }

      const jury = await apiFetch<JuryQuestionResponse>(
        "/api/workshop/defense/jury-question",
        {
          method: "POST",
          body: {
            project_id: projectId,
            session_id: session.id,
            manuscript_text: text,
            lang: "tr",
          },
        },
      );

      setSessionId(session.id);
      setManuscriptText(text);
      setQuestions(jury.questions);
      setActiveIdx(jury.active_idx);
      setTimer(jury.timer_seconds ?? TIMER_SECONDS);
      submittedRef.current = false;
      setPhase("questioning");
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Simülasyon başlatılamadı.";
      setError(msg);
      setPhase("error");
    }
  }, [projectId]);

  // ── HyDE fetch when active question changes ──────────────────────────────
  useEffect(() => {
    if (phase !== "questioning" || !active) return;
    if (hyde) return; // already fetched for this idx
    let cancelled = false;
    const currentIdx = active.idx;
    apiFetch<HydeFanoutResponse>("/api/workshop/defense/hyde-fanout-rerank", {
      method: "POST",
      body: {
        project_id: projectId,
        question_text: active.text,
        manuscript_text: manuscriptText,
        lang: "tr",
      },
    })
      .then((data) => {
        if (!cancelled) setHydeStore({ idx: currentIdx, data });
      })
      .catch(() => {
        if (!cancelled)
          setHydeStore({
            idx: currentIdx,
            data: {
              hyde_hypotheticals: [],
              rerank_top: [],
              missing_concepts: [],
              fanout_used: false,
              rerank_used: false,
            },
          });
      });
    return () => {
      cancelled = true;
    };
  }, [phase, active, hyde, projectId, manuscriptText]);

  // ── Timer countdown ──────────────────────────────────────────────────────
  useEffect(() => {
    if (phase !== "questioning") return;
    if (timer <= 0) return;
    const tid = window.setTimeout(() => setTimer((t) => t - 1), 1000);
    return () => window.clearTimeout(tid);
  }, [phase, timer]);

  // ── Submit answer (manual or timeout) ─────────────────────────────────────
  const submitAnswer = useCallback(
    async (auto: boolean) => {
      if (!sessionId || !active) return;
      if (submittedRef.current) return;
      submittedRef.current = true;
      setSubmitting(true);
      setError(null);
      try {
        const elapsed = TIMER_SECONDS - Math.max(0, timer);
        const finalAnswer = auto && !answer.trim() ? "(süre doldu, cevap verilmedi)" : answer.trim();
        const score = await apiFetch<AnswerScoreResponse>(
          "/api/workshop/defense/answer-score",
          {
            method: "POST",
            body: {
              session_id: sessionId,
              question_idx: active.idx,
              user_answer: finalAnswer,
              answer_seconds: elapsed,
              hyde_top: hyde?.rerank_top ?? [],
              hyde_hypotheticals: hyde?.hyde_hypotheticals ?? [],
              key_concepts: hyde?.missing_concepts ?? [],
            },
          },
        );

        setHistory((h) => [...h, { question: active, answer: finalAnswer, score }]);
        setAnswer("");

        const nextIdx = activeIdx + 1;
        if (nextIdx >= questions.length) {
          setPhase("finalizing");
          try {
            const cons = await apiFetch<ConsistencyCheckResponse>(
              "/api/workshop/defense/consistency-check",
              { method: "POST", body: { session_id: sessionId } },
            );
            setConsistency(cons);
            const dec = await apiFetch<JuryDecisionBandResponse>(
              "/api/workshop/defense/jury-decision-band",
              { method: "POST", body: { session_id: sessionId } },
            );
            setDecision(dec);
            setPhase("final");
          } catch (e) {
            const msg = e instanceof ApiError ? e.message : "Karar hesaplanamadı.";
            setError(msg);
            setPhase("error");
          }
        } else {
          setActiveIdx(nextIdx);
          setTimer(TIMER_SECONDS);
          submittedRef.current = false;
        }
      } catch (e) {
        const msg = e instanceof ApiError ? e.message : "Cevap kaydedilemedi.";
        setError(msg);
        submittedRef.current = false;
      } finally {
        setSubmitting(false);
      }
    },
    [sessionId, active, activeIdx, questions.length, answer, timer, hyde],
  );

  // Auto-submit on timeout
  useEffect(() => {
    if (phase !== "questioning") return;
    if (timer > 0) return;
    if (submittedRef.current) return;
    void submitAnswer(true);
  }, [phase, timer, submitAnswer]);

  const skipQuestion = useCallback(() => {
    if (submittedRef.current) return;
    setAnswer("");
    void submitAnswer(true);
  }, [submitAnswer]);

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6">
      <AdvisorBanner
        zone="defense"
        message="Jüri simülasyonu — 5 persona, 60sn timer, HyDE arka plan kanıt çekme. Gerçek savunma stresini sim ediyoruz."
      />

      {error && (
        <div className="flex items-start gap-3 rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-700">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <div className="flex-1">
            <p className="font-medium">Hata</p>
            <p className="mt-1">{error}</p>
          </div>
        </div>
      )}

      {phase === "idle" && (
        <div className="rounded-2xl border border-stone-200 bg-white p-10 text-center shadow-sm">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-amber-50">
            <MessageSquare className="h-8 w-8 text-amber-500" />
          </div>
          <h2 className="font-display mb-2 text-xl font-semibold text-stone-800">
            Jüri &amp; Hakem Simülasyonu
          </h2>
          <p className="mb-8 text-sm text-stone-500">
            5 jüri persona, soru başına 60 saniye, gerçek savunma stresi.
          </p>
          <button
            onClick={startSimulation}
            disabled={!projectId}
            className="inline-flex items-center gap-2 rounded-xl bg-amber-500 px-8 py-3 text-sm font-semibold text-white shadow-sm hover:bg-amber-600 disabled:opacity-50"
          >
            Simülasyonu Başlat
          </button>
        </div>
      )}

      {phase === "starting" && (
        <div className="flex items-center justify-center gap-3 rounded-2xl border border-stone-200 bg-white p-10 text-stone-500">
          <Loader2 className="h-5 w-5 animate-spin" />
          <span className="text-sm">Oturum oluşturuluyor, tez okunuyor, jüri soruları hazırlanıyor…</span>
        </div>
      )}

      {phase === "error" && (
        <div className="rounded-2xl border border-stone-200 bg-white p-8 text-center shadow-sm">
          <button
            onClick={startSimulation}
            className="inline-flex items-center gap-2 rounded-xl border border-stone-200 bg-white px-6 py-2.5 text-sm font-medium text-stone-700 hover:bg-stone-50"
          >
            Tekrar Dene
          </button>
        </div>
      )}

      {/* History so far */}
      {(phase === "questioning" || phase === "scoring" || phase === "finalizing" || phase === "final") &&
        history.map((item) => (
          <div key={item.question.idx} className="space-y-2">
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
              <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-amber-700">
                {PERSONA_LABEL[item.question.persona]} · Soru {item.question.idx + 1}
                {item.question.depth === 2 ? " (alt soru)" : ""}
              </p>
              <p className="text-sm text-stone-800">{item.question.text}</p>
            </div>
            <div className="ml-4 rounded-xl border border-blue-100 bg-blue-50 p-4">
              <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-blue-600">Yanıtınız</p>
              <p className="text-sm text-stone-700 whitespace-pre-wrap">{item.answer}</p>
            </div>
            <div className={`ml-4 rounded-xl border p-4 ${REACTION_STYLE[item.score.jury_reaction].cls}`}>
              <p className="mb-1 text-xs font-semibold uppercase tracking-wider">
                Jüri Tepkisi: {REACTION_STYLE[item.score.jury_reaction].label}
              </p>
              <p className="text-sm">
                Kanıt: {Math.round(item.score.evidence_coverage * 100)}% · Derinlik:{" "}
                {Math.round(item.score.depth_score * 100)}% · Netlik:{" "}
                {Math.round(item.score.clarity_score * 100)}% · Ağırlıklı:{" "}
                {Math.round(item.score.weighted_score * 100)}%
              </p>
              {item.score.missing_concepts.length > 0 && (
                <p className="mt-2 text-xs">
                  Eksik kavramlar: {item.score.missing_concepts.join(", ")}
                </p>
              )}
            </div>
          </div>
        ))}

      {/* Active question + answer ui */}
      {phase === "questioning" && active && (
        <div className="space-y-4">
          <div className="rounded-xl border-2 border-amber-200 bg-amber-50 p-5">
            <div className="mb-2 flex items-center justify-between">
              <p className="text-xs font-semibold uppercase tracking-wider text-amber-700">
                {PERSONA_LABEL[active.persona]} · Soru {active.idx + 1} / {questions.length}
                {active.depth === 2 ? " (alt soru)" : ""}
              </p>
              <span className="inline-flex items-center gap-1 rounded-full bg-white px-2 py-0.5 text-xs font-semibold text-amber-700">
                <Clock className="h-3 w-3" />
                {timer}s
              </span>
            </div>
            <p className="text-base font-medium text-stone-800">{active.text}</p>
          </div>

          {/* HyDE background indicator */}
          <div className="rounded-xl border border-stone-100 bg-stone-50 p-3 text-xs text-stone-500">
            <div className="flex items-center gap-2">
              <Sparkles className="h-3 w-3 text-stone-400" />
              {hydeLoading ? (
                <span>Arka plan kanıt zinciri çalışıyor (HyDE → fan-out → rerank)…</span>
              ) : hyde ? (
                <span>
                  {hyde.rerank_top.length} kanıt cümle bulundu
                  {hyde.missing_concepts.length > 0
                    ? ` · ${hyde.missing_concepts.length} eksik kavram tespit edildi`
                    : ""}
                </span>
              ) : (
                <span>Hazırlanıyor…</span>
              )}
            </div>
          </div>

          <textarea
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            placeholder="Yanıtınızı buraya yazın…"
            rows={5}
            disabled={submitting}
            className="w-full rounded-xl border border-stone-200 bg-white p-4 text-sm text-stone-700 outline-none focus:border-amber-300 focus:ring-2 focus:ring-amber-100 disabled:bg-stone-50"
          />

          <div className="flex items-center gap-3">
            <button
              onClick={() => void submitAnswer(false)}
              disabled={!answer.trim() || submitting}
              className="flex items-center gap-2 rounded-xl bg-amber-500 px-6 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-amber-600 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              Yanıtla
            </button>
            <button
              onClick={skipQuestion}
              disabled={submitting}
              className="flex items-center gap-2 rounded-xl border border-stone-200 bg-white px-5 py-2.5 text-sm font-medium text-stone-600 hover:bg-stone-50 disabled:opacity-50"
            >
              <SkipForward className="h-4 w-4" />
              Soruyu Atla
            </button>
          </div>
        </div>
      )}

      {phase === "finalizing" && (
        <div className="flex items-center justify-center gap-3 rounded-2xl border border-stone-200 bg-white p-10 text-stone-500">
          <Loader2 className="h-5 w-5 animate-spin" />
          <span className="text-sm">Tutarlılık taraması ve jüri kararı hesaplanıyor…</span>
        </div>
      )}

      {phase === "final" && decision && (
        <div className="space-y-4 rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between border-b border-stone-100 pb-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-stone-500">
                Jüri Kararı
              </p>
              <p className="font-display text-2xl font-semibold text-stone-800">
                {VERDICT_LABEL[decision.prediction]}
              </p>
            </div>
            <p className="text-sm text-stone-500">
              Güven: {Math.round(decision.confidence * 100)}%
            </p>
          </div>

          {decision.advice && (
            <div className="rounded-xl border border-blue-100 bg-blue-50 p-4 text-sm text-stone-700">
              {decision.advice}
            </div>
          )}

          {consistency && (
            <div className="rounded-xl border border-stone-100 bg-stone-50 p-4">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-stone-500">
                Tutarlılık Taraması
              </p>
              <p className="mb-2 text-sm text-stone-700">{consistency.summary}</p>
              {consistency.conflicts.length === 0 ? (
                <p className="flex items-center gap-2 text-sm text-emerald-700">
                  <CheckCircle2 className="h-4 w-4" /> Çelişki bulunamadı.
                </p>
              ) : (
                <ul className="space-y-1 text-sm text-red-700">
                  {consistency.conflicts.map((c, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <XCircle className="mt-0.5 h-4 w-4 shrink-0" />
                      <span>
                        Soru {c.q_idx_a + 1} ↔ Soru {c.q_idx_b + 1}: {c.conflict_text}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          <button
            onClick={startSimulation}
            className="inline-flex items-center gap-2 rounded-xl border border-stone-200 bg-white px-6 py-2.5 text-sm font-medium text-stone-700 hover:bg-stone-50"
          >
            Yeni Simülasyon
          </button>
        </div>
      )}
    </div>
  );
}
