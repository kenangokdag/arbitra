"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { Hint } from "@/components/Hint";
import { PageHeader } from "@/components/PageHeader";
import { PaperCard } from "@/components/PaperCard";
import { SearchPending } from "@/components/SearchPending";
import { apiFetch, ApiError } from "@/lib/api";
import type { SearchResponse } from "@/lib/types";

type YearFilter = "all" | "3" | "5" | "10";
type LangFilter = "all" | "tr" | "en" | "id";

const YEAR_OPTIONS: { value: YearFilter; label: string }[] = [
  { value: "all", label: "Yıl: hepsi" },
  { value: "3", label: "Son 3 yıl" },
  { value: "5", label: "Son 5 yıl" },
  { value: "10", label: "Son 10 yıl" },
];

const LANG_OPTIONS: { value: LangFilter; label: string }[] = [
  { value: "all", label: "Dil: hepsi" },
  { value: "tr", label: "Türkçe" },
  { value: "en", label: "İngilizce" },
  { value: "id", label: "Endonezce" },
];

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [yearFilter, setYearFilter] = useState<YearFilter>("all");
  const [langFilter, setLangFilter] = useState<LangFilter>("all");

  const {
    data,
    isLoading,
    isError,
    error,
    isFetched,
  } = useQuery<SearchResponse>({
    queryKey: ["search", submitted],
    queryFn: () =>
      apiFetch<SearchResponse>("/api/search", {
        method: "POST",
        body: { query: submitted, k: 50 },
      }),
    enabled: submitted.length > 0,
  });

  const papers = data?.papers ?? [];
  const latencyMs = data?.latency_ms;
  const showInitial = !submitted;

  const filteredPapers = useMemo(() => {
    if (yearFilter === "all" && langFilter === "all") return papers;
    const currentYear = new Date().getFullYear();
    const yearCutoff =
      yearFilter === "all" ? null : currentYear - parseInt(yearFilter, 10);
    return papers.filter((p) => {
      if (yearCutoff !== null) {
        if (p.year == null || p.year < yearCutoff) return false;
      }
      if (langFilter !== "all" && p.language !== langFilter) return false;
      return true;
    });
  }, [papers, yearFilter, langFilter]);

  const filterActive = yearFilter !== "all" || langFilter !== "all";

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = query.trim();
    if (trimmed) setSubmitted(trimmed);
  }

  return (
    <>
      <PageHeader
        title="Makale Ara"
        lede="Anahtar kelime, yazar adı veya bir cümle ile arayın. İlk 50 sonuç gösterilir; istediğinizi okuma listenize ekleyebilir, özetletebilirsiniz."
      />

      {showInitial && (
        <Hint>
          Arama yaparak başlayın — sonuçlar backend API&apos;den çekilecektir.
        </Hint>
      )}

      <form className="mb-5 flex gap-2" onSubmit={handleSubmit}>
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Örn: tıbbi görüntülerde self-supervised learning"
          className="flex-1 rounded-sm border border-rule bg-bg-card px-3.5 py-2 text-[14px] text-ink outline-none placeholder:text-ink-mute focus:border-accent focus:ring-2 focus:ring-accent/25"
          aria-label="Arama sorgusu"
        />
        <button
          type="submit"
          disabled={isLoading}
          className="rounded-sm bg-primary px-4 py-2 text-[14px] font-medium tracking-[-0.005em] text-primary-foreground transition-colors duration-150 hover:bg-primary/90 disabled:opacity-50"
        >
          {isLoading ? "Aranıyor…" : "Ara"}
        </button>
      </form>

      {isLoading && <SearchPending />}

      {isError && (
        <div className="mb-5 rounded-md border border-red-200 bg-red-50 px-3.5 py-2.5 text-[13px] text-red-700">
          Arama sırasında hata oluştu:{" "}
          {error instanceof ApiError ? error.message : "Bağlantı hatası"}
        </div>
      )}

      {isFetched && !isLoading && !isError && submitted && (
        <>
          <div className="mb-5 flex flex-wrap items-center gap-1.5 text-[12.5px] text-ink-soft">
            <span className="text-ink-mute">Filtre:</span>
            <select
              value={yearFilter}
              onChange={(e) => setYearFilter(e.target.value as YearFilter)}
              aria-label="Yıl filtresi"
              className={`rounded-full border px-2.5 py-1 transition-colors duration-150 ${
                yearFilter !== "all"
                  ? "border-accent bg-accent/10 text-accent"
                  : "border-rule bg-bg-card hover:bg-bg-hover"
              }`}
            >
              {YEAR_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            <select
              value={langFilter}
              onChange={(e) => setLangFilter(e.target.value as LangFilter)}
              aria-label="Dil filtresi"
              className={`rounded-full border px-2.5 py-1 transition-colors duration-150 ${
                langFilter !== "all"
                  ? "border-accent bg-accent/10 text-accent"
                  : "border-rule bg-bg-card hover:bg-bg-hover"
              }`}
            >
              {LANG_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            {filterActive && (
              <button
                type="button"
                onClick={() => {
                  setYearFilter("all");
                  setLangFilter("all");
                }}
                className="rounded-full border border-rule bg-bg-card px-2.5 py-1 text-ink-mute transition-colors duration-150 hover:bg-bg-hover"
              >
                Sıfırla
              </button>
            )}
            <span className="ml-auto text-[12.5px] text-ink-mute">
              {filterActive
                ? `${filteredPapers.length} / ${papers.length} sonuç`
                : `${papers.length} sonuç`}
              {latencyMs != null ? ` · ${latencyMs} ms` : ""}
            </span>
          </div>

          <div className="flex flex-col gap-4">
            {filteredPapers.map((paper) => (
              <PaperCard key={paper.paper_id} paper={paper} compact />
            ))}
            {filteredPapers.length === 0 && (
              <p className="py-8 text-center text-[14px] text-ink-mute">
                {filterActive
                  ? "Filtreye uyan sonuç yok. Filtreyi sıfırlayın."
                  : "Sonuç bulunamadı."}
              </p>
            )}
          </div>
        </>
      )}

    </>
  );
}
