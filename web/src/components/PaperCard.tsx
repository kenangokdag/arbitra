"use client";

import { useState } from "react";
import {
  BookmarkPlus,
  Check,
  ChevronDown,
  ChevronUp,
  FileText,
  Loader2,
  MessageCircleQuestion,
  MessageSquare,
  StickyNote,
} from "lucide-react";
import Link from "next/link";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { Button } from "./ui/button";
import { apiFetch } from "@/lib/api";
import { useOpenChatbox } from "@/stores/ui";
import type {
  NoteItem,
  PaperCard as PaperCardData,
  ReadingListItem,
  SummarizeAccepted,
  SummaryDoc,
} from "@/lib/types";

const BAND_LABEL: Record<PaperCardData["decision_band"], string> = {
  canon: "Kanonik kanit",
  strong_evidence: "Guclu kanit",
  frontier: "Yenilik",
  risk: "Riskli",
};

const BAND_TONE: Record<
  PaperCardData["decision_band"],
  { stripe: string; chip: string }
> = {
  canon: {
    stripe: "border-l-emerald-600",
    chip: "border-emerald-200 bg-emerald-50 text-emerald-700",
  },
  strong_evidence: {
    stripe: "border-l-blue-600",
    chip: "border-blue-200 bg-blue-50 text-blue-700",
  },
  frontier: {
    stripe: "border-l-amber-600",
    chip: "border-amber-200 bg-amber-50 text-amber-700",
  },
  risk: {
    stripe: "border-l-red-600",
    chip: "border-red-200 bg-red-50 text-red-700",
  },
};

const LANG_LABEL: Record<string, string> = {
  tr: "Turkce",
  en: "Ingilizce",
  id: "Endonezce",
};

type EstraSignalSpec = {
  key: "Q_weak" | "MQ_Tier1" | "CD5" | "sentence_role_RES";
  label: string;
  desc: string;
  hi: number;
  lo: number;
};

const ESTRA_SPECS: EstraSignalSpec[] = [
  { key: "Q_weak", label: "Q", desc: "Kalite zayif sinyal", hi: 1.5, lo: 1.0 },
  { key: "MQ_Tier1", label: "M", desc: "Yontem Tier-1", hi: 1.5, lo: 1.0 },
  { key: "CD5", label: "Δ5", desc: "Atif delta 5y", hi: 1.0, lo: 0.5 },
  { key: "sentence_role_RES", label: "R", desc: "Bulgu cumle yogunlugu", hi: 1.5, lo: 1.0 },
];

function estraTone(value: number, hi: number, lo: number): string {
  if (value >= hi) return "border-emerald-200 bg-emerald-50 text-emerald-700";
  if (value >= lo) return "border-amber-200 bg-amber-50 text-amber-700";
  return "border-stone-200 bg-stone-50 text-stone-600";
}

function EstraChips({ signals }: { signals: Record<string, number> }) {
  if (Object.keys(signals).length === 0) return null;
  return (
    <div
      className="mb-2 flex flex-wrap items-center gap-1 font-mono text-[10.5px]"
      data-testid="estra-chips"
    >
      {ESTRA_SPECS.map((spec) => {
        const v = signals[spec.key] ?? 0;
        return (
          <span
            key={spec.key}
            className={`rounded-md border px-1.5 py-0.5 ${estraTone(v, spec.hi, spec.lo)}`}
            title={`${spec.key} = ${v.toFixed(2)} — ${spec.desc}`}
          >
            {spec.label} {v.toFixed(1)}
          </span>
        );
      })}
    </div>
  );
}

