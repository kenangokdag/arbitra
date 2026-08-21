"use client";

import { useCallback, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  GraduationCap,
  Play,
  Check,
  FileText,
  Download,
  Monitor,
  MessageCircle,
  Star,
  FolderPlus,
  ChevronLeft,
  ChevronRight,
  Loader2,
  AlertTriangle,
  Sparkles,
} from "lucide-react";
import { apiFetch, ApiError } from "@/lib/api";

// F13-S3.2 — defense-6 (S2 Proje Tamamlama) mezuniyet ekrani.
// 2 endpoint binding:
//   POST /api/completion/snapshot               → mezuniyet snapshot + LLM yorum
//   POST /api/feedback/project-completion       → 5-soru geri-bildirim
//
// KURAL (kullanici 2026-05-02): sayfa kendi arka planini koymaz; AppShell bg-stone-50 mirasi tek kaynak.

type StepStatus = "basarili" | "gelistirilmeli";

interface StepReview {
  step_id: string;
  label: string;
  status: StepStatus;
  score: number;
  comment: string;
}

interface CompletionBadges {
  basarili: number;
  gelistirilmeli: number;
}

interface CompletionSnapshot {
  step_reviews: StepReview[];
  badges: CompletionBadges;
  graduate_advice: string[];
  summary_paragraph: string;
}

interface SnapshotResponse {
  completion_id: string;
  project_id: string;
  completed_at: string;
  snapshot: CompletionSnapshot;
  delete_after: string;
}

interface FeedbackResponse {
  completion_id: string;
  project_id: string;
  feedback: {
    topic_suggestion_rating: number;
    process_rating: number;
    missing_features: string;
    overall_satisfaction: number;
    nps: number;
  };
  updated_at: string;
}

const OUTPUTS = [
  { icon: FileText, name: "Tez taslagi", meta: "PDF" },
  { icon: Download, name: "Bibliyografi", meta: "BibTeX · RIS" },
  { icon: Monitor, name: "Sunum", meta: "PPTX" },
  { icon: MessageCircle, name: "Soru bankasi", meta: "Cevap iskeleti" },
] as const;

const FALLBACK_NEXT_STEPS = [
  {
    icon: Star,
    title: "Makale yayinla",
    sub: "Tezinden bir makale cikarmana yardim edeyim — Yazim & Hazirlik tezgahindan devam edelim",
  },
  {
    icon: FolderPlus,
    title: "Yeni proje baslat",
    sub: "Doktora veya bir sonraki arastirma icin temiz bir tezgah ac",
  },
  {
    icon: Download,
    title: "Projenin arsivini indir",
    sub: "Tum sohbetler, notlar, kaynaklar ve ciktilar — tek dosya olarak (.zip)",
  },
] as const;

const FALLBACK_LETTER =
  "Bu yolun basinda, 504K hucrelik bosluk haritasina bakip “ben buralarda kaybolurum” demistin. Simdi o haritada kendi noktani koyuyorsun. Hazir oldugunu biliyorum.";

