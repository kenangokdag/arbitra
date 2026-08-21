// kaynak: docs/plans/V1_S10_vitrin_tek_sayfa.md §2 (UX) + §3 (KD-V1-S10-01..07)
// V1-S10-03: 25 makale + checkbox seçim (anon=3, authed=25) + "Literatür Özeti Üret".
// V1-S10-05: ReviewPanel single-content (akademik literatür inceleme bölümü).
// V1-S10-06 (KD-V1-S10-07): liste üstü filtreler (yıl/min atıf/abstract/sıralama) +
// Tümünü Seç (indeterminate, clamp) + görünen sayaç.

"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion, AnimatePresence, useReducedMotion } from "motion/react";
import {
  Search,
  ArrowRight,
  Loader2,
  BookOpen,
  FolderPlus,
  Mic,
  MicOff,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

import { useQ } from "@/hooks/useQ";
import { useNavigation } from "@/lib/navigation-context";
import { useLitReview } from "@/hooks/useLitReview";
import { useSpeechInput } from "@/hooks/useSpeechInput";
import { useTierMock } from "@/hooks/useTierMock";
import { AudioPlayButton } from "@/components/AudioPlayButton";
import { apiFetch, ApiError } from "@/lib/api";
import type { QLang } from "@/lib/q-api";
import type { LiteratureReviewApi } from "@/lib/lit-review-api";

// F11 Phase A — POST /api/project/from-q response (api/models/project.py)
type ProjectFromQResponse = {
  project_id: string;
  seed_query: string;
  seed_paper_count: number;
};
import {
  DEFAULT_LOCAL_FILTERS,
  applyLocalFilters,
  selectAllClamped,
  isAllVisibleSelected,
  type LocalFilters,
  type SortMode,
} from "@/lib/q-filters";
import type { PaperPreviewApi, QueryTranslationApi } from "@/lib/q-api";

const VITRIN = "#0e7490";
const VITRIN_PALE = "#ecfeff";

const ANON_PAPER_LIMIT = 3; // KD-V1-S10-02
const AUTHED_PAPER_LIMIT = 25;

function parseYear(input: string): number | undefined {
  const trimmed = input.trim();
  if (!trimmed) return undefined;
  const n = Number(trimmed);
  if (!Number.isFinite(n)) return undefined;
  if (n < 1900 || n > 2100) return undefined;
  return Math.floor(n);
}

export default function QPage() {
  const router = useRouter();
  const sp = useSearchParams();
  const initial = (sp.get("q") ?? "").trim();

  const [query, setQuery] = useState(initial);
  const [submitted, setSubmitted] = useState(initial);
  // Yıl form-state vs submit-state ayrı: Ara butonuna basınca backend query yenilenir.
  const [yearFromInput, setYearFromInput] = useState("");
  const [yearToInput, setYearToInput] = useState("");
  const [submittedYearFrom, setSubmittedYearFrom] = useState<
    number | undefined
  >(undefined);
  const [submittedYearTo, setSubmittedYearTo] = useState<number | undefined>(
    undefined,
  );
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [localFilters, setLocalFilters] = useState<LocalFilters>(
    DEFAULT_LOCAL_FILTERS,
  );
  // F11 Phase A: "Projeye Dönüştür" akışı state machine
  const [isConverting, setIsConverting] = useState(false);
  const [convertError, setConvertError] = useState<string | null>(null);
  // V1-S15 P001: review hazırken kaynaklar (search+filter+25 paper) collapse
  // edilir → kullanıcı doğrudan özeti görür, isterse "Düzenle" ile açar.
  const [sourcesOpen, setSourcesOpen] = useState(true);
  const reduceMotion = useReducedMotion();

  const { tier, isAuthenticated } = useTierMock();
  const { enterProject } = useNavigation();
  const maxSelect = isAuthenticated ? AUTHED_PAPER_LIMIT : ANON_PAPER_LIMIT;

  // V1-S12-02: Web Speech API sesli giriş (TR-only V1)
  const speech = useSpeechInput({
    lang: "tr-TR",
    onResult: (transcript) => {
      setQuery(transcript);
      runSearch(transcript);
    },
  });

  const qQuery = useQ({
    query: submitted,
    lang: "tr",
    yearFrom: submittedYearFrom,
    yearTo: submittedYearTo,
    enabled: submitted.length >= 2,
  });
  const litReview = useLitReview();

  const reviewData: LiteratureReviewApi | undefined =
    litReview.data?.review;

  // Review geldiğinde kaynak panelini otomatik kapat (Omer talebi 2026-05-10).
  useEffect(() => {
    if (reviewData) setSourcesOpen(false);
  }, [reviewData]);

  const allPapers: PaperPreviewApi[] = qQuery.data?.papers ?? [];
  const visiblePapers = useMemo(
    () => applyLocalFilters(allPapers, localFilters),
    [allPapers, localFilters],
  );
  const allSelected = isAllVisibleSelected(visiblePapers, selected, maxSelect);
  const someSelected = selected.size > 0 && !allSelected;

  function runSearch(q: string) {
    if (!q.trim()) return;
    const yf = parseYear(yearFromInput);
    const yt = parseYear(yearToInput);
    setSubmitted(q.trim());
    setSubmittedYearFrom(yf);
    setSubmittedYearTo(yt);
    setSelected(new Set());
    litReview.reset();
    router.replace(`/q?q=${encodeURIComponent(q.trim())}`);
  }

  function toggleSelect(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else if (next.size < maxSelect) {
        next.add(id);
      }
      return next;
    });
  }

  function toggleSelectAll() {
    if (allSelected) {
      setSelected(new Set());
    } else {
      setSelected(selectAllClamped(visiblePapers, maxSelect));
    }
  }

  function generateReview() {
    if (selected.size === 0 || litReview.isPending) return;
    litReview.mutate({
      paperIds: Array.from(selected),
      lang: "tr",
    });
  }

  // F11 Phase A: Q → Project köprüsü.
  // Q sorgusu + seçili paper'lar backend'e gönderilir; dönen project_id ile
  // discovery-1 (ResearchAreaConfirmPage)'a geçilir. enterProject zaten
  // /project/{id}/discovery-1 route'una gidiyor (navigation-context F10-F6).
  async function convertToProject() {
    if (selected.size === 0 || isConverting) return;
    setIsConverting(true);
    setConvertError(null);
    try {
      const lang: QLang = "tr";
      const res = await apiFetch<ProjectFromQResponse>(
        "/api/project/from-q",
        {
          method: "POST",
          body: {
            q_query: submitted,
            q_lang: lang,
            selected_paper_ids: Array.from(selected),
          },
        },
      );
      enterProject(res.project_id);
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? `Proje oluşturulamadı (${err.status})`
          : err instanceof Error
            ? err.message
            : "Proje oluşturulamadı";
      setConvertError(msg);
      setIsConverting(false);
    }
  }

  const tierBadge = useMemo(
    () =>
      isAuthenticated
        ? `${tier} · ${AUTHED_PAPER_LIMIT} makale seçebilirsin`
        : `anon · max ${ANON_PAPER_LIMIT} makale (giriş yap → ${AUTHED_PAPER_LIMIT})`,
    [tier, isAuthenticated],
  );

  return (
    <div className="flex flex-col gap-5">
      {/* Tier + breadcrumb */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-stone-100 pb-3">
        <div className="flex items-center gap-2 text-[12px]">
          <span
            className="rounded-md px-2 py-0.5 font-mono-pmid text-[10.5px] font-medium uppercase tracking-[0.08em]"
            style={{ background: VITRIN_PALE, color: VITRIN }}
          >
            Vitrin · Q
          </span>
          <span className="text-stone-400">›</span>
          <span className="font-display text-[14px] text-stone-700">
            Hızlı İnceleme
          </span>
        </div>
        <span
          data-testid="tier-badge"
          className="rounded-full border px-2.5 py-0.5 font-mono-pmid text-[10.5px] uppercase tracking-[0.08em] text-stone-500"
          style={{ borderColor: "var(--color-rule, #e7e5e4)" }}
        >
          {tierBadge}
        </span>
      </div>

      {/* V1-S15 P001: Kompakt özet — review geldiğinde kaynak paneli gizlenir,
          kullanıcı doğrudan özeti görür. Tıklanırsa kaynaklar tekrar açılır. */}
      {reviewData && !sourcesOpen ? (
        <button
          type="button"
          onClick={() => setSourcesOpen(true)}
          data-testid="sources-toggle-open"
          className="flex items-center justify-between gap-3 rounded-xl border bg-white px-4 py-3 text-left transition hover:border-stone-300"
          style={{ borderColor: "var(--color-rule, #e7e5e4)" }}
        >
          <span className="flex min-w-0 items-center gap-2.5">
            <BookOpen
              className="h-4 w-4 flex-shrink-0 text-stone-400"
              aria-hidden
            />
            <span className="min-w-0 truncate font-display text-[13.5px] text-stone-800">
              &ldquo;{submitted.slice(0, 60)}
              {submitted.length > 60 ? "…" : ""}&rdquo;
            </span>
            <span className="hidden flex-shrink-0 font-mono-pmid text-[10.5px] uppercase tracking-[0.08em] text-stone-500 sm:inline">
              · {selected.size} kaynak
            </span>
          </span>
          <span className="flex flex-shrink-0 items-center gap-1 font-sans text-[12px] font-medium text-stone-600">
            Kaynakları düzenle
            <ChevronDown className="h-3.5 w-3.5" aria-hidden />
          </span>
        </button>
      ) : null}

      {/* Kaynak bölümü (hero + search + arama sonuçları) — collapsible.
          reviewData yoksa veya sourcesOpen=true ise görünür. */}
      <AnimatePresence initial={false}>
        {!reviewData || sourcesOpen ? (
          <motion.section
            key="sources"
            initial={reduceMotion ? false : { height: 0, opacity: 0 }}
            animate={
              reduceMotion ? { opacity: 1 } : { height: "auto", opacity: 1 }
            }
            exit={reduceMotion ? { opacity: 0 } : { height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
            style={{ overflow: "hidden" }}
            className="flex flex-col gap-5"
          >
            {reviewData && sourcesOpen ? (
              <button
                type="button"
                onClick={() => setSourcesOpen(false)}
                data-testid="sources-toggle-close"
                className="self-start inline-flex items-center gap-1 font-sans text-[12px] text-stone-500 transition hover:text-stone-800"
              >
                <ChevronUp className="h-3.5 w-3.5" aria-hidden />
                Kaynakları kapat
              </button>
            ) : null}

            {/* Hero */}
            <header className="flex flex-col gap-1.5">
              <h1 className="font-display text-[28px] leading-tight tracking-tight text-stone-900">
                Konunu yaz, makaleleri seç,{" "}
                <span className="font-crimson italic">literatür özetini al</span>.
              </h1>
              <p
                className="font-crimson text-[15px] italic text-stone-500"
                style={{ maxWidth: "62ch" }}
              >
                OpenAlex&apos;ten 25 makale alaka sırasıyla gelir. İncelemek
                istediklerini işaretle, akademik makale formatında özet üretelim.
                Hesap gerekmez.
              </p>
            </header>

      {/* Search + yıl filtresi (backend) */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          runSearch(query);
        }}
        className="flex flex-col gap-2.5"
      >
        <div
          className="flex items-center gap-2 rounded-xl border bg-white px-3.5 py-2.5 transition focus-within:border-stone-900"
          style={{ borderColor: "var(--color-rule, #e7e5e4)" }}
        >
          <Search className="h-4 w-4 text-stone-400" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Anahtar kelime, araştırma sorusu, abstract ya da DOI…"
            className="flex-1 bg-transparent font-display text-[15.5px] leading-tight text-stone-900 outline-none placeholder:text-stone-400"
          />
          {speech.isSupported ? (
            <button
              type="button"
              onClick={() =>
                speech.isListening ? speech.stop() : speech.start()
              }
              data-testid="mic-button"
              aria-label={
                speech.isListening
                  ? "Mikrofonu durdur"
                  : "Sesli arama yap (TR)"
              }
              title={
                speech.isListening
                  ? "Dinleniyor… (durdurmak için tıkla)"
                  : "Sesli ara"
              }
              className="inline-flex h-9 w-9 items-center justify-center rounded-lg border transition"
              style={{
                borderColor: speech.isListening
                  ? "#dc2626"
                  : "var(--color-rule, #e7e5e4)",
                background: speech.isListening ? "#fef2f2" : "transparent",
                color: speech.isListening ? "#dc2626" : "#57534e",
              }}
            >
              {speech.isListening ? (
                <MicOff className="h-4 w-4 animate-pulse" />
              ) : (
                <Mic className="h-4 w-4" />
              )}
            </button>
          ) : null}
          <button
            type="submit"
            disabled={!query.trim()}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg px-3.5 font-sans text-[12.5px] font-medium text-white transition disabled:cursor-not-allowed disabled:opacity-50"
            style={{ background: VITRIN }}
          >
            Ara <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>
        <div className="flex flex-wrap items-center gap-2 px-1 font-mono-pmid text-[11px] uppercase tracking-[0.08em] text-stone-500">
          <span>Yıl:</span>
          <input
            type="number"
            inputMode="numeric"
            min={1900}
            max={2100}
            placeholder="den"
            value={yearFromInput}
            onChange={(e) => setYearFromInput(e.target.value)}
            data-testid="year-from"
            className="h-7 w-20 rounded-md border bg-white px-2 font-sans text-[12px] normal-case tracking-normal text-stone-800 outline-none focus:border-stone-900"
            style={{ borderColor: "var(--color-rule, #e7e5e4)" }}
          />
          <span className="text-stone-400">–</span>
          <input
            type="number"
            inputMode="numeric"
            min={1900}
            max={2100}
            placeholder="ya"
            value={yearToInput}
            onChange={(e) => setYearToInput(e.target.value)}
            data-testid="year-to"
            className="h-7 w-20 rounded-md border bg-white px-2 font-sans text-[12px] normal-case tracking-normal text-stone-800 outline-none focus:border-stone-900"
            style={{ borderColor: "var(--color-rule, #e7e5e4)" }}
          />
          <span className="text-stone-400 normal-case tracking-normal">
            (Ara butonu yeni sorgu çalıştırır)
          </span>
        </div>
      </form>

      {/* Sonuç bölümü */}
      {!submitted ? (
        <EmptyHint />
      ) : qQuery.isPending ? (
        <QLoading />
      ) : qQuery.isError ? (
        <QError
          message={qQuery.error.message}
          onRetry={() => qQuery.refetch()}
        />
      ) : qQuery.data && qQuery.data.papers.length > 0 ? (
        <>
          <div
            className="flex items-center justify-between border-b pb-2"
            style={{ borderColor: "var(--color-rule-soft, #f5f5f4)" }}
          >
            <span className="font-mono-pmid text-[10.5px] uppercase tracking-[0.08em] text-stone-500">
              {visiblePapers.length} / {qQuery.data.papers.length} makale ·
              alaka sırasıyla
            </span>
            <span className="font-mono-pmid text-[10.5px] text-stone-400">
              &ldquo;{submitted.slice(0, 60)}
              {submitted.length > 60 ? "…" : ""}&rdquo;
            </span>
          </div>

          <TranslationBanner translation={qQuery.data.translation} />

          {/* Filter bar (frontend) + Tümünü Seç */}
          <FilterBar
            filters={localFilters}
            onChange={setLocalFilters}
            visibleCount={visiblePapers.length}
            allSelected={allSelected}
            someSelected={someSelected}
            onToggleSelectAll={toggleSelectAll}
            disabled={visiblePapers.length === 0}
          />

          {visiblePapers.length === 0 ? (
            <NoVisible />
          ) : (
            <ul className="flex flex-col gap-2">
              {visiblePapers.map((p, i) => {
                const checked = selected.has(p.id);
                const disabled = !checked && selected.size >= maxSelect;
                return (
                  <li
                    key={p.id}
                    data-testid={`paper-row-${i}`}
                    className="rounded-xl border bg-white p-4 transition hover:border-stone-300"
                    style={{ borderColor: "var(--color-rule, #e7e5e4)" }}
                  >
                    <label className="flex items-start gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={checked}
                        disabled={disabled}
                        onChange={() => toggleSelect(p.id)}
                        data-testid={`paper-checkbox-${i}`}
                        className="mt-1.5 h-4 w-4 cursor-pointer accent-cyan-700 disabled:cursor-not-allowed disabled:opacity-40"
                      />
                      <span className="mt-0.5 font-mono-pmid text-[11px] text-stone-400">
                        [{String(i + 1).padStart(2, "0")}]
                      </span>
                      <div className="min-w-0 flex-1">
                        <h3 className="font-display text-[15.5px] font-medium leading-snug text-stone-900">
                          {p.title}
                        </h3>
                        <p className="mt-0.5 font-sans text-[12px] text-stone-500">
                          {p.authorsLabel}
                          {p.venue ? ` · ${p.venue}` : ""}
                          {p.year ? `, ${p.year}` : ""} · {p.citedByCount} atıf
                        </p>
                        {p.abstract ? (
                          <p
                            className="font-crimson mt-2 text-[13.5px] italic leading-snug text-stone-700"
                            style={{ maxWidth: "62ch" }}
                          >
                            {p.abstract}
                          </p>
                        ) : null}
                      </div>
                    </label>
                  </li>
                );
              })}
            </ul>
          )}

        </>
      ) : (
        <NoResults submitted={submitted} />
      )}
          </motion.section>
        ) : null}
      </AnimatePresence>

      {/* Selection bar — sticky çalışsın diye motion.section dışında. Sadece
          kaynaklar açıkken + arama sonucu varken görünür. */}
      {(!reviewData || sourcesOpen) &&
      qQuery.data &&
      qQuery.data.papers.length > 0 ? (
        <div
          className="sticky bottom-3 z-10 flex flex-wrap items-center justify-between gap-3 rounded-xl border bg-white px-4 py-3 shadow-sm"
          style={{ borderColor: "var(--color-rule, #e7e5e4)" }}
        >
          <span
            data-testid="selection-counter"
            className="font-mono-pmid text-[11.5px] uppercase tracking-[0.08em] text-stone-600"
          >
            Seçili: {selected.size} / {maxSelect}
            {!isAuthenticated && selected.size >= ANON_PAPER_LIMIT ? (
              <span className="ml-2 normal-case tracking-normal text-stone-400">
                · giriş yap → 25
              </span>
            ) : null}
          </span>
          <div className="flex items-center gap-2">
            {litReview.isPending ? (
              <button
                type="button"
                onClick={() => litReview.abort()}
                data-testid="cancel-review-btn"
                className="inline-flex h-9 items-center gap-1.5 rounded-lg border px-3 font-sans text-[12px] font-medium text-stone-700 transition hover:bg-stone-50"
                style={{ borderColor: "var(--color-rule, #e7e5e4)" }}
                aria-label="Literatür özetini iptal et"
              >
                İptal
              </button>
            ) : null}
            <button
              type="button"
              onClick={generateReview}
              disabled={selected.size === 0 || litReview.isPending}
              data-testid="generate-review-btn"
              className="inline-flex h-9 items-center gap-1.5 rounded-lg px-4 font-sans text-[12.5px] font-medium text-white transition disabled:cursor-not-allowed disabled:opacity-50"
              style={{ background: VITRIN }}
            >
              {litReview.isPending ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  Üretiliyor… (~15s)
                </>
              ) : (
                <>
                  <BookOpen className="h-3.5 w-3.5" />
                  Literatür Özeti Üret
                </>
              )}
            </button>
          </div>
        </div>
      ) : null}

      {/* Review panel + Projeye Dönüştür CTA — collapse durumundan bağımsız,
          her zaman görünür (review hazırsa kullanıcı doğrudan görsün). */}
      {litReview.isError ? (
        <ReviewError
          message={litReview.error.message}
          onRetry={generateReview}
        />
      ) : reviewData ? (
        <>
          <ReviewPanel review={reviewData} />
          {/* F11 Phase A: Vitrin → Atelye köprüsü (gerçek backend).
              POST /api/project/from-q → discovery-1 (ResearchAreaConfirmPage). */}
          <div
            className="flex flex-col gap-3 rounded-xl border p-5"
            style={{
              background: VITRIN_PALE,
              borderColor: VITRIN,
            }}
          >
            <div className="flex items-center justify-between gap-4">
              <div className="min-w-0">
                <h3
                  className="font-display"
                  style={{ fontSize: 16, color: "#0f172a", lineHeight: 1.25 }}
                >
                  Bu ozeti projeye donustur
                </h3>
                <p
                  style={{
                    fontSize: 13,
                    color: "#475569",
                    marginTop: 4,
                    lineHeight: 1.45,
                  }}
                >
                  Sectigin {selected.size} makale ile yeni atelye projesi ac — Kesif, Curation,
                  Bosluk, Yazim, Savunma adimlariyla derinlemesine calis.
                </p>
              </div>
              <button
                type="button"
                onClick={convertToProject}
                disabled={selected.size === 0 || isConverting}
                data-testid="convert-to-project-btn"
                className="inline-flex h-10 flex-shrink-0 items-center gap-2 rounded-lg px-5 font-sans text-[13px] font-medium text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
                style={{ background: VITRIN }}
              >
                {isConverting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Olusturuluyor…
                  </>
                ) : (
                  <>
                    <FolderPlus className="h-4 w-4" />
                    Projeye Donustur
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </button>
            </div>
            {convertError ? (
              <p
                data-testid="convert-error"
                className="rounded-md border px-3 py-2 text-[12.5px]"
                style={{
                  borderColor: "#fca5a5",
                  background: "#fef2f2",
                  color: "#991b1b",
                }}
              >
                {convertError}
              </p>
            ) : null}
          </div>
        </>
      ) : null}
    </div>
  );
}

function FilterBar({
  filters,
  onChange,
  visibleCount,
  allSelected,
  someSelected,
  onToggleSelectAll,
  disabled,
}: {
  filters: LocalFilters;
  onChange: (next: LocalFilters) => void;
  visibleCount: number;
  allSelected: boolean;
  someSelected: boolean;
  onToggleSelectAll: () => void;
  disabled: boolean;
}) {
  const cbRef = useRef<HTMLInputElement>(null);
  // HTML indeterminate sadece imperatif set edilebilir.
  useEffect(() => {
    if (cbRef.current) cbRef.current.indeterminate = someSelected;
  }, [someSelected]);

  return (
    <div
      className="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-xl border bg-stone-50/60 px-4 py-2.5"
      style={{ borderColor: "var(--color-rule, #e7e5e4)" }}
    >
      <label className="flex items-center gap-2 font-sans text-[12.5px] text-stone-700 cursor-pointer">
        <input
          ref={cbRef}
          type="checkbox"
          checked={allSelected}
          disabled={disabled}
          onChange={onToggleSelectAll}
          data-testid="select-all-checkbox"
          className="h-4 w-4 cursor-pointer accent-cyan-700 disabled:cursor-not-allowed disabled:opacity-40"
        />
        <span>Tümünü Seç</span>
        <span
          data-testid="visible-count"
          className="font-mono-pmid text-[10.5px] uppercase tracking-[0.08em] text-stone-400"
        >
          ({visibleCount} görünüyor)
        </span>
      </label>

      <span className="hidden h-4 w-px bg-stone-200 md:block" />

      <label className="flex items-center gap-1.5 font-sans text-[12.5px] text-stone-700">
        <span className="text-stone-500">Min atıf:</span>
        <input
          type="number"
          inputMode="numeric"
          min={0}
          value={filters.minCitations || ""}
          placeholder="0"
          onChange={(e) =>
            onChange({
              ...filters,
              minCitations: Math.max(0, Number(e.target.value) || 0),
            })
          }
          data-testid="filter-min-cites"
          className="h-7 w-16 rounded-md border bg-white px-2 text-[12px] outline-none focus:border-stone-900"
          style={{ borderColor: "var(--color-rule, #e7e5e4)" }}
        />
      </label>

      <label className="flex items-center gap-1.5 font-sans text-[12.5px] text-stone-700 cursor-pointer">
        <input
          type="checkbox"
          checked={filters.hasAbstractOnly}
          onChange={(e) =>
            onChange({ ...filters, hasAbstractOnly: e.target.checked })
          }
          data-testid="filter-has-abstract"
          className="h-3.5 w-3.5 cursor-pointer accent-cyan-700"
        />
        <span>Sadece abstract&apos;ı olanlar</span>
      </label>

      <label className="flex items-center gap-1.5 font-sans text-[12.5px] text-stone-700">
        <span className="text-stone-500">Sıralama:</span>
        <select
          value={filters.sort}
          onChange={(e) =>
            onChange({ ...filters, sort: e.target.value as SortMode })
          }
          data-testid="filter-sort"
          className="h-7 rounded-md border bg-white px-2 text-[12px] outline-none focus:border-stone-900"
          style={{ borderColor: "var(--color-rule, #e7e5e4)" }}
        >
          <option value="relevance">Alaka</option>
          <option value="citations_desc">Atıf ↓</option>
          <option value="year_desc">Yıl ↓</option>
        </select>
      </label>
    </div>
  );
}

function TranslationBanner({
  translation,
}: {
  translation: QueryTranslationApi | null;
}) {
  // KD-V1-S11 plan §4:
  //  - null → translate skip/fail (degraded), kullanıcıya bildir
  //  - detectedLang === "en" → tek arama yeterli, banner gösterme
  //  - aksi halde → "Aranan: <DİL> + EN çeviri (<english_query>)"
  if (translation === null) {
    return (
      <p
        data-testid="translation-degraded"
        className="font-crimson -mt-1 text-[12px] italic text-stone-500"
      >
        İngilizce çeviri atlandı, sadece kullanıcı dilinde arama yapıldı.
      </p>
    );
  }
  if (translation.detectedLang === "en") return null;
  const langLabel =
    translation.detectedLang === "tr"
      ? "TR"
      : translation.detectedLang === "id"
        ? "ID"
        : translation.detectedLang.toUpperCase();
  return (
    <p
      data-testid="translation-banner"
      className="font-crimson -mt-1 text-[12px] italic text-stone-500"
    >
      Aranan: {langLabel} + EN çeviri ({translation.englishQuery})
    </p>
  );
}

function NoVisible() {
  return (
    <div
      data-testid="filter-empty"
      className="rounded-xl border border-dashed px-6 py-8 text-center"
      style={{ borderColor: "var(--color-rule, #e7e5e4)" }}
    >
      <p className="font-display text-[14px] text-stone-700">
        Filtreyle eşleşen makale yok.
      </p>
      <p className="font-crimson mt-1 text-[12.5px] italic text-stone-500">
        Min atıf eşiğini düşür ya da abstract filtresini kapat.
      </p>
    </div>
  );
}

function EmptyHint() {
  return (
    <div
      className="rounded-xl border border-dashed px-6 py-10 text-center"
      style={{ borderColor: "var(--color-rule, #e7e5e4)" }}
    >
      <p className="font-crimson text-[14.5px] italic text-stone-500">
        Yukarıya bir sorgu yaz veya örneklerden birini dene.
      </p>
    </div>
  );
}

function QLoading() {
  return (
    <div
      data-testid="q-loading"
      className="flex flex-col items-center justify-center rounded-xl border border-dashed px-6 py-12 text-center"
      style={{ borderColor: "var(--color-rule, #e7e5e4)" }}
    >
      <Loader2 className="mb-3 h-6 w-6 animate-spin text-stone-400" aria-hidden />
      <p className="font-display text-[14px] text-stone-700">
        Makale aranıyor…
      </p>
      <p className="font-crimson mt-1 text-[12.5px] italic text-stone-500">
        OpenAlex&apos;ten 1-3 saniye sürebilir.
      </p>
    </div>
  );
}

function QError({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div
      data-testid="q-error"
      className="rounded-xl border px-6 py-10 text-center"
      style={{ borderColor: "#fca5a5", background: "#fef2f2" }}
    >
      <p className="font-display text-[14px] text-rose-800">
        Arama yapılamadı.
      </p>
      <p className="font-crimson mt-1 text-[12.5px] italic text-rose-600">
        {message}
      </p>
      <button
        type="button"
        onClick={onRetry}
        className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-rose-700 px-3.5 py-1.5 text-[12.5px] font-medium text-white transition hover:bg-rose-800"
      >
        Tekrar dene
      </button>
    </div>
  );
}

function NoResults({ submitted }: { submitted: string }) {
  return (
    <div
      data-testid="q-empty"
      className="rounded-xl border border-dashed px-6 py-10 text-center"
      style={{ borderColor: "var(--color-rule, #e7e5e4)" }}
    >
      <p className="font-display text-[14px] text-stone-700">
        Bu sorgu için makale bulunamadı.
      </p>
      <p className="font-crimson mt-1 text-[12.5px] italic text-stone-500">
        &ldquo;{submitted}&rdquo; — daha geniş anahtar kelime dene.
      </p>
    </div>
  );
}

function ReviewError({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div
      data-testid="review-error"
      className="rounded-xl border px-6 py-8 text-center"
      style={{ borderColor: "#fca5a5", background: "#fef2f2" }}
    >
      <p className="font-display text-[14px] text-rose-800">
        Özet üretilemedi.
      </p>
      <p className="font-crimson mt-1 text-[12.5px] italic text-rose-600">
        {message}
      </p>
      <button
        type="button"
        onClick={onRetry}
        className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-rose-700 px-3.5 py-1.5 text-[12.5px] font-medium text-white transition hover:bg-rose-800"
      >
        Tekrar dene
      </button>
    </div>
  );
}

function ReviewPanel({ review }: { review: LiteratureReviewApi }) {
  // KD-V1-S10-04 (revize 2026-05-09): tek blok content + numaralı kaynaklar.
  // Akademik makalenin "literatür inceleme bölümü" — komple makale değil.
  return (
    <article
      data-testid="review-panel"
      className="rounded-2xl border bg-white p-6 md:p-8"
      style={{ borderColor: "var(--color-rule, #e7e5e4)" }}
    >
      <header className="mb-4 flex items-center justify-between gap-3">
        <span className="font-mono-pmid text-[10.5px] uppercase tracking-[0.08em] text-stone-400">
          Literatür İncelemesi
        </span>
        {/* V1-S12-03: sesli dinlet — özetin TR seslendirmesi */}
        <AudioPlayButton text={review.content} lang="tr" />
      </header>

      <p
        className="font-crimson whitespace-pre-line text-[14.5px] leading-relaxed text-stone-800"
        style={{ maxWidth: "70ch" }}
      >
        {review.content}
      </p>

      <div
        className="mt-6 border-t pt-4"
        style={{ borderColor: "var(--color-rule-soft, #f5f5f4)" }}
      >
        <h3 className="mb-2 font-display text-[15px] font-medium text-stone-900">
          Kaynaklar
        </h3>
        <ol className="flex flex-col gap-1.5">
          {review.references.map((ref) => (
            <li
              key={ref.index}
              className="flex gap-2 font-sans text-[12.5px] leading-snug text-stone-700"
            >
              <span className="font-mono-pmid text-[11px] text-stone-400">
                [{String(ref.index).padStart(2, "0")}]
              </span>
              <span>{ref.citation}</span>
            </li>
          ))}
        </ol>
      </div>
    </article>
  );
}
