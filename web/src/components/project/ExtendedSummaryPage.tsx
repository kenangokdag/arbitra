"use client";

import { useSearchParams } from "next/navigation";
import { Download, Copy, BookOpen, Ghost, Loader2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { AdvisorBanner } from "@/components/project/AdvisorBanner";
import { apiFetch } from "@/lib/api";

interface SummarizeAccepted { task_id: string; status: string; }
interface SummaryDoc { paper_id: string; mode: string; language: string; text: string; citations: string[]; }

async function fetchDeepSummary(paperId: string, language = "tr"): Promise<SummaryDoc> {
  const accepted = await apiFetch<SummarizeAccepted>("/api/summarize", {
    method: "POST",
    body: { paper_id: paperId, mode: "deep", language },
  });
  return apiFetch<SummaryDoc>(`/api/summarize/${accepted.task_id}`);
}

export function ExtendedSummaryPage() {
  const params = useSearchParams();
  const paperId = params.get("paper_id") ?? "";

  const { data, isLoading, isError } = useQuery({
    queryKey: ["summarize-deep", paperId],
    queryFn: () => fetchDeepSummary(paperId),
    enabled: !!paperId,
    staleTime: 1800_000,
  });

  const paragraphs = (data?.text ?? "").split(/\n{2,}/).filter(Boolean);
  const citations = data?.citations ?? [];

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <AdvisorBanner message="Daha derin lazimsa 31.85M ghost paper'i da dahil ediyorum — kapsami genisletelim." />

      {!paperId && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6 text-center text-sm text-amber-700">
          Derin ozet almak icin bir paper secin (URL: ?paper_id=W...)
        </div>
      )}

      {paperId && (
        <div className="flex gap-6">
          {/* Left — Extended summary */}
          <div className="min-w-0 flex-1" style={{ maxWidth: "768px" }}>
            <div
              className="rounded-2xl border border-stone-200 bg-white p-8"
              style={{ boxShadow: "0 1px 3px rgba(0,0,0,0.06)" }}
            >
              <div className="mb-4 flex items-center justify-between">
                <h2 className="font-display text-lg font-semibold text-stone-800">
                  Genisletilmis Literatur Ozeti
                </h2>
                <span
                  className="inline-flex items-center gap-1 rounded-full px-3 py-1 text-[10px] font-medium"
                  style={{ background: "#E8A15715", color: "#E8A157", border: "1px solid #E8A15730" }}
                >
                  <BookOpen className="h-3 w-3" />
                  24.87M + 31.85M ghost paper havuzundan
                </span>
              </div>

              {isLoading && (
                <div className="flex items-center gap-2 text-sm text-stone-500">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Derin ozet hazirlanıyor...
                </div>
              )}

              {isError && (
                <p className="text-sm text-red-500">Ozet yuklenemedi. Paper ID gecerli mi?</p>
              )}

              {data && (
                <div className="space-y-5">
                  {paragraphs.map((para, i) => (
                    <p key={i} className="font-display text-base leading-[1.8] text-stone-700">
                      {para}
                    </p>
                  ))}
                </div>
              )}

              <div className="mt-8 flex gap-3 border-t border-stone-100 pt-5">
                <button
                  className="inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-medium text-white transition-colors hover:opacity-90"
                  style={{ background: "#E8A157" }}
                >
                  <Download className="h-4 w-4" />
                  PDF indir
                </button>
                <button className="inline-flex items-center gap-2 rounded-xl border border-stone-200 bg-white px-5 py-2.5 text-sm font-medium text-stone-600 transition-colors hover:bg-stone-50">
                  <Copy className="h-4 w-4" />
                  Deftere kopyala
                </button>
              </div>
            </div>
          </div>

          {/* Right — Citations with ghost marker */}
          <div className="w-[320px] flex-shrink-0">
            <div
              className="sticky top-6 rounded-2xl border border-stone-200 bg-white p-5"
              style={{ boxShadow: "0 1px 3px rgba(0,0,0,0.06)" }}
            >
              <h3 className="font-display mb-4 text-sm font-semibold text-stone-800">
                Kaynaklar ({citations.length})
              </h3>
              {citations.length === 0 && !isLoading && (
                <p className="text-xs text-stone-400">Atif listesi bekleniyor...</p>
              )}
              <div className="space-y-2">
                {citations.map((cid, i) => (
                  <div key={cid} className="rounded-lg border border-stone-100 bg-stone-50 p-2.5">
                    <div className="flex items-start gap-2">
                      <span className="mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-md bg-stone-300 text-[10px] font-bold text-white">
                        {i + 1}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="font-mono text-[11px] text-stone-500">{cid}</p>
                        {!cid.startsWith("W") && (
                          <span className="mt-0.5 inline-flex items-center gap-1 text-[10px] text-stone-400">
                            <Ghost className="h-2.5 w-2.5" /> Ghost kaynak
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
