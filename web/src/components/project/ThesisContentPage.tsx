"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  AlertTriangle,
  CheckCircle2,
  FileText,
  Loader2,
  Sparkles,
  Wand2,
} from "lucide-react";
import { AdvisorBanner } from "@/components/project/AdvisorBanner";
import { apiFetch, ApiError } from "@/lib/api";

// F13-S3.1 — defense workflow giriş kapısı (6.1 Yayın İçeriği).
// 4 endpoint binding:
//   GET  /api/workshop/manuscript?project_id=
//   PUT  /api/workshop/manuscript/{section_type}
//   POST /api/workshop/manuscript/quality-check
//   POST /api/workshop/manuscript/auto-draft

type SectionType = "intro" | "methods" | "findings" | "discussion" | "conclusion";
type QualityFlag = "ok" | "sahte";

interface ManuscriptSection {
  section_type: SectionType;
  content: string;
  word_count: number;
  ai_quality_flag: QualityFlag | null;
  ai_quality_reason: string | null;
  updated_at: string;
}

interface GateStatus {
  filled_count: number;
  gate_open: boolean;
  quality_blocked: boolean;
}

interface ManuscriptResponse {
  project_id: string;
  sections: ManuscriptSection[];
  gate_status: GateStatus;
}

interface QualityCheckResponse {
  section_type: SectionType;
  flag: QualityFlag;
  reason: string;
  cache_hit: boolean;
}

interface AutoDraftResponse {
  section_type: SectionType;
  draft_content: string;
  source_steps: string[];
}

const SECTION_ORDER: SectionType[] = [
  "intro",
  "methods",
  "findings",
  "discussion",
  "conclusion",
];

const SECTION_LABELS: Record<SectionType, string> = {
  intro: "Giriş",
  methods: "Yöntem",
  findings: "Bulgular",
  discussion: "Tartışma",
  conclusion: "Sonuç",
};

function emptySection(t: SectionType): ManuscriptSection {
  return {
    section_type: t,
    content: "",
    word_count: 0,
    ai_quality_flag: null,
    ai_quality_reason: null,
    updated_at: "",
  };
}