export function PaperCard({
  paper,
  isGhost = false,
  compact = false,
}: {
  paper: PaperCardData;
  isGhost?: boolean;
  compact?: boolean;
}) {
  const [added, setAdded] = useState(false);
  const [summaryText, setSummaryText] = useState<string | null>(null);
  const [summaryOpen, setSummaryOpen] = useState(false);
  const [noteAdded, setNoteAdded] = useState(false);
  const queryClient = useQueryClient();
  const openChatbox = useOpenChatbox();

  const addToList = useMutation({
    mutationFn: () =>
      apiFetch<ReadingListItem>("/api/reading-list", {
        method: "POST",
        body: { paper_id: paper.paper_id, status: "want_to_read" },
      }),
    onSuccess: () => {
      setAdded(true);
      queryClient.invalidateQueries({ queryKey: ["reading-list"] });
    },
  });

  const summarize = useMutation({
    mutationFn: async () => {
      const accepted = await apiFetch<SummarizeAccepted>("/api/summarize", {
        method: "POST",
        body: { paper_id: paper.paper_id, mode: "tldr", language: "tr" },
      });
      const doc = await apiFetch<SummaryDoc>(
        `/api/summarize/${accepted.task_id}`
      );
      return doc;
    },
    onSuccess: (doc) => {
      setSummaryText(doc.text);
      setSummaryOpen(true);
    },
  });

  const addNote = useMutation({
    mutationFn: () =>
      apiFetch<NoteItem>("/api/notes", {
        method: "POST",
        body: {
          paper_id: paper.paper_id,
          content: `Not: ${paper.title}`,
          tags: [],
        },
      }),
    onSuccess: () => {
      setNoteAdded(true);
      queryClient.invalidateQueries({ queryKey: ["notes"] });
    },
  });

  const lang = paper.language
    ? (LANG_LABEL[paper.language] ?? paper.language.toUpperCase())
    : "--";
  const authorsLine =
    paper.authors.slice(0, 3).join(", ") +
    (paper.authors.length > 3 ? " ve dig." : "");
  const journal = paper.journal ?? "--";
  const year = isGhost && !paper.year_verified ? "0000" : (paper.year ?? "--");
  const cite = paper.n_cited.toLocaleString("tr-TR");

  const tone = BAND_TONE[paper.decision_band];

  return (
    <article
      className={`group relative rounded-xl border border-stone-200 ${
        isGhost ? "border-dashed" : ""
      } border-l-[3px] border-l-solid ${tone.stripe} bg-white ${compact ? "p-3.5" : "p-5"} shadow-sm transition-[box-shadow,transform] duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] hover:-translate-y-0.5 hover:shadow-lg`}
      style={isGhost ? { opacity: 0.82 } : undefined}
    >
      {isGhost && (
        <span
          className="absolute right-3 top-3 rounded-full px-2 py-0.5 font-mono text-[9.5px]"
          style={{
            background: "var(--color-bg-soft)",
            border: "1px solid var(--color-rule)",
            color: "var(--color-ink-faint)",
          }}
        >
          Klasik kaynak
        </span>
      )}
      <div className="mb-2.5 flex flex-wrap items-center gap-1.5 text-[11px] font-medium">
        {paper.is_open_access && (
          <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-emerald-700">
            Acik erisim
          </span>
        )}
        <span className="rounded-full border border-stone-200 bg-stone-50 px-2 py-0.5 text-stone-600">
          {lang}
        </span>
        <span className={`rounded-full border px-2 py-0.5 ${tone.chip}`}>
          {BAND_LABEL[paper.decision_band]}
        </span>
      </div>

      <EstraChips signals={paper.signals_13} />

      <h3
        className={`font-display mb-1.5 ${compact ? "text-[15px]" : "text-[17px]"} font-medium italic leading-snug transition-[letter-spacing] duration-300 group-hover:tracking-[-0.02em]`}
        style={{ color: isGhost ? "var(--color-ink-soft)" : undefined }}
      >
        <Link
          href={`/paper/${paper.paper_id}`}
          className={`transition-colors duration-150 ${isGhost ? "hover:text-stone-900" : "hover:text-indigo-700"} ${isGhost ? "text-stone-700" : "text-stone-900"}`}
        >
          {paper.title}
        </Link>
      </h3>

      <p className="mb-3 text-[12.5px] text-stone-500">
        {authorsLine} · <em className="text-stone-600">{journal}</em> · {year}
        {paper.year_verified ? "" : " (?)"} · {cite} atif
      </p>

      {!compact && paper.abstract_excerpt && (
        <p className="mb-4 line-clamp-3 text-[13.5px] leading-relaxed text-stone-600">
          {paper.abstract_excerpt}
        </p>
      )}

      {/* Summary result */}
      {!compact && summaryText && (
        <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50/50 px-4 py-3">
          <button
            type="button"
            onClick={() => setSummaryOpen(!summaryOpen)}
            className="flex w-full items-center justify-between text-[12.5px] font-medium text-amber-800"
          >
            <span>Ozet</span>
            {summaryOpen ? (
              <ChevronUp className="h-3.5 w-3.5" />
            ) : (
              <ChevronDown className="h-3.5 w-3.5" />
            )}
          </button>
          {summaryOpen && (
            <p className="mt-2 text-[13px] leading-relaxed text-stone-700">
              {summaryText}
            </p>
          )}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-1.5">
        <Link
          href={`/paper/${paper.paper_id}`}
          className="inline-flex h-8 items-center gap-1 rounded-lg px-3.5 text-[13px] font-medium text-white transition-colors duration-150 hover:opacity-90"
          style={{
            background: "linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)",
          }}
        >
          Detay
        </Link>
        <Button
          size="sm"
          variant="secondary"
          type="button"
          disabled={added || addToList.isPending}
          onClick={() => addToList.mutate()}
        >
          {added ? (
            <Check className="h-3.5 w-3.5 text-emerald-600" />
          ) : (
            <BookmarkPlus className="h-3.5 w-3.5" />
          )}
          {added ? "Eklendi" : addToList.isPending ? "Ekleniyor..." : "Listeme"}
        </Button>
        {!compact && (
          <Button
            size="sm"
            variant="secondary"
            type="button"
            disabled={isGhost || summarize.isPending || !!summaryText}
            onClick={() => summarize.mutate()}
          >
            {summarize.isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : summaryText ? (
              <Check className="h-3.5 w-3.5 text-emerald-600" />
            ) : (
              <FileText className="h-3.5 w-3.5" />
            )}
            {summarize.isPending
              ? "Ozetleniyor..."
              : summaryText
                ? "Ozetlendi"
                : "Ozetle"}
          </Button>
        )}
        <Link href={`/chat?paper=${paper.paper_id}`}>
          <Button size="sm" variant="secondary" type="button">
            <MessageSquare className="h-3.5 w-3.5" />
            Sohbet
          </Button>
        </Link>
        {!compact && (
          <Button
            size="sm"
            variant="ghost"
            type="button"
            disabled={noteAdded || addNote.isPending}
            onClick={() => addNote.mutate()}
          >
            {noteAdded ? (
              <Check className="h-3.5 w-3.5 text-emerald-600" />
            ) : (
              <StickyNote className="h-3.5 w-3.5" />
            )}
            {noteAdded ? "Not eklendi" : addNote.isPending ? "Ekleniyor..." : "Nota ekle"}
          </Button>
        )}
        {!compact && (
          <Button
            size="sm"
            variant="ghost"
            type="button"
            onClick={() =>
              openChatbox({
                kind: "paper",
                paperId: paper.paper_id,
                title: paper.title,
              })
            }
          >
            <MessageCircleQuestion className="h-3.5 w-3.5" />
            Danismana sor
          </Button>
        )}
      </div>
    </article>
  );
}
