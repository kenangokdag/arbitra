"use client";

import { useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  GraduationCap,
  ScrollText,
  Mic2,
  Loader2,
  Users,
  Sparkles,
  AlertTriangle,
  X,
} from "lucide-react";
import { AdvisorBanner } from "@/components/project/AdvisorBanner";
import { apiFetch, ApiError } from "@/lib/api";
import { setDefenseSessionId } from "@/lib/defenseSession";

// F13-S2.2 — defense-1 (6.2 Savunma Formati) wizard + endpoint binding.
// Static 3-format UI korunur; alt bölümde 3 backend endpoint:
//   POST /api/workshop/defense/session          (upsert metadata)
//   GET  /api/workshop/defense/suggest-jury     (havuzdan yazar önerisi)
//   POST /api/workshop/defense/generate-questions (Gemini Pro 8-12 soru / üye)

type FormatId = "thesis" | "qualifying" | "conference";
type SessionType = "tez" | "yeterlilik" | "bildiri";

const FORMAT_TO_SESSION: Record<FormatId, SessionType> = {
  thesis: "tez",
  qualifying: "yeterlilik",
  conference: "bildiri",
};

const FORMAT_TO_JURY_SIZE: Record<FormatId, number> = {
  thesis: 5,
  qualifying: 3,
  conference: 1,
};

interface FoundPaper {
  paper_id: string;
  title: string;
  year: number | null;
  cited_by: number | null;
}

interface JuryMember {
  name: string;
  affiliation: string | null;
  field: string;
  orcid: string | null;
  openalex_author_id: string | null;
  found_papers: FoundPaper[];
  generic_fallback: boolean;
}

interface DefenseQuestion {
  jury_member_index: number;
  category: "method" | "contribution" | "limitation" | "ethics" | "field_specific";
  question: string;
  depth: number;
  source_paper_id: string | null;
  follow_up_questions: string[];
}

interface DefenseSessionResponse {
  id: string;
  project_id: string;
  session_type: SessionType;
  scheduled_date: string | null;
  jury_size: number;
  title: string;
  field: string;
  preferred_lang: "tr" | "en";
  jury_members: JuryMember[];
  question_pool: DefenseQuestion[];
}

interface JurySuggestion {
  name: string;
  affiliation: string | null;
  paper_count: number;
  total_citations: number;
  top_paper_ids: string[];
}

interface SuggestJuryResponse {
  project_id: string;
  field: string;
  suggestions: JurySuggestion[];
}

interface GenerateQuestionsResponse {
  session_id: string;
  jury_member_index: number;
  questions: DefenseQuestion[];
  total_pool_size: number;
}

interface TimelineRow {
  range: string;
  label: string;
  desc: string;
}

interface FormatConfig {
  title: string;
  duration: string;
  jury: string;
  language: string;
  timelineTitle: string;
  rows: TimelineRow[];
}

const FORMAT_CONFIG: Record<FormatId, FormatConfig> = {
  thesis: {
    title: "Tez Savunmasi",
    duration: "90 dakika",
    jury: "5 juri uyesi",
    language: "Turkce",
    timelineTitle: "Tez Savunmasi Akisi (90 dk)",
    rows: [
      { range: "0-5 dk", label: "Acilis & Tanitim", desc: "Juri baskani oturumu acar, adayi tanitir" },
      { range: "5-35 dk", label: "Sunum", desc: "30 dk tez sunumu (problem - yontem - bulgular - sonuc)" },
      { range: "35-75 dk", label: "Soru-Cevap", desc: "40 dk juri sorulari, savunma" },
      { range: "75-85 dk", label: "Muzakere", desc: "Juri kapali oturum degerlendirmesi" },
      { range: "85-90 dk", label: "Karar & Kapanis", desc: "Sonuc aciklamasi, oturum kapanisi" },
    ],
  },
  qualifying: {
    title: "Yeterlilik Sinavi",
    duration: "30 dakika",
    jury: "3 juri uyesi",
    language: "Turkce",
    timelineTitle: "Yeterlilik Sinavi Akisi (30 dk)",
    rows: [
      { range: "0-3 dk", label: "Acilis", desc: "Komite baskani oturumu acar" },
      { range: "3-13 dk", label: "Alan Sorulari", desc: "10 dk literatur hakimiyeti sorulari" },
      { range: "13-25 dk", label: "Proje Sunumu", desc: "12 dk doktora projesi sunumu + Q&A" },
      { range: "25-28 dk", label: "Muzakere", desc: "Komite degerlendirmesi" },
      { range: "28-30 dk", label: "Karar", desc: "Sonuc aciklamasi" },
    ],
  },
  conference: {
    title: "Konferans Bildirisi",
    duration: "20 dakika",
    jury: "Acik dinleyici",
    language: "Ingilizce",
    timelineTitle: "Konferans Bildirisi Akisi (20 dk)",
    rows: [
      { range: "0-1 dk", label: "Tanitim", desc: "Oturum baskani tanitimi" },
      { range: "1-16 dk", label: "Sunum", desc: "15 dk bildiri sunumu (slayt)" },
      { range: "16-19 dk", label: "Soru-Cevap", desc: "Dinleyici sorulari (3 dk)" },
      { range: "19-20 dk", label: "Kapanis", desc: "Oturum baskani tesekkuru" },
    ],
  },
};