export function ProjectClosurePage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const projectId = params?.id;

  const [snapshot, setSnapshot] = useState<SnapshotResponse | null>(null);
  const [snapshotBusy, setSnapshotBusy] = useState(false);
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [feedbackBusy, setFeedbackBusy] = useState(false);
  const [feedbackSent, setFeedbackSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [topicRating, setTopicRating] = useState(5);
  const [processRating, setProcessRating] = useState(5);
  const [missing, setMissing] = useState("");
  const [satisfaction, setSatisfaction] = useState(5);
  const [nps, setNps] = useState(9);

  const generateSnapshot = useCallback(async () => {
    if (!projectId) return;
    setSnapshotBusy(true);
    setError(null);
    try {
      const data = await apiFetch<SnapshotResponse>("/api/completion/snapshot", {
        method: "POST",
        body: { project_id: projectId },
      });
      setSnapshot(data);
    } catch (e: unknown) {
      const msg =
        e instanceof ApiError
          ? `Snapshot olusturulamadi (${e.status})`
          : "Snapshot olusturulamadi";
      setError(msg);
    } finally {
      setSnapshotBusy(false);
    }
  }, [projectId]);

  async function submitFeedback() {
    if (!projectId) return;
    setFeedbackBusy(true);
    setError(null);
    try {
      await apiFetch<FeedbackResponse>("/api/feedback/project-completion", {
        method: "POST",
        body: {
          project_id: projectId,
          feedback: {
            topic_suggestion_rating: topicRating,
            process_rating: processRating,
            missing_features: missing,
            overall_satisfaction: satisfaction,
            nps,
          },
        },
      });
      setFeedbackSent(true);
      setFeedbackOpen(false);
    } catch (e: unknown) {
      const msg =
        e instanceof ApiError
          ? `Geri-bildirim gonderilemedi (${e.status})`
          : "Geri-bildirim gonderilemedi";
      setError(msg);
    } finally {
      setFeedbackBusy(false);
    }
  }

  const goBack = () => {
    if (projectId) router.push(`/project/${projectId}/defense-5`);
    else router.back();
  };
  const closeProject = () => router.push("/");

  const snap = snapshot?.snapshot ?? null;
  const stepRows = snap?.step_reviews ?? [];
  const badges = snap?.badges ?? null;
  const advice = snap?.graduate_advice ?? [];
  const summary = snap?.summary_paragraph ?? FALLBACK_LETTER;

  return (
    <div className="mx-auto flex max-w-[880px] flex-col gap-6 pb-20">
      <PmClosureStyles />

      {/* Mezuniyet header */}
      <header className="relative px-6 pt-9 pb-7 text-center">
        <Confetti />

        <div className="relative inline-flex">
          <div
            className="pmclosure-medal flex h-24 w-24 items-center justify-center rounded-full"
            style={{ background: "var(--color-ink)" }}
            aria-hidden="true"
          >
            <GraduationCap
              className="h-11 w-11"
              style={{ color: "var(--color-bg)" }}
              strokeWidth={2}
            />
          </div>
        </div>

        <div
          className="mt-4 font-mono uppercase"
          style={{ fontSize: 10.5, letterSpacing: "0.18em", color: "var(--color-ink-soft)" }}
        >
          — Tebrikler —
        </div>
        <h1
          className="font-display italic mx-auto mt-2 max-w-[600px]"
          style={{ fontSize: 38, fontWeight: 500, lineHeight: 1.1, color: "var(--color-ink)" }}
        >
          Tezini bitirdin.
        </h1>

        {!snapshot && (
          <button
            type="button"
            onClick={generateSnapshot}
            disabled={snapshotBusy || !projectId}
            className="mt-5 inline-flex items-center gap-2 rounded-lg bg-stone-800 px-4 py-2 text-sm font-medium text-white hover:bg-stone-900 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {snapshotBusy ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            Mezuniyet ozetini olustur
          </button>
        )}
      </header>

      {error && (
        <div className="mx-6 flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Danisman mektubu / LLM ozet */}
      <article
        className="relative rounded-xl px-6 py-5"
        style={{
          background: "var(--color-bg-card)",
          border: "1px solid var(--color-rule)",
          borderLeft: "3px solid var(--color-ink)",
        }}
      >
        <p
          className="font-display italic ml-7"
          style={{ fontSize: 16, lineHeight: 1.65, color: "var(--color-ink)" }}
        >
          {summary}
        </p>
        <div
          className="ml-7 mt-3 flex items-center gap-2.5"
          style={{ fontSize: 12.5, color: "var(--color-ink-faint)" }}
        >
          <span>— Danisman</span>
        </div>
      </article>

      {/* Badges */}
      {badges && (
        <section className="flex flex-col gap-3.5">
          <SectionLabel>Yolculugun rakamlarla</SectionLabel>
          <div className="grid grid-cols-2 gap-3">
            <StatCard
              icon={Check}
              value={String(badges.basarili)}
              label="Basarili adim"
              color="emerald"
            />
            <StatCard
              icon={Play}
              value={String(badges.gelistirilmeli)}
              label="Gelistirilmeli adim"
              color="amber"
            />
          </div>
        </section>
      )}

      {/* Step reviews — gercek data */}
      {stepRows.length > 0 && (
        <section className="flex flex-col gap-3.5">
          <SectionLabel>Tamamlanan adimlar</SectionLabel>
          <ul
            className="rounded-xl"
            style={{
              background: "var(--color-bg-card)",
              border: "1px solid var(--color-rule)",
            }}
          >
            {stepRows.map((sr, i) => (
              <li
                key={sr.step_id}
                className="grid items-start gap-3.5 px-5 py-3"
                style={{
                  gridTemplateColumns: "24px 1fr auto",
                  borderBottom:
                    i === stepRows.length - 1
                      ? "none"
                      : "1px solid var(--color-rule-soft)",
                }}
              >
                <span
                  className="mx-1.5 mt-1.5 h-2.5 w-2.5 flex-shrink-0 rounded-full"
                  style={{
                    background: sr.status === "basarili" ? "#10b981" : "#f59e0b",
                  }}
                />
                <div>
                  <div
                    className="font-display italic"
                    style={{ fontSize: 15, fontWeight: 500, color: "var(--color-ink)" }}
                  >
                    {sr.label}
                  </div>
                  <div
                    className="mt-1 text-xs"
                    style={{ color: "var(--color-ink-mute)" }}
                  >
                    {sr.comment}
                  </div>
                </div>
                <span
                  className="font-mono text-xs"
                  style={{ color: "var(--color-ink-faint)" }}
                >
                  %{Math.round(sr.score * 100)}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Outputs */}
      <section className="flex flex-col gap-3.5">
        <SectionLabel>Projenden goturecekleri</SectionLabel>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {OUTPUTS.map((o) => (
            <OutputCard key={o.name} {...o} />
          ))}
        </div>
      </section>

      {/* Next steps — graduate advice if any, else fallback */}
      <section className="flex flex-col gap-3.5">
        <SectionLabel>Bundan sonra</SectionLabel>
        <div className="flex flex-col gap-2.5">
          {advice.length > 0
            ? advice.map((a, i) => (
                <NextCard key={i} icon={Star} title={a} sub="" />
              ))
            : FALLBACK_NEXT_STEPS.map((n) => (
                <NextCard key={n.title} {...n} />
              ))}
        </div>
      </section>

      {/* Feedback */}
      <section className="flex flex-col gap-3.5">
        <SectionLabel>Geri bildirimin</SectionLabel>
        {feedbackSent ? (
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
            Tesekkurler — geri-bildirimin kaydedildi.
          </div>
        ) : feedbackOpen ? (
          <div
            className="rounded-xl p-4"
            style={{
              background: "var(--color-bg-card)",
              border: "1px solid var(--color-rule)",
            }}
          >
            <FeedbackField
              label="Konu onerisi puani (1-5)"
              value={topicRating}
              onChange={setTopicRating}
              min={1}
              max={5}
            />
            <FeedbackField
              label="Surec puani (1-5)"
              value={processRating}
              onChange={setProcessRating}
              min={1}
              max={5}
            />
            <FeedbackField
              label="Genel tatmin (1-5)"
              value={satisfaction}
              onChange={setSatisfaction}
              min={1}
              max={5}
            />
            <FeedbackField
              label="NPS (0-10)"
              value={nps}
              onChange={setNps}
              min={0}
              max={10}
            />
            <label
              className="mt-3 block text-xs font-medium"
              style={{ color: "var(--color-ink-mute)" }}
            >
              Eksik bulduklarin
              <textarea
                value={missing}
                onChange={(e) => setMissing(e.target.value)}
                className="mt-1 min-h-[80px] w-full rounded-lg border border-stone-300 bg-stone-50 p-2 text-sm"
              />
            </label>
            <div className="mt-3 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setFeedbackOpen(false)}
                className="rounded-lg border border-stone-300 bg-white px-3 py-1.5 text-xs font-medium text-stone-700"
              >
                Iptal
              </button>
              <button
                type="button"
                onClick={submitFeedback}
                disabled={feedbackBusy}
                className="inline-flex items-center gap-1 rounded-lg bg-stone-800 px-3 py-1.5 text-xs font-medium text-white hover:bg-stone-900 disabled:opacity-40"
              >
                {feedbackBusy && <Loader2 className="h-3 w-3 animate-spin" />}
                Gonder
              </button>
            </div>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setFeedbackOpen(true)}
            disabled={!projectId}
            className="self-start rounded-lg border border-stone-300 bg-white px-3 py-2 text-sm font-medium text-stone-700 hover:bg-stone-50 disabled:opacity-40"
          >
            Geri bildirim ver
          </button>
        )}
      </section>

      {/* Final actions */}
      <div className="mt-2 flex flex-col justify-center gap-2.5 sm:flex-row">
        <button
          type="button"
          onClick={goBack}
          className="inline-flex items-center justify-center gap-2 rounded-[11px] px-5 py-3"
          style={{
            background: "var(--color-bg-card)",
            border: "1px solid var(--color-rule)",
            color: "var(--color-ink-soft)",
            fontSize: 14,
            fontWeight: 500,
          }}
        >
          <ChevronLeft className="h-3.5 w-3.5" />
          5.5 Simulasyona don
        </button>
        <button
          type="button"
          onClick={closeProject}
          className="inline-flex items-center justify-center gap-2 rounded-[11px] px-5 py-3 hover:brightness-110"
          style={{
            background: "var(--color-ink)",
            color: "#fff",
            fontSize: 14,
            fontWeight: 500,
          }}
        >
          <Check className="h-3.5 w-3.5" />
          Projeyi kapat
        </button>
      </div>

      <div
        className="font-display italic mt-3 pt-4 text-center"
        style={{
          fontSize: 13,
          color: "var(--color-ink-faint)",
          borderTop: "1px dashed var(--color-rule)",
        }}
      >
        “Bilim, sabirla yapilir. Sen yaptin.”
      </div>
    </div>
  );
}

// ── Internal blocks ──────────────────────────────────────────────────────

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="font-mono uppercase"
      style={{
        fontSize: 10.5,
        letterSpacing: "0.1em",
        color: "var(--color-ink-faint)",
      }}
    >
      {children}
    </div>
  );
}

function StatCard({
  icon: Icon,
  value,
  label,
  color,
}: {
  icon: typeof Check;
  value: string;
  label: string;
  color: "emerald" | "amber";
}) {
  const bgClass = color === "emerald" ? "bg-emerald-50" : "bg-amber-50";
  const textClass = color === "emerald" ? "text-emerald-700" : "text-amber-700";
  return (
    <div
      className={`flex flex-col items-start gap-1.5 rounded-xl p-4 ${bgClass}`}
      style={{ border: "1px solid var(--color-rule)" }}
    >
      <Icon className={`h-5 w-5 ${textClass}`} strokeWidth={2} />
      <div
        className="font-display italic"
        style={{ fontSize: 28, fontWeight: 500, lineHeight: 1, color: "var(--color-ink)" }}
      >
        {value}
      </div>
      <div style={{ fontSize: 11.5, color: "var(--color-ink-mute)" }}>{label}</div>
    </div>
  );
}

function OutputCard({
  icon: Icon,
  name,
  meta,
}: {
  icon: typeof FileText;
  name: string;
  meta: string;
}) {
  return (
    <button
      type="button"
      className="flex w-full items-center gap-3.5 rounded-xl p-4 text-left"
      style={{
        background: "var(--color-bg-card)",
        border: "1px solid var(--color-rule)",
      }}
    >
      <span
        className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-[10px]"
        style={{
          background: "var(--color-bg-soft)",
          border: "1px solid var(--color-rule)",
          color: "var(--color-ink-soft)",
        }}
      >
        <Icon className="h-5 w-5" strokeWidth={2} />
      </span>
      <div className="min-w-0 flex-1">
        <div style={{ fontSize: 13.5, fontWeight: 600, color: "var(--color-ink)" }}>
          {name}
        </div>
        <div
          className="font-mono mt-0.5"
          style={{ fontSize: 11.5, color: "var(--color-ink-mute)" }}
        >
          {meta}
        </div>
      </div>
      <ChevronRight className="h-3.5 w-3.5 flex-shrink-0" />
    </button>
  );
}

function NextCard({
  icon: Icon,
  title,
  sub,
}: {
  icon: typeof Star;
  title: string;
  sub: string;
}) {
  return (
    <button
      type="button"
      className="flex w-full items-center gap-3.5 rounded-xl px-4 py-4 text-left"
      style={{
        background: "var(--color-bg-card)",
        border: "1px solid var(--color-rule)",
      }}
    >
      <span
        className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-[9px]"
        style={{
          background: "var(--color-bg-soft)",
          border: "1px solid var(--color-rule)",
          color: "var(--color-ink)",
        }}
      >
        <Icon className="h-4 w-4" strokeWidth={2} />
      </span>
      <div className="min-w-0 flex-1">
        <div style={{ fontSize: 13.5, fontWeight: 600, color: "var(--color-ink)" }}>
          {title}
        </div>
        {sub && (
          <div className="mt-0.5" style={{ fontSize: 12.5, color: "var(--color-ink-mute)" }}>
            {sub}
          </div>
        )}
      </div>
      <ChevronRight className="h-3.5 w-3.5 flex-shrink-0" />
    </button>
  );
}

function FeedbackField({
  label,
  value,
  onChange,
  min,
  max,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
}) {
  return (
    <label
      className="mt-3 block text-xs font-medium"
      style={{ color: "var(--color-ink-mute)" }}
    >
      {label}
      <input
        type="number"
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="ml-2 w-16 rounded-md border border-stone-300 bg-white px-2 py-1 text-sm text-stone-800"
      />
    </label>
  );
}

function Confetti() {
  const COLORS = ["#E8A157", "#0E4F4A", "#1F2937"];
  const POSITIONS = [8, 18, 28, 38, 50, 62, 72, 82, 92, 14, 44, 58];
  const DELAYS = [0, 0.7, 1.4, 2.1, 0.3, 1.0, 1.7, 2.4, 0.5, 1.2, 2.6, 1.8];
  return (
    <div className="pointer-events-none absolute inset-0" aria-hidden="true">
      {POSITIONS.map((left, i) => (
        <span
          key={i}
          className="pmclosure-confetti"
          style={{
            position: "absolute",
            left: `${left}%`,
            top: "-10%",
            width: 7,
            height: 11,
            borderRadius: 1,
            background: COLORS[i % 3],
            opacity: 0.85,
            animationDelay: `${DELAYS[i]}s`,
          }}
        />
      ))}
    </div>
  );
}

function PmClosureStyles() {
  return (
    <style>{`
      @keyframes pmclosure-medal-in {
        from { transform: scale(0.6) rotate(-14deg); opacity: 0; }
        to   { transform: scale(1) rotate(0); opacity: 1; }
      }
      @keyframes pmclosure-confetti-fall {
        0%   { transform: translateY(0) rotate(0); opacity: 0; }
        10%  { opacity: 0.85; }
        100% { transform: translateY(700px) rotate(720deg); opacity: 0; }
      }
      .pmclosure-medal {
        animation: pmclosure-medal-in 800ms cubic-bezier(.34,1.56,.64,1) both;
      }
      .pmclosure-confetti {
        animation: pmclosure-confetti-fall 4s linear infinite;
      }
      @media (prefers-reduced-motion: reduce) {
        .pmclosure-medal,
        .pmclosure-confetti {
          animation-duration: 0.01ms !important;
          animation-iteration-count: 1 !important;
        }
      }
    `}</style>
  );
}
