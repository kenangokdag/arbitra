"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  BookmarkPlus,
  Check,
  Download,
  ExternalLink,
  FileText,
  Loader2,
  MessageSquare,
  StickyNote,
} from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { Hint } from "@/components/Hint";
import { Button } from "@/components/ui/button";
import { apiFetch, ApiError } from "@/lib/api";
import type {
  DecisionBand,
  NoteItem,
  PaperDetail,
  ReadingListItem,
  SummarizeAccepted,
  SummaryDoc,
} from "@/lib/types";

const BAND_LABEL: Record<DecisionBand, string> = {
  canon: "Kanonik kanıt",
  strong_evidence: "Güçlü kanıt",
  frontier: "Yenilik",
  risk: "Riskli",
};

const BAND_TONE: Record<DecisionBand, string> = {
  canon: "border-emerald-200 bg-emerald-50 text-emerald-700",
  strong_evidence: "border-blue-200 bg-blue-50 text-blue-700",
  frontier: "border-amber-200 bg-amber-50 text-amber-700",
  risk: "border-red-200 bg-red-50 text-red-700",
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function PaperDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const queryClient = useQueryClient();
  const [added, setAdded] = useState(false);
  const [noteAdded, setNoteAdded] = useState(false);
  const [summaryText, setSummaryText] = useState<string | null>(null);

  const { data, isLoading, isError, error } = useQuery<PaperDetail>({
    queryKey: ["paper", id],
    queryFn: () => apiFetch<PaperDetail>(`/api/paper/${id}`),
    retry: false,
  });

  const addToList = useMutation({
    mutationFn: () =>
      apiFetch<ReadingListItem>("/api/reading-list", {
        method: "POST",
        body: { paper_id: id, status: "want_to_read" },
      }),
    onSuccess: () => {
      setAdded(true);
      queryClient.invalidateQueries({ queryKey: ["reading-list"] });
    },
  });

  const addNote = useMutation({
    mutationFn: () =>
      apiFetch<NoteItem>("/api/notes", {
        method: "POST",
        body: { paper_id: id, content: `Not: ${data?.title ?? id}`, tags: [] },
      }),
    onSuccess: () => {
      setNoteAdded(true);
      queryClient.invalidateQueries({ queryKey: ["notes"] });
    },
  });

  const summarize = useMutation({
    mutationFn: async () => {
      const accepted = await apiFetch<SummarizeAccepted>("/api/summarize", {
        method: "POST",
        body: { paper_id: id, mode: "tldr", language: "tr" },
      });
      const doc = await apiFetch<SummaryDoc>(
        `/api/summarize/${accepted.task_id}`
      );
      return doc;
    },
    onSuccess: (doc) => setSummaryText(doc.text),
  });

  if (isLoading) {
    return (
      <>
        <div className="mb-4 h-6 w-32 animate-pulse rounded bg-bg-soft" />
        <div className="h-10 w-3/4 animate-pulse rounded bg-bg-soft" />
        <div className="mt-3 h-4 w-1/2 animate-pulse rounded bg-bg-soft" />
        <div className="mt-6 h-40 animate-pulse rounded-xl bg-bg-soft" />
      </>
    );
  }

  if (isError) {
    const notFound = error instanceof ApiError && error.status === 404;
    return (
      <>
        <Link
          href="/"
          className="mb-4 inline-flex items-center gap-1 text-[13px] text-ink-mute hover:text-ink"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Geri
        </Link>
        <PageHeader
          title={notFound ? "Makale bulunamadı" : "Yüklenemedi"}
          lede={
            notFound
              ? `${id} için ne yerel veritabanımızda ne de OpenAlex'te kayıt var.`
              : error instanceof ApiError
                ? error.message
                : "Bağlantı hatası."
          }
        />
      </>
    );
  }

  if (!data) return null;

  const authorsLine =
    data.authors.length > 0
      ? data.authors.slice(0, 6).join(", ") +
        (data.authors.length > 6 ? ` ve ${data.authors.length - 6} kişi daha` : "")
      : "Yazar bilgisi yok";
  const yearStr = data.year ?? "—";
  const journal = data.journal ?? "—";

  return (
    <>
      <Link
        href="/"
        className="mb-3 inline-flex items-center gap-1 text-[13px] text-ink-mute hover:text-ink"
      >
        <ArrowLeft className="h-3.5 w-3.5" /> Geri
      </Link>

      <div className="mb-2 flex flex-wrap items-center gap-1.5 text-[11px] font-medium">
        {data.is_open_access && (
          <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-emerald-700">
            Açık erişim
          </span>
        )}
        <span className="rounded-full border border-stone-200 bg-stone-50 px-2 py-0.5 text-stone-600">
          {data.language?.toUpperCase() ?? "—"}
        </span>
        <span
          className={`rounded-full border px-2 py-0.5 ${BAND_TONE[data.decision_band]}`}
        >
          {BAND_LABEL[data.decision_band]}
        </span>
      </div>

      <h1 className="font-display mb-2 text-[26px] font-medium italic leading-tight text-ink">
        {data.title}
      </h1>

      <p className="mb-5 text-[13.5px] text-ink-mute">
        {authorsLine} ·{" "}
        <em className="text-ink-soft">{journal}</em> · {yearStr}
        {data.year_verified ? "" : " (?)"} · {data.cited_by_count.toLocaleString("tr-TR")} atıf
      </p>

      <div className="mb-6 flex flex-wrap items-center gap-1.5">
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
          {added ? "Eklendi" : addToList.isPending ? "Ekleniyor..." : "Listeme ekle"}
        </Button>
        <Button
          size="sm"
          variant="secondary"
          type="button"
          disabled={summarize.isPending || !!summaryText}
          onClick={() => summarize.mutate()}
        >
          {summarize.isPending ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : summaryText ? (
            <Check className="h-3.5 w-3.5 text-emerald-600" />
          ) : (
            <FileText className="h-3.5 w-3.5" />
          )}
          {summarize.isPending ? "Özetleniyor..." : summaryText ? "Özetlendi" : "Özetle"}
        </Button>
        <Link href={`/chat?paper=${id}`}>
          <Button size="sm" variant="secondary" type="button">
            <MessageSquare className="h-3.5 w-3.5" />
            Sohbet
          </Button>
        </Link>
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
          {noteAdded ? "Not eklendi" : "Nota ekle"}
        </Button>
        <a
          href={`${API_URL}/api/paper/${id}/export?fmt=bibtex`}
          target="_blank"
          rel="noopener noreferrer"
        >
          <Button size="sm" variant="ghost" type="button">
            <Download className="h-3.5 w-3.5" />
            BibTeX
          </Button>
        </a>
        {data.doi && (
          <a
            href={`https://doi.org/${data.doi.replace(/^https?:\/\/(dx\.)?doi\.org\//, "")}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            <Button size="sm" variant="ghost" type="button">
              <ExternalLink className="h-3.5 w-3.5" />
              DOI
            </Button>
          </a>
        )}
        {data.url && (
          <a href={data.url} target="_blank" rel="noopener noreferrer">
            <Button size="sm" variant="ghost" type="button">
              <ExternalLink className="h-3.5 w-3.5" />
              Kaynak
            </Button>
          </a>
        )}
      </div>

      {addToList.isError && (
        <Hint>Listeye eklenemedi: {(addToList.error as Error).message}</Hint>
      )}
      {summarize.isError && (
        <Hint>Özetleme başarısız: {(summarize.error as Error).message}</Hint>
      )}

      {summaryText && (
        <section className="mb-6 rounded-lg border border-amber-200 bg-amber-50/50 px-5 py-4">
          <h2 className="serif mb-2 text-[14px] font-medium italic text-amber-900">
            Özet
          </h2>
          <p className="text-[13.5px] leading-relaxed text-stone-700">{summaryText}</p>
        </section>
      )}

      {data.abstract ? (
        <section className="mb-6">
          <h2 className="serif mb-2 text-[16px] font-medium italic text-ink-soft">
            Özet (kaynaktan)
          </h2>
          <p className="whitespace-pre-line text-[14px] leading-relaxed text-ink-soft">
            {data.abstract}
          </p>
        </section>
      ) : (
        <p className="mb-6 text-[13px] italic text-ink-mute">
          Özet kaynakta bulunamadı.
        </p>
      )}

      {data.gate_warnings.length > 0 && (
        <section className="mb-6">
          <h2 className="serif mb-2 text-[14px] font-medium italic text-ink-soft">
            Uyarılar
          </h2>
          <ul className="flex flex-col gap-1.5">
            {data.gate_warnings.map((w, i) => (
              <li
                key={`${w.gate_id}-${i}`}
                className={`rounded-md border px-3 py-2 text-[12.5px] ${
                  w.severity === "block"
                    ? "border-red-200 bg-red-50 text-red-700"
                    : w.severity === "warn"
                      ? "border-amber-200 bg-amber-50 text-amber-700"
                      : "border-stone-200 bg-stone-50 text-stone-600"
                }`}
              >
                <span className="font-mono text-[11px]">[{w.gate_id}]</span>{" "}
                {w.message}
              </li>
            ))}
          </ul>
        </section>
      )}

      {Object.keys(data.signals_13 ?? {}).length > 0 && (
        <section className="mb-6">
          <h2 className="serif mb-2 text-[14px] font-medium italic text-ink-soft">
            Sinyaller
          </h2>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {Object.entries(data.signals_13)
              .filter(([, v]) => typeof v === "number" && v > 0)
              .slice(0, 8)
              .map(([k, v]) => (
                <div
                  key={k}
                  className="rounded-md border border-rule bg-bg-card px-3 py-2"
                >
                  <div className="text-[11px] uppercase tracking-wide text-ink-faint">
                    {k}
                  </div>
                  <div className="font-mono text-[14px] text-ink-soft">
                    {v.toFixed(2)}
                  </div>
                </div>
              ))}
          </div>
        </section>
      )}
    </>
  );
}
