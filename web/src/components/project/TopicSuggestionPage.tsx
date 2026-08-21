"use client";

import { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import { Lock, ChevronRight, Eye, Loader2, RefreshCw, ArrowRight, CheckCircle2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { AdvisorBanner } from "@/components/project/AdvisorBanner";
import { apiFetch } from "@/lib/api";

interface PaperCard {
  paper_id: string;
  title: string;
  abstract_excerpt: string | null;
  authors: string | null;
  year: number | null;
  signals_13: Record<string, number>;
}

interface Top5Response {
  papers: PaperCard[];
  needs_clarify: boolean;
  margin_used: number;
}

// V1-S19-P007: anchor context project read — parsed_understanding.focuses + seed_query
type ParsedUnderstandingApi = {
  focuses: string[];
  field: string;
  subfield: string | null;
  interdisc: boolean;
  confidence: "high" | "med" | "low";
  adviser_text: string;
  finished: boolean;
};

type ProjectReadApi = {
  id: string;
  seed_query: string | null;
  parsed_understanding: ParsedUnderstandingApi | null;
};

const DEFAULT_QUERY = "MCDM cok kriterli karar verme";

function buildAnchorQuery(project: ProjectReadApi | undefined): string {
  if (!project) return DEFAULT_QUERY;
  const focuses = project.parsed_understanding?.focuses ?? [];
  if (focuses.length > 0) {
    return focuses.join(" · ");
  }
  if (project.seed_query && project.seed_query.trim()) {
    return project.seed_query.trim();
  }
  return DEFAULT_QUERY;
}

async function fetchTopics(query: string): Promise<Top5Response> {
  return apiFetch<Top5Response>("/api/top5", {
    method: "POST",
    body: { query, k: 5, margin: 0.3, session_id: crypto.randomUUID() },
  });
}

export function TopicSuggestionPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const projectId = params?.id ?? "p1";

  // V1-S19-P007: gerçek proje çapasından konu sorgusu çıkar (parsed.focuses
  // > seed_query > DEFAULT). 'p1' demo path'inde DEFAULT_QUERY kalır.
  const projectQuery = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => apiFetch<ProjectReadApi>(`/api/project/${projectId}`),
    enabled: projectId !== "p1",
    retry: false,
    staleTime: 60_000,
  });
  const anchorQuery = buildAnchorQuery(projectQuery.data);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [query, setQuery] = useState(anchorQuery);
  const [activeQuery, setActiveQuery] = useState(anchorQuery);

  // Proje verisi sonradan geldiğinde input'u bir kez senkronla
  // (kullanıcı henüz manuel düzenleme yapmadıysa).
  useEffect(() => {
    if (projectQuery.data && query === DEFAULT_QUERY && activeQuery === DEFAULT_QUERY) {
      setQuery(anchorQuery);
      setActiveQuery(anchorQuery);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectQuery.data]);

  // F10-F8: konu lock CTA — selectedId varken alt sticky bar gosterir,
  // discovery-3 (Bibliyometrik panorama)'a gecirir. Backend lock endpoint
  // henuz yok (Phase 2: POST /api/project/{id}/topic/lock).
  const goLockTopic = () => {
    if (!selectedId) return;
    router.push(`/project/${projectId}/discovery-3`);
  };

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["top5-topics", activeQuery],
    queryFn: () => fetchTopics(activeQuery),
    staleTime: 900_000,
  });

  const papers = data?.papers ?? [];

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <AdvisorBanner message="Sana en ilgili 5 paper'i getirdim. Hangileri ilgini cekiyor, beraber inceleyelim — bu sonuclar sana ozel." />

      {/* Query bar */}
      <div className="flex gap-3">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") { setActiveQuery(query); } }}
          placeholder="Konu ara (orn. MCDM, bulanik mantik, ESG...)"
          className="flex-1 rounded-xl border border-stone-200 bg-white px-4 py-2.5 text-sm text-stone-700 placeholder:text-stone-400 focus:border-amber-400 focus:outline-none focus:ring-1 focus:ring-amber-300/30"
        />
        <button
          onClick={() => setActiveQuery(query)}
          disabled={isLoading}
          className="inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-medium text-white transition-colors hover:opacity-90 disabled:opacity-50"
          style={{ background: "linear-gradient(135deg, #E8A157 0%, #D4883A 100%)" }}
        >
          {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
          {isLoading ? "Aranıyor..." : "Ara"}
        </button>
      </div>

      {isError && (
        <div className="rounded-2xl border border-red-100 bg-red-50 p-4 text-sm text-red-600">
          Sonuclar yuklenemedi. Sunucu calisıyor mu?
        </div>
      )}

      {data?.needs_clarify && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-700">
          Sorgu daha spesifik olursa daha iyi sonuclar alabiliriz.
        </div>
      )}

      <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
        {isLoading && Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-48 animate-pulse rounded-2xl border border-stone-200 bg-stone-100" />
        ))}

        {papers.map((paper) => {
          const isSelected = selectedId === paper.paper_id;
          return (
            <div
              key={paper.paper_id}
              className="relative overflow-hidden rounded-2xl border border-stone-200 bg-white transition-all"
              style={{
                borderLeftWidth: isSelected ? 4 : 1,
                borderLeftColor: isSelected ? "#E8A157" : undefined,
                boxShadow: isSelected ? "0 2px 8px rgba(232,161,87,0.15)" : "0 1px 3px rgba(0,0,0,0.06)",
              }}
            >
              <div className="p-5">
                <div className="mb-3 flex items-start justify-between">
                  <h3 className="font-display text-[15px] font-semibold leading-snug text-stone-900">
                    {paper.title}
                  </h3>
                  {isSelected && (
                    <span
                      className="ml-2 inline-flex flex-shrink-0 items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium"
                      style={{ background: "#E8A15720", color: "#E8A157", border: "1px solid #E8A15740" }}
                    >
                      Secildi
                    </span>
                  )}
                </div>

                {paper.abstract_excerpt && (
                  <p className="mb-3 text-[13px] leading-relaxed text-stone-600 line-clamp-3">
                    {paper.abstract_excerpt}
                  </p>
                )}

                <div className="mb-3 flex flex-wrap gap-2 text-[11px] text-stone-400">
                  {paper.authors && <span>{paper.authors}</span>}
                  {paper.year && <span>· {paper.year}</span>}
                  <span className="font-mono">{paper.paper_id}</span>
                </div>

                <div className="mb-4">
                  <span
                    className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-[11px] font-medium"
                    style={{ background: "#E8A15712", color: "#B07A3A", border: "1px solid #E8A15730" }}
                  >
                    <Lock className="h-3 w-3" />
                    Konu bana kilitli
                  </span>
                </div>

                <div className="flex items-center gap-3">
                  <button
                    onClick={() => setSelectedId(paper.paper_id)}
                    className="inline-flex items-center gap-1.5 rounded-lg px-4 py-2 text-[13px] font-medium text-white transition-colors"
                    style={{ background: "linear-gradient(135deg, #E8A157 0%, #D4883A 100%)" }}
                  >
                    Bu paper'i sec
                    <ChevronRight className="h-3.5 w-3.5" />
                  </button>
                  <button className="inline-flex items-center gap-1.5 rounded-lg border border-stone-200 bg-white px-4 py-2 text-[13px] font-medium text-stone-600 transition-colors hover:bg-stone-50">
                    <Eye className="h-3.5 w-3.5" />
                    Detay gor
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {!isLoading && papers.length === 0 && !isError && (
        <div className="flex justify-center pt-2 text-sm text-stone-400">
          Sonuc bulunamadı.
        </div>
      )}

      {/* F10-F8: Konu lock CTA — selectedId varken aktif */}
      {selectedId && (
        <div
          className="sticky bottom-4 flex items-center justify-between gap-4 rounded-xl border bg-white p-4"
          style={{
            borderColor: "#E8A157",
            boxShadow: "0 4px 12px rgba(232,161,87,0.18)",
          }}
        >
          <div className="min-w-0">
            <div
              className="font-display text-stone-900"
              style={{ fontSize: 14.5, lineHeight: 1.3 }}
            >
              Bu makaleyi konu olarak kilitle
            </div>
            <p className="text-stone-500" style={{ fontSize: 12.5, marginTop: 2 }}>
              Onayla → Bibliyometrik panorama (havuzun nicel haritasi).
            </p>
          </div>
          <button
            type="button"
            onClick={goLockTopic}
            data-testid="lock-topic-btn"
            className="inline-flex flex-shrink-0 items-center gap-2 rounded-lg px-5 py-2.5 text-white transition hover:brightness-110"
            style={{
              background: "linear-gradient(135deg, #E8A157 0%, #D4883A 100%)",
              fontSize: 13.5,
            }}
          >
            <CheckCircle2 className="h-4 w-4" />
            Konuyu Kilitle ve Devam Et
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  );
}
