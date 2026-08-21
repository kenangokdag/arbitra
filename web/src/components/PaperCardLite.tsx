"use client";

import { useState } from "react";
import {
  Bookmark,
  BookmarkCheck,
  Check,
  Copy,
  ExternalLink,
  Eye,
} from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api";
import type { ReadingListItem } from "@/lib/types";

export interface PaperCardLiteData {
  id: string;
  title: string;
  authors: string[];
  venue?: string;
  volume?: string;
  year?: number;
  doi?: string;
  is_open_access: boolean;
  source: "OpenAlex" | "arXiv";
  scholar_url?: string;
}

function formatCitation(p: PaperCardLiteData): string {
  const authors =
    p.authors.length > 3
      ? `${p.authors.slice(0, 3).join(", ")} et al.`
      : p.authors.join(", ");
  const venue = p.venue ? `, ${p.venue}` : "";
  const vol = p.volume ? ` ${p.volume}` : "";
  const year = p.year ? ` (${p.year})` : "";
  const doi = p.doi ? `. https://doi.org/${p.doi}` : "";
  return `${authors}${year}. ${p.title}${venue}${vol}${doi}`;
}

export function PaperCardLite({ paper, onRead }: {
  paper: PaperCardLiteData;
  onRead?: (id: string) => void;
}) {
  const [added, setAdded] = useState(false);
  const [copied, setCopied] = useState(false);
  const queryClient = useQueryClient();

  const addToList = useMutation({
    mutationFn: () =>
      apiFetch<ReadingListItem>("/api/reading-list", {
        method: "POST",
        body: { paper_id: paper.id, status: "want_to_read" },
      }),
    onSuccess: () => {
      setAdded(true);
      queryClient.invalidateQueries({ queryKey: ["reading-list"] });
    },
  });

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(formatCitation(paper));
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable */
    }
  };

  const authorsLine =
    paper.authors.length > 3
      ? `${paper.authors.slice(0, 3).join(", ")} et al.`
      : paper.authors.join(", ");

  const baseBtn =
    "inline-flex h-[26px] items-center gap-1 rounded-md border px-2.5 text-[11.5px] font-medium transition-colors";
  const btnStyle = {
    borderColor: "var(--color-rule-soft)",
    background: "var(--color-bg)",
    color: "var(--color-ink-mute)",
  };
  const infoStyle = {
    background: "var(--color-info-pale)",
    border: "1px solid rgba(29,78,216,0.2)",
    color: "var(--color-info)",
  };

  return (
    <article
      className="relative rounded-[10px] bg-white px-4 py-3.5 transition-[box-shadow,transform] duration-200 hover:-translate-y-px hover:shadow-md"
      style={{ border: "1px solid var(--color-rule-soft)" }}
    >
      {/* Top-right badges */}
      <div className="absolute right-3 top-3 flex items-center gap-1">
        {paper.is_open_access && (
          <span
            className="rounded-full px-2 py-0.5 font-mono text-[9.5px]"
            style={{
              background: "var(--color-ok-pale)",
              border: "1px solid #a7f3d0",
              color: "var(--color-ok)",
            }}
          >
            OA
          </span>
        )}
        <span
          className="rounded-full px-2 py-0.5 font-mono text-[9.5px]"
          style={{
            background: "var(--color-bg-soft)",
            border: "1px solid var(--color-rule-soft)",
            color: "var(--color-ink-faint)",
          }}
        >
          {paper.source}
        </span>
      </div>

      <div className="grid grid-cols-[1fr_auto] items-start gap-3 pr-16">
        <button
          type="button"
          onClick={() => onRead?.(paper.id)}
          className="font-display text-left text-[15px] font-medium italic leading-snug transition-colors hover:underline"
          style={{ color: "var(--color-ink)" }}
        >
          {paper.title}
        </button>
        {paper.year !== undefined && (
          <span
            className="font-mono text-[11px] leading-[1.5]"
            style={{ color: "var(--color-ink-faint)" }}
          >
            {paper.year}
          </span>
        )}
      </div>

      <p
        className="mt-1.5 text-xs"
        style={{ color: "var(--color-ink-faint)" }}
      >
        {authorsLine}
      </p>
      {paper.venue && (
        <p
          className="mb-2.5 text-xs italic"
          style={{ color: "var(--color-ink-faint)" }}
        >
          {paper.venue}
          {paper.volume ? ` ${paper.volume}` : ""}
        </p>
      )}

      {/* 5 actions */}
      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        <button
          type="button"
          className={baseBtn}
          style={btnStyle}
          onClick={() => onRead?.(paper.id)}
        >
          <Eye className="h-3 w-3" />
          Oku
        </button>

        <button
          type="button"
          className={baseBtn}
          style={btnStyle}
          disabled={added || addToList.isPending}
          onClick={() => addToList.mutate()}
        >
          {added ? (
            <BookmarkCheck className="h-3 w-3" style={{ color: "var(--color-ok)" }} />
          ) : (
            <Bookmark className="h-3 w-3" />
          )}
          {added ? "Eklendi" : "Listeme Ekle"}
        </button>

        <a
          className={baseBtn}
          style={paper.doi ? infoStyle : { ...btnStyle, opacity: 0.5, pointerEvents: "none" }}
          href={paper.doi ? `https://doi.org/${paper.doi}` : undefined}
          target="_blank"
          rel="noopener noreferrer"
          aria-disabled={!paper.doi}
        >
          <ExternalLink className="h-3 w-3" />
          DOI
        </a>

        <a
          className={baseBtn}
          style={
            paper.scholar_url
              ? infoStyle
              : { ...btnStyle, opacity: 0.5, pointerEvents: "none" }
          }
          href={paper.scholar_url}
          target="_blank"
          rel="noopener noreferrer"
          aria-disabled={!paper.scholar_url}
        >
          <ExternalLink className="h-3 w-3" />
          Scholar
        </a>

        <button
          type="button"
          className={baseBtn}
          style={btnStyle}
          onClick={handleCopy}
        >
          {copied ? (
            <Check className="h-3 w-3" style={{ color: "var(--color-ok)" }} />
          ) : (
            <Copy className="h-3 w-3" />
          )}
          {copied ? "Kopyalandi" : "Atif Kopyala"}
        </button>
      </div>
    </article>
  );
}
