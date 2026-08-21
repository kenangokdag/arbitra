"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import {
  AlertTriangle,
  ArrowRight,
  Check,
  Layers,
  Loader2,
  Sparkles,
} from "lucide-react";
import { AdvisorBanner } from "@/components/project/AdvisorBanner";
import { apiFetch, ApiError } from "@/lib/api";

// F13-S3.4 — authoring-2 (5.2 Yayın Taslağı).
// 2 endpoint binding:
//   POST /api/workshop/topic-proposals → 3 gap-uyumlu konu kartı
//   POST /api/workshop/draft-skeleton  → IMRaD 4 bölüm taslağı

type GapMatrixId = "M1" | "M7" | "M8";
type TopicLang = "tr" | "en" | "id";
type SectionName = "intro" | "methods" | "findings" | "discussion";

interface TopicSubQuestions {
  cautious: string;
  balanced: string;
  bold: string;
}

interface TopicEvidenceChain {
  gap_summary: string;
  method_summary: string;
  synthesis_summary: string;
}

interface TopicProposal {
  title: string;
  sub_questions: TopicSubQuestions;
  top_3_refs: string[];
  method_suggestion: string;
  evidence_chain: TopicEvidenceChain;
}

interface TopicProposalsResponse {
  proposals: TopicProposal[];
  generation_count: number;
  daily_quota_remaining: number;
  lang: TopicLang;
}

interface SkeletonPaperRef {
  paper_id: string;
  title: string;
  year: number | null;
  authors_short: string;
  citations_count: number;
}

interface DraftSection {
  name: SectionName;
  draft_paragraph: string;
  why_explanation: string;
  top_5_papers: SkeletonPaperRef[];
}

interface DraftSkeletonResponse {
  sections: DraftSection[];
  lang: TopicLang;
}

const SECTION_LABELS: Record<SectionName, string> = {
  intro: "Giriş",
  methods: "Yöntem",
  findings: "Bulgular",
  discussion: "Tartışma",
};