export function ThesisContentPage() {
  const params = useParams<{ id: string }>();
  const projectId = params?.id;

  const [sections, setSections] = useState<Record<SectionType, ManuscriptSection> | null>(
    null,
  );
  const [gate, setGate] = useState<GateStatus | null>(null);
  const [drafts, setDrafts] = useState<Record<SectionType, string>>({
    intro: "",
    methods: "",
    findings: "",
    discussion: "",
    conclusion: "",
  });
  const [savingSection, setSavingSection] = useState<SectionType | null>(null);
  const [qualityBusy, setQualityBusy] = useState<SectionType | null>(null);
  const [draftBusy, setDraftBusy] = useState<SectionType | null>(null);
  const [autoDraftPreview, setAutoDraftPreview] = useState<AutoDraftResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const loadingManuscript = sections === null && error === null;

  useEffect(() => {
    if (!projectId) return;
    const ctrl = new AbortController();
    apiFetch<ManuscriptResponse>(
      `/api/workshop/manuscript?project_id=${encodeURIComponent(projectId)}`,
      { method: "GET", signal: ctrl.signal },
    )
      .then((data) => {
        const map: Record<SectionType, ManuscriptSection> = {
          intro: emptySection("intro"),
          methods: emptySection("methods"),
          findings: emptySection("findings"),
          discussion: emptySection("discussion"),
          conclusion: emptySection("conclusion"),
        };
        const nextDrafts: Record<SectionType, string> = {
          intro: "",
          methods: "",
          findings: "",
          discussion: "",
          conclusion: "",
        };
        for (const s of data.sections) {
          map[s.section_type] = s;
          nextDrafts[s.section_type] = s.content;
        }
        setSections(map);
        setDrafts(nextDrafts);
        setGate(data.gate_status);
        setError(null);
      })
      .catch((e: unknown) => {
        if ((e as { name?: string })?.name === "AbortError") return;
        const msg =
          e instanceof ApiError ? `Manuscript yüklenemedi (${e.status})` : "Manuscript yüklenemedi";
        setError(msg);
      });
    return () => ctrl.abort();
  }, [projectId]);

  const refetch = useCallback(async () => {
    if (!projectId) return;
    try {
      const data = await apiFetch<ManuscriptResponse>(
        `/api/workshop/manuscript?project_id=${encodeURIComponent(projectId)}`,
        { method: "GET" },
      );
      const map: Record<SectionType, ManuscriptSection> = {
        intro: emptySection("intro"),
        methods: emptySection("methods"),
        findings: emptySection("findings"),
        discussion: emptySection("discussion"),
        conclusion: emptySection("conclusion"),
      };
      for (const s of data.sections) map[s.section_type] = s;
      setSections(map);
      setGate(data.gate_status);
    } catch (e: unknown) {
      const msg =
        e instanceof ApiError ? `Yenileme başarısız (${e.status})` : "Yenileme başarısız";
      setError(msg);
    }
  }, [projectId]);

  async function saveSection(t: SectionType) {
    if (!projectId) return;
    setSavingSection(t);
    setError(null);
    try {
      await apiFetch<ManuscriptSection>(`/api/workshop/manuscript/${t}`, {
        method: "PUT",
        body: { project_id: projectId, content: drafts[t] },
      });
      await refetch();
    } catch (e: unknown) {
      const msg =
        e instanceof ApiError ? `Kayıt başarısız (${e.status})` : "Kayıt başarısız";
      setError(msg);
    } finally {
      setSavingSection(null);
    }
  }

  async function runQualityCheck(t: SectionType) {
    if (!projectId) return;
    setQualityBusy(t);
    setError(null);
    try {
      await apiFetch<QualityCheckResponse>("/api/workshop/manuscript/quality-check", {
        method: "POST",
        body: { project_id: projectId, section_type: t },
      });
      await refetch();
    } catch (e: unknown) {
      const msg =
        e instanceof ApiError
          ? `Kalite kontrolü başarısız (${e.status})`
          : "Kalite kontrolü başarısız";
      setError(msg);
    } finally {
      setQualityBusy(null);
    }
  }

  async function runAutoDraft(t: SectionType) {
    if (!projectId) return;
    setDraftBusy(t);
    setError(null);
    try {
      const data = await apiFetch<AutoDraftResponse>("/api/workshop/manuscript/auto-draft", {
        method: "POST",
        body: { project_id: projectId, section_type: t },
      });
      setAutoDraftPreview(data);
    } catch (e: unknown) {
      const msg =
        e instanceof ApiError ? `Taslak çıkarılamadı (${e.status})` : "Taslak çıkarılamadı";
      setError(msg);
    } finally {
      setDraftBusy(null);
    }
  }

  function acceptDraft() {
    if (!autoDraftPreview) return;
    setDrafts((d) => ({
      ...d,
      [autoDraftPreview.section_type]: autoDraftPreview.draft_content,
    }));
    setAutoDraftPreview(null);
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <AdvisorBanner message="6.1 Yayın İçeriği — 5 bölümünü doldur, kalite kontrolünü çalıştır; 3+ bölüm × 50 kelime × sahte değil → 6.2 kapısı açılır." />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-semibold text-stone-800">
            6.1 Yayın İçeriği
          </h1>
          <p className="mt-1 text-sm text-stone-500">
            Giriş · Yöntem · Bulgular · Tartışma · Sonuç — her bölüm en az 50 kelime.
          </p>
        </div>
        <FileText className="h-8 w-8 text-stone-300" />
      </div>

      {error && (
        <div className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {gate && (
        <div
          className={`rounded-xl border p-4 ${
            gate.gate_open
              ? "border-emerald-200 bg-emerald-50"
              : gate.quality_blocked
              ? "border-amber-200 bg-amber-50"
              : "border-stone-200 bg-stone-50"
          }`}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm">
              {gate.gate_open ? (
                <CheckCircle2 className="h-5 w-5 text-emerald-600" />
              ) : (
                <AlertTriangle className="h-5 w-5 text-stone-500" />
              )}
              <span className="font-medium text-stone-800">
                Doluluk: {gate.filled_count}/5 bölüm
              </span>
            </div>
            <span
              className={`rounded-full px-3 py-1 text-xs font-medium ${
                gate.gate_open
                  ? "bg-emerald-100 text-emerald-800"
                  : gate.quality_blocked
                  ? "bg-amber-100 text-amber-800"
                  : "bg-stone-200 text-stone-700"
              }`}
            >
              {gate.gate_open
                ? "6.2 Savunma kapısı açık"
                : gate.quality_blocked
                ? "Kalite engeli — sahte bölüm var"
                : "Kapı kapalı"}
            </span>
          </div>
        </div>
      )}

      {loadingManuscript && (
        <div className="flex items-center gap-2 rounded-xl border border-stone-200 bg-white p-4 text-sm text-stone-500">
          <Loader2 className="h-4 w-4 animate-spin" />
          Manuscript yükleniyor…
        </div>
      )}

      {sections && (
        <div className="space-y-4">
          {SECTION_ORDER.map((t) => {
            const s = sections[t];
            const draftVal = drafts[t];
            const dirty = draftVal !== s.content;
            const flagChip =
              s.ai_quality_flag === "ok" ? (
                <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-800">
                  Kalite: ok
                </span>
              ) : s.ai_quality_flag === "sahte" ? (
                <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800">
                  Kalite: sahte
                </span>
              ) : (
                <span className="rounded-full bg-stone-100 px-2 py-0.5 text-xs font-medium text-stone-600">
                  Kalite: değerlendirilmedi
                </span>
              );

            return (
              <div
                key={t}
                className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm"
              >
                <div className="mb-3 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <h3 className="font-display text-base font-semibold text-stone-800">
                      {SECTION_LABELS[t]}
                    </h3>
                    <span className="text-xs text-stone-500">
                      {s.word_count} kelime
                    </span>
                    {flagChip}
                  </div>
                </div>

                <textarea
                  value={draftVal}
                  onChange={(e) =>
                    setDrafts((d) => ({ ...d, [t]: e.target.value }))
                  }
                  placeholder={`${SECTION_LABELS[t]} bölümü…`}
                  className="min-h-[140px] w-full rounded-xl border border-stone-200 bg-stone-50 p-3 text-sm text-stone-800 focus:border-stone-400 focus:outline-none"
                  aria-label={`${SECTION_LABELS[t]} içerik`}
                />

                {s.ai_quality_flag === "sahte" && s.ai_quality_reason && (
                  <p className="mt-2 text-xs text-red-700">
                    Sebep: {s.ai_quality_reason}
                  </p>
                )}

                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => saveSection(t)}
                    disabled={!dirty || savingSection === t || !projectId}
                    className="inline-flex items-center gap-1 rounded-lg bg-stone-800 px-3 py-1.5 text-xs font-medium text-white hover:bg-stone-900 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    {savingSection === t && <Loader2 className="h-3 w-3 animate-spin" />}
                    Kaydet
                  </button>
                  <button
                    type="button"
                    onClick={() => runQualityCheck(t)}
                    disabled={qualityBusy === t || s.word_count < 10 || !projectId}
                    className="inline-flex items-center gap-1 rounded-lg border border-stone-300 bg-white px-3 py-1.5 text-xs font-medium text-stone-700 hover:bg-stone-50 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    {qualityBusy === t ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      <Sparkles className="h-3 w-3" />
                    )}
                    Kalite kontrolü
                  </button>
                  <button
                    type="button"
                    onClick={() => runAutoDraft(t)}
                    disabled={draftBusy === t || !projectId}
                    className="inline-flex items-center gap-1 rounded-lg border border-stone-300 bg-white px-3 py-1.5 text-xs font-medium text-stone-700 hover:bg-stone-50 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    {draftBusy === t ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      <Wand2 className="h-3 w-3" />
                    )}
                    Taslak çıkar
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {autoDraftPreview && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-stone-900/40 p-4">
          <div className="max-h-[80vh] w-full max-w-2xl overflow-auto rounded-2xl border border-stone-200 bg-white p-6 shadow-xl">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="font-display text-lg font-semibold text-stone-800">
                Otomatik taslak — {SECTION_LABELS[autoDraftPreview.section_type]}
              </h3>
              <button
                type="button"
                onClick={() => setAutoDraftPreview(null)}
                className="text-xs text-stone-500 hover:text-stone-800"
                aria-label="Kapat"
              >
                Kapat
              </button>
            </div>
            <p className="whitespace-pre-wrap text-sm text-stone-800">
              {autoDraftPreview.draft_content}
            </p>
            {autoDraftPreview.source_steps.length > 0 && (
              <p className="mt-3 text-xs text-stone-500">
                Kaynak adımlar: {autoDraftPreview.source_steps.join(", ")}
              </p>
            )}
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setAutoDraftPreview(null)}
                className="rounded-lg border border-stone-300 bg-white px-3 py-1.5 text-xs font-medium text-stone-700"
              >
                İptal
              </button>
              <button
                type="button"
                onClick={acceptDraft}
                className="rounded-lg bg-stone-800 px-3 py-1.5 text-xs font-medium text-white hover:bg-stone-900"
              >
                Editöre yapıştır
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