const FORMAT_CARDS: { id: FormatId; title: string; icon: typeof ScrollText; sub: string; meta: string }[] = [
  { id: "thesis", title: "Tez Savunmasi", icon: ScrollText, sub: "Doktora veya yuksek lisans tezi", meta: "90 dk - 5 juri" },
  { id: "qualifying", title: "Yeterlilik Sinavi", icon: GraduationCap, sub: "Doktora yeterlilik komitesi", meta: "30 dk - 3 juri" },
  { id: "conference", title: "Konferans Bildirisi", icon: Mic2, sub: "Bilimsel toplanti sunumu", meta: "20 dk - acik" },
];

export function DefenseFormatPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const projectId = params?.id;

  const [selected, setSelected] = useState<FormatId>("thesis");
  const cfg = FORMAT_CONFIG[selected];

  const [title, setTitle] = useState<string>("");
  const [field, setField] = useState<string>("");
  const [scheduledDate, setScheduledDate] = useState<string>("");

  const [session, setSession] = useState<DefenseSessionResponse | null>(null);
  const [saving, setSaving] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [suggestions, setSuggestions] = useState<JurySuggestion[]>([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState<boolean>(false);

  const [generating, setGenerating] = useState<number | null>(null);

  const saveSession = useCallback(async () => {
    if (!projectId) {
      setError("Proje kimliği bulunamadı.");
      return;
    }
    if (!title.trim() || !field.trim()) {
      setError("Başlık ve alan zorunlu.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const body: Record<string, unknown> = {
        session_id: session?.id,
        project_id: projectId,
        session_type: FORMAT_TO_SESSION[selected],
        jury_size: FORMAT_TO_JURY_SIZE[selected],
        title: title.trim(),
        field: field.trim(),
        preferred_lang: selected === "conference" ? "en" : "tr",
        jury_members: session?.jury_members ?? [],
      };
      if (scheduledDate) body.scheduled_date = scheduledDate;
      const next = await apiFetch<DefenseSessionResponse>(
        "/api/workshop/defense/session",
        { method: "POST", body },
      );
      setSession(next);
      setDefenseSessionId(projectId, next.id);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Oturum kaydedilemedi.");
    } finally {
      setSaving(false);
    }
  }, [projectId, title, field, scheduledDate, selected, session]);

  const loadSuggestions = useCallback(async () => {
    if (!projectId || !field.trim()) {
      setError("Alan girilmeden öneri alınamaz.");
      return;
    }
    setLoadingSuggestions(true);
    setError(null);
    try {
      const resp = await apiFetch<SuggestJuryResponse>(
        `/api/workshop/defense/suggest-jury?project_id=${projectId}&field=${encodeURIComponent(field.trim())}`,
        { method: "GET" },
      );
      setSuggestions(resp.suggestions);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Jüri önerileri alınamadı.");
    } finally {
      setLoadingSuggestions(false);
    }
  }, [projectId, field]);

  const addMember = useCallback(
    async (s: JurySuggestion) => {
      if (!session) {
        setError("Önce oturumu kaydedin.");
        return;
      }
      const newMember: JuryMember = {
        name: s.name,
        affiliation: s.affiliation,
        field: session.field,
        orcid: null,
        openalex_author_id: null,
        found_papers: s.top_paper_ids.map((pid) => ({
          paper_id: pid,
          title: "",
          year: null,
          cited_by: null,
        })),
        generic_fallback: false,
      };
      setSaving(true);
      setError(null);
      try {
        const next = await apiFetch<DefenseSessionResponse>(
          "/api/workshop/defense/session",
          {
            method: "POST",
            body: {
              session_id: session.id,
              project_id: session.project_id,
              session_type: session.session_type,
              jury_size: session.jury_size,
              title: session.title,
              field: session.field,
              preferred_lang: session.preferred_lang,
              jury_members: [...session.jury_members, newMember],
            },
          },
        );
        setSession(next);
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "Üye eklenemedi.");
      } finally {
        setSaving(false);
      }
    },
    [session],
  );

  const removeMember = useCallback(
    async (idx: number) => {
      if (!session) return;
      setSaving(true);
      setError(null);
      try {
        const next = await apiFetch<DefenseSessionResponse>(
          "/api/workshop/defense/session",
          {
            method: "POST",
            body: {
              session_id: session.id,
              project_id: session.project_id,
              session_type: session.session_type,
              jury_size: session.jury_size,
              title: session.title,
              field: session.field,
              preferred_lang: session.preferred_lang,
              jury_members: session.jury_members.filter((_, i) => i !== idx),
            },
          },
        );
        setSession(next);
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "Üye silinemedi.");
      } finally {
        setSaving(false);
      }
    },
    [session],
  );

  const generateQuestions = useCallback(
    async (memberIdx: number) => {
      if (!session) return;
      setGenerating(memberIdx);
      setError(null);
      try {
        await apiFetch<GenerateQuestionsResponse>(
          "/api/workshop/defense/generate-questions",
          {
            method: "POST",
            body: { session_id: session.id, jury_member_index: memberIdx },
          },
        );
        // re-read session to refresh question_pool
        const refreshed = await apiFetch<DefenseSessionResponse>(
          "/api/workshop/defense/session",
          {
            method: "POST",
            body: {
              session_id: session.id,
              project_id: session.project_id,
              session_type: session.session_type,
              jury_size: session.jury_size,
              title: session.title,
              field: session.field,
              preferred_lang: session.preferred_lang,
              jury_members: session.jury_members,
            },
          },
        );
        setSession(refreshed);
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "Soru üretilemedi.");
      } finally {
        setGenerating(null);
      }
    },
    [session],
  );

  const goNext = () => {
    if (projectId) router.push(`/project/${projectId}/defense-2`);
  };
  const goBack = () => router.back();

  return (
    <div data-zone="defense" className="space-y-6">
      <header className="space-y-2">
        <div
          className="font-mono uppercase"
          style={{
            fontSize: 10,
            letterSpacing: "0.12em",
            color: "var(--color-ink-faint, #64748b)",
          }}
        >
          Savunma - 5.1
        </div>
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1">
            <h1 className="font-display italic" style={{ fontSize: 28, color: "var(--color-ink)", lineHeight: 1.2 }}>
              Savunmani planlayalim
            </h1>
            <p style={{ fontSize: 14.5, color: "var(--color-ink-mute)", lineHeight: 1.5 }}>
              Once formati secelim — surenden juri sayisina kadar her sey bundan sekillenir.
            </p>
          </div>
          <span
            className="font-mono whitespace-nowrap"
            style={{
              fontSize: 11,
              letterSpacing: "0.06em",
              color: "var(--color-accent)",
              background: "var(--color-accent-pale)",
              border: "1px solid var(--color-rule)",
              padding: "5px 10px",
              borderRadius: 999,
            }}
          >
            Adim 1/6
          </span>
        </div>
      </header>

      <AdvisorBanner
        zone="defense"
        message="Hangi sinava giriyorsun? Tez savunmasi mi, yeterlilik mi? Format degisince hazirlik da degisir."
      />

      <section
        aria-label="Savunma formati"
        className="grid grid-cols-1 gap-4 md:grid-cols-3"
      >
        {FORMAT_CARDS.map((card) => {
          const Icon = card.icon;
          const isSelected = selected === card.id;
          return (
            <button
              key={card.id}
              type="button"
              onClick={() => setSelected(card.id)}
              className="relative flex flex-col items-start gap-2 rounded-xl p-4 text-left transition-all"
              style={{
                background: isSelected ? "var(--color-accent-pale)" : "var(--color-bg-card)",
                border: isSelected ? "2px solid var(--color-accent)" : "1px solid var(--color-rule)",
                boxShadow: isSelected ? "0 1px 4px rgba(15,23,42,0.08)" : "none",
              }}
              aria-pressed={isSelected}
            >
              {isSelected && (
                <span
                  className="absolute right-3 top-3 flex items-center gap-1 rounded-full font-mono"
                  style={{
                    background: "var(--color-accent)",
                    color: "var(--color-accent-fg)",
                    padding: "2px 8px",
                    fontSize: 10,
                    letterSpacing: "0.05em",
                  }}
                >
                  <Check className="h-3 w-3" /> Secildi
                </span>
              )}
              <Icon
                className="h-7 w-7"
                style={{ color: isSelected ? "var(--color-accent)" : "var(--color-ink-mute)" }}
                strokeWidth={1.6}
              />
              <h3 className="font-display" style={{ fontSize: 17, color: "var(--color-ink)" }}>
                {card.title}
              </h3>
              <p style={{ fontSize: 13, color: "var(--color-ink-mute)", lineHeight: 1.45 }}>
                {card.sub}
              </p>
              <span
                className="font-mono"
                style={{
                  fontSize: 10.5,
                  letterSpacing: "0.04em",
                  color: "var(--color-ink-faint)",
                }}
              >
                {card.meta}
              </span>
            </button>
          );
        })}
      </section>

      <section
        aria-label="Detaylar"
        className="rounded-xl p-5"
        style={{
          background: "var(--color-bg-card)",
          border: "1px solid var(--color-rule)",
        }}
      >
        <h2
          className="font-display mb-4"
          style={{ fontSize: 17, color: "var(--color-ink)" }}
        >
          Detaylar
        </h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Field label="Tez/Sunum basligi">
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Orn. Bibliometric analysis of MCDM in finance"
              className="w-full rounded-md px-3 py-2 outline-none"
              style={{
                background: "var(--color-bg)",
                border: "1px solid var(--color-rule)",
                fontSize: 13.5,
                color: "var(--color-ink)",
              }}
            />
          </Field>
          <Field label="Alan / Anabilim dali">
            <input
              type="text"
              value={field}
              onChange={(e) => setField(e.target.value)}
              placeholder="Orn. Isletme / Yonetim Bilimi"
              className="w-full rounded-md px-3 py-2 outline-none"
              style={{
                background: "var(--color-bg)",
                border: "1px solid var(--color-rule)",
                fontSize: 13.5,
                color: "var(--color-ink)",
              }}
            />
          </Field>
          <Field label="Planlanan tarih">
            <input
              type="date"
              value={scheduledDate}
              onChange={(e) => setScheduledDate(e.target.value)}
              className="w-full rounded-md px-3 py-2 outline-none"
              style={{
                background: "var(--color-bg)",
                border: "1px solid var(--color-rule)",
                fontSize: 13.5,
                color: "var(--color-ink)",
              }}
            />
          </Field>
          <Field label="Toplam sure">
            <ReadOnly value={cfg.duration} />
          </Field>
          <Field label="Juri buyuklugu">
            <ReadOnly value={cfg.jury} />
          </Field>
          <Field label="Sunum dili">
            <ReadOnly value={cfg.language} />
          </Field>
        </div>
      </section>

      <section
        aria-label="Akis"
        className="rounded-xl p-5"
        style={{
          background: "var(--color-bg-card)",
          border: "1px solid var(--color-rule)",
        }}
      >
        <h2
          className="font-display mb-4"
          style={{ fontSize: 17, color: "var(--color-ink)" }}
        >
          {cfg.timelineTitle}
        </h2>
        <ol className="space-y-3">
          {cfg.rows.map((row, i) => (
            <li
              key={`${selected}-${i}`}
              className="flex items-start gap-4 rounded-lg p-3"
              style={{
                background: "var(--color-bg)",
                border: "1px solid var(--color-rule-soft)",
              }}
            >
              <span
                className="font-mono whitespace-nowrap rounded-md px-2 py-1"
                style={{
                  fontSize: 11,
                  letterSpacing: "0.04em",
                  color: "var(--color-accent)",
                  background: "var(--color-accent-pale)",
                  minWidth: 80,
                  textAlign: "center",
                }}
              >
                {row.range}
              </span>
              <div className="min-w-0 flex-1">
                <div
                  className="font-display"
                  style={{ fontSize: 14.5, color: "var(--color-ink)", marginBottom: 2 }}
                >
                  {row.label}
                </div>
                <div style={{ fontSize: 13, color: "var(--color-ink-mute)", lineHeight: 1.45 }}>
                  {row.desc}
                </div>
              </div>
            </li>
          ))}
        </ol>
      </section>

      {error && (
        <div className="flex items-start gap-3 rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-700">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <section
        aria-label="Oturum kaydi"
        className="flex flex-wrap items-center justify-between gap-3 rounded-xl p-4"
        style={{
          background: "var(--color-bg-card)",
          border: "1px solid var(--color-rule)",
        }}
      >
        <div className="flex flex-col gap-0.5">
          <span
            className="font-mono uppercase"
            style={{ fontSize: 10, letterSpacing: "0.1em", color: "var(--color-ink-faint)" }}
          >
            Oturum
          </span>
          <span style={{ fontSize: 13, color: "var(--color-ink-mute)" }}>
            {session
              ? `Kaydedildi · ${session.jury_members.length}/${session.jury_size} juri uyesi · ${session.question_pool.length} soru havuzu`
              : "Bilgileri girip oturumu kaydedin."}
          </span>
        </div>
        <button
          type="button"
          onClick={() => void saveSession()}
          disabled={saving || !title.trim() || !field.trim()}
          className="flex items-center gap-2 rounded-lg px-4 py-2 transition-all hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-50"
          style={{
            background: session ? "var(--color-bg)" : "var(--color-accent)",
            color: session ? "var(--color-ink)" : "var(--color-accent-fg)",
            border: session ? "1px solid var(--color-rule)" : "none",
            fontSize: 13.5,
          }}
        >
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
          {session ? "Guncelle" : "Oturumu Kaydet"}
        </button>
      </section>

      {session && (
        <section
          aria-label="Onerilen juri"
          className="rounded-xl p-5"
          style={{
            background: "var(--color-bg-card)",
            border: "1px solid var(--color-rule)",
          }}
        >
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-display" style={{ fontSize: 17, color: "var(--color-ink)" }}>
              Onerilen Juri (havuzdan)
            </h2>
            <button
              type="button"
              onClick={() => void loadSuggestions()}
              disabled={loadingSuggestions || !field.trim()}
              className="flex items-center gap-2 rounded-md px-3 py-1.5 transition-colors hover:brightness-105 disabled:opacity-50"
              style={{
                background: "var(--color-accent-pale)",
                color: "var(--color-accent)",
                border: "1px solid var(--color-rule)",
                fontSize: 12.5,
              }}
            >
              {loadingSuggestions ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Users className="h-3.5 w-3.5" />}
              {suggestions.length > 0 ? "Yenile" : "Oneri Al"}
            </button>
          </div>
          {suggestions.length === 0 ? (
            <p style={{ fontSize: 13, color: "var(--color-ink-mute)" }}>
              Alan bazli havuzdan jurinin en aktif 5 yazarini ceker.
            </p>
          ) : (
            <ul className="space-y-2">
              {suggestions.map((s) => (
                <li
                  key={s.name}
                  className="flex items-start justify-between gap-3 rounded-md p-3"
                  style={{
                    background: "var(--color-bg)",
                    border: "1px solid var(--color-rule-soft)",
                  }}
                >
                  <div className="min-w-0 flex-1">
                    <div className="font-display" style={{ fontSize: 14, color: "var(--color-ink)" }}>
                      {s.name}
                    </div>
                    <div style={{ fontSize: 12.5, color: "var(--color-ink-mute)" }}>
                      {s.affiliation ?? "Kurum bilinmiyor"} · {s.paper_count} paper · {s.total_citations} alinti
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => void addMember(s)}
                    disabled={saving}
                    className="rounded-md px-3 py-1 transition-colors hover:brightness-105 disabled:opacity-50"
                    style={{
                      background: "var(--color-accent-pale)",
                      color: "var(--color-accent)",
                      fontSize: 12,
                    }}
                  >
                    + Juriye ekle
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {session && session.jury_members.length > 0 && (
        <section
          aria-label="Juri uyeleri ve sorular"
          className="rounded-xl p-5"
          style={{
            background: "var(--color-bg-card)",
            border: "1px solid var(--color-rule)",
          }}
        >
          <h2 className="font-display mb-4" style={{ fontSize: 17, color: "var(--color-ink)" }}>
            Juri Uyeleri ve Soru Havuzu
          </h2>
          <ul className="space-y-3">
            {session.jury_members.map((m, i) => {
              const memberQuestions = session.question_pool.filter(
                (q) => q.jury_member_index === i,
              );
              return (
                <li
                  key={`${m.name}-${i}`}
                  className="rounded-lg p-4"
                  style={{
                    background: "var(--color-bg)",
                    border: "1px solid var(--color-rule-soft)",
                  }}
                >
                  <div className="mb-2 flex items-center justify-between gap-3">
                    <div>
                      <div className="font-display" style={{ fontSize: 14.5, color: "var(--color-ink)" }}>
                        {m.name}
                      </div>
                      <div style={{ fontSize: 12.5, color: "var(--color-ink-mute)" }}>
                        {m.field}
                        {m.found_papers.length > 0 ? ` · ${m.found_papers.length} paper` : ""}
                        {m.generic_fallback ? " · jenerik soru modu" : ""}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => void generateQuestions(i)}
                        disabled={generating !== null}
                        className="flex items-center gap-1 rounded-md px-3 py-1 transition-colors hover:brightness-105 disabled:opacity-50"
                        style={{
                          background: "var(--color-accent-pale)",
                          color: "var(--color-accent)",
                          fontSize: 12,
                        }}
                      >
                        {generating === i ? (
                          <Loader2 className="h-3 w-3 animate-spin" />
                        ) : (
                          <Sparkles className="h-3 w-3" />
                        )}
                        Soru uret
                      </button>
                      <button
                        type="button"
                        onClick={() => void removeMember(i)}
                        disabled={saving}
                        className="rounded-md p-1 transition-colors hover:bg-red-50 disabled:opacity-50"
                        aria-label="Uyeyi sil"
                      >
                        <X className="h-3.5 w-3.5 text-red-500" />
                      </button>
                    </div>
                  </div>
                  {memberQuestions.length > 0 && (
                    <ol className="ml-4 list-decimal space-y-1">
                      {memberQuestions.map((q, qi) => (
                        <li
                          key={qi}
                          style={{ fontSize: 13, color: "var(--color-ink-soft)", lineHeight: 1.4 }}
                        >
                          <span
                            className="font-mono mr-2"
                            style={{ fontSize: 10, color: "var(--color-ink-faint)" }}
                          >
                            [{q.category}]
                          </span>
                          {q.question}
                        </li>
                      ))}
                    </ol>
                  )}
                </li>
              );
            })}
          </ul>
        </section>
      )}

      <div className="flex items-center justify-between gap-3 pt-2">
        <button
          type="button"
          onClick={goBack}
          className="flex items-center gap-2 rounded-lg px-4 py-2 transition-colors"
          style={{
            border: "1px solid var(--color-rule)",
            background: "var(--color-bg-card)",
            color: "var(--color-ink-soft)",
            fontSize: 13.5,
          }}
        >
          <ArrowLeft className="h-4 w-4" />
          Geri
        </button>
        <button
          type="button"
          onClick={goNext}
          className="flex items-center gap-2 rounded-lg px-5 py-2.5 transition-all hover:brightness-105"
          style={{
            background: "var(--color-accent)",
            color: "var(--color-accent-fg)",
            fontSize: 14,
            boxShadow: "0 1px 3px rgba(15,23,42,0.1)",
          }}
        >
          Devam et — 5.2 Icerik Analizi
          <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span
        className="font-mono uppercase"
        style={{
          fontSize: 10,
          letterSpacing: "0.1em",
          color: "var(--color-ink-faint)",
        }}
      >
        {label}
      </span>
      {children}
    </label>
  );
}

function ReadOnly({ value }: { value: string }) {
  return (
    <div
      className="rounded-md px-3 py-2"
      style={{
        background: "var(--color-bg)",
        border: "1px solid var(--color-rule-soft)",
        fontSize: 13.5,
        color: "var(--color-ink-soft)",
      }}
    >
      {value}
    </div>
  );
}