export function WritingSkeletonPage() {
  const params = useParams<{ id: string }>();
  const projectId = params?.id;

  const [matrixId, setMatrixId] = useState<GapMatrixId>("M1");
  const [axisX, setAxisX] = useState("");
  const [axisY, setAxisY] = useState("");
  const [methodProfile, setMethodProfile] = useState("");
  const [synthesisText, setSynthesisText] = useState("");
  const [lang, setLang] = useState<TopicLang>("tr");

  const [proposals, setProposals] = useState<TopicProposalsResponse | null>(null);
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
  const [skeleton, setSkeleton] = useState<DraftSkeletonResponse | null>(null);

  const [proposalsBusy, setProposalsBusy] = useState(false);
  const [skeletonBusy, setSkeletonBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const proposalsReady = axisX.length >= 1 && axisY.length >= 1;

  async function runProposals() {
    if (!projectId) return;
    setProposalsBusy(true);
    setError(null);
    setSkeleton(null);
    setSelectedIdx(null);
    try {
      const data = await apiFetch<TopicProposalsResponse>(
        "/api/workshop/topic-proposals",
        {
          method: "POST",
          body: {
            project_id: projectId,
            gap_matrix_id: matrixId,
            gap_axis_x: axisX,
            gap_axis_y: axisY,
            method_profile: methodProfile
              .split(",")
              .map((s) => s.trim())
              .filter(Boolean)
              .slice(0, 5),
            synthesis_text: synthesisText || null,
            lang,
          },
        },
      );
      setProposals(data);
    } catch (e: unknown) {
      const msg =
        e instanceof ApiError
          ? `Konu önerileri alınamadı (${e.status})`
          : "Konu önerileri alınamadı";
      setError(msg);
    } finally {
      setProposalsBusy(false);
    }
  }

  async function runSkeleton() {
    if (!projectId || selectedIdx === null || !proposals) return;
    const picked = proposals.proposals[selectedIdx];
    if (!picked) return;
    setSkeletonBusy(true);
    setError(null);
    try {
      const data = await apiFetch<DraftSkeletonResponse>(
        "/api/workshop/draft-skeleton",
        {
          method: "POST",
          body: {
            project_id: projectId,
            selected_topic: picked,
            method_metod_ids: [],
            sections: ["intro", "methods", "findings", "discussion"],
            lang,
          },
        },
      );
      setSkeleton(data);
    } catch (e: unknown) {
      const msg =
        e instanceof ApiError
          ? `İskelet oluşturulamadı (${e.status})`
          : "İskelet oluşturulamadı";
      setError(msg);
    } finally {
      setSkeletonBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <AdvisorBanner message="Boşluk haritasından 3 konu önerisi → IMRaD iskeleti. Eksen + yöntem + sentez doldur, geri kalanı LLM yapar." />

      {error && (
        <div className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Input form */}
      <div className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="font-display mb-3 text-base font-semibold text-stone-800">
          Gap girdileri
        </h3>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <label className="flex flex-col gap-1 text-xs text-stone-600">
            Gap matrix
            <select
              value={matrixId}
              onChange={(e) => setMatrixId(e.target.value as GapMatrixId)}
              className="rounded-lg border border-stone-300 bg-white px-2 py-1.5 text-sm"
            >
              <option value="M1">M1</option>
              <option value="M7">M7</option>
              <option value="M8">M8</option>
            </select>
          </label>
          <label className="flex flex-col gap-1 text-xs text-stone-600">
            Dil
            <select
              value={lang}
              onChange={(e) => setLang(e.target.value as TopicLang)}
              className="rounded-lg border border-stone-300 bg-white px-2 py-1.5 text-sm"
            >
              <option value="tr">Türkçe</option>
              <option value="en">English</option>
              <option value="id">Bahasa Indonesia</option>
            </select>
          </label>
          <label className="flex flex-col gap-1 text-xs text-stone-600">
            Eksen X
            <input
              value={axisX}
              onChange={(e) => setAxisX(e.target.value)}
              className="rounded-lg border border-stone-300 bg-white px-2 py-1.5 text-sm"
              placeholder="Örn: bulanık ortam"
            />
          </label>
          <label className="flex flex-col gap-1 text-xs text-stone-600">
            Eksen Y
            <input
              value={axisY}
              onChange={(e) => setAxisY(e.target.value)}
              className="rounded-lg border border-stone-300 bg-white px-2 py-1.5 text-sm"
              placeholder="Örn: TOPSIS"
            />
          </label>
        </div>
        <label className="mt-3 flex flex-col gap-1 text-xs text-stone-600">
          Yöntem profili (virgülle, max 5)
          <input
            value={methodProfile}
            onChange={(e) => setMethodProfile(e.target.value)}
            placeholder="TOPSIS, VIKOR, AHP"
            className="rounded-lg border border-stone-300 bg-white px-2 py-1.5 text-sm"
          />
        </label>
        <label className="mt-3 flex flex-col gap-1 text-xs text-stone-600">
          Sentez metni (opsiyonel)
          <textarea
            value={synthesisText}
            onChange={(e) => setSynthesisText(e.target.value)}
            placeholder="3.4 sentez çıktısı — şart değil."
            className="min-h-[80px] rounded-lg border border-stone-300 bg-white px-2 py-1.5 text-sm"
          />
        </label>
        <div className="mt-4">
          <button
            type="button"
            onClick={runProposals}
            disabled={!proposalsReady || proposalsBusy || !projectId}
            className="inline-flex items-center gap-2 rounded-lg bg-stone-800 px-4 py-2 text-sm font-medium text-white hover:bg-stone-900 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {proposalsBusy ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            3 konu öner
          </button>
        </div>
      </div>

      {proposals && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-display text-base font-semibold text-stone-800">
              Konu Önerileri
            </h3>
            <span className="text-xs text-stone-500">
              Üretim {proposals.generation_count} · kota {proposals.daily_quota_remaining}
            </span>
          </div>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            {proposals.proposals.map((p, idx) => {
              const isSel = selectedIdx === idx;
              return (
                <div
                  key={idx}
                  className={`rounded-2xl border-2 p-4 transition-all ${
                    isSel
                      ? "border-[#E8A157] bg-amber-50/40"
                      : "border-stone-200 bg-white hover:border-stone-300"
                  }`}
                >
                  <div className="mb-2 flex items-start justify-between gap-2">
                    <h4 className="font-display text-sm font-semibold text-stone-800">
                      {p.title}
                    </h4>
                    {isSel && (
                      <Check className="h-4 w-4 shrink-0 text-[#E8A157]" />
                    )}
                  </div>
                  <ul className="space-y-1 text-xs text-stone-600">
                    <li>
                      <strong>Temkinli:</strong> {p.sub_questions.cautious}
                    </li>
                    <li>
                      <strong>Dengeli:</strong> {p.sub_questions.balanced}
                    </li>
                    <li>
                      <strong>Cesur:</strong> {p.sub_questions.bold}
                    </li>
                  </ul>
                  <p className="mt-2 text-xs text-stone-500">
                    Yöntem: {p.method_suggestion}
                  </p>
                  {p.top_3_refs.length > 0 && (
                    <p className="mt-1 text-xs text-stone-400">
                      Ref: {p.top_3_refs.join(", ")}
                    </p>
                  )}
                  <button
                    type="button"
                    onClick={() => setSelectedIdx(idx)}
                    className={`mt-3 inline-flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium ${
                      isSel
                        ? "bg-stone-200 text-stone-500"
                        : "bg-stone-800 text-white hover:bg-stone-900"
                    }`}
                  >
                    {isSel ? "Seçildi" : "Bu konuyu seç"}
                  </button>
                </div>
              );
            })}
          </div>

          {selectedIdx !== null && (
            <button
              type="button"
              onClick={runSkeleton}
              disabled={skeletonBusy}
              className="inline-flex items-center gap-2 rounded-lg bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {skeletonBusy ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Layers className="h-4 w-4" />
              )}
              İskeleti oluştur
            </button>
          )}
        </div>
      )}

      {skeleton && (
        <div className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
          <h3 className="font-display mb-3 text-base font-semibold text-stone-800">
            IMRaD İskeleti
          </h3>
          <div className="space-y-4">
            {skeleton.sections.map((sec) => (
              <div
                key={sec.name}
                className="rounded-xl border border-stone-100 bg-stone-50/50 p-4"
              >
                <h4 className="font-display text-sm font-semibold text-stone-800">
                  {SECTION_LABELS[sec.name]}
                </h4>
                <p className="mt-2 whitespace-pre-wrap text-sm text-stone-700">
                  {sec.draft_paragraph}
                </p>
                <p className="mt-1 text-xs italic text-stone-500">
                  Neden: {sec.why_explanation}
                </p>
                {sec.top_5_papers.length > 0 && (
                  <ul className="mt-2 space-y-1 text-xs text-stone-600">
                    {sec.top_5_papers.map((paper) => (
                      <li key={paper.paper_id} className="flex items-center gap-1.5">
                        <ArrowRight className="h-3 w-3 text-stone-400" />
                        <span>
                          {paper.title} · {paper.authors_short}
                          {paper.year ? ` (${paper.year})` : ""} · {paper.citations_count} atıf
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
