"use client";

// V1-S14 P006: 6 fixture sabit canlı backend ile değiştirildi
// (POST /api/project/{id}/bibliometrics, B-029).
// Metric set warehouse'a hizalı: TOP_VENUES→TOP_AREAS (fact_paper_field),
// TOP_AUTHORS+LOTKA_BINS→TOP_METHODS (fact_paper_sentence_role.dominant_role),
// mostCited.title→PMID-{pmid} placeholder (papers.title boş, lazy-fill V2).

import { TrendingUp, FileText, Users, BookOpen } from "lucide-react";
import { motion, useReducedMotion, type Variants } from "motion/react";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";

import { AdvisorBanner } from "@/components/project/AdvisorBanner";
import { apiFetch } from "@/lib/api";
import { DataProvenance, type DataProvenanceProps } from "./DataProvenance";
import { BibliometricSummaryPageSkeleton } from "./BibliometricSummaryPageSkeleton";

type MostCited = { paper_id: string; pmid: string | null; citations: number };
type YearCount = { year: number; count: number };
type LangCount = { code: string; count: number };
type NamedCount = { name: string; count: number };

// N-13: backend BibliometricConfidence — metrik-bazlı kanıt seviyesi.
type BibliometricConfidence = {
  card_metrics: "A" | "C";
  beauty_metrics: "A" | "C";
  top_areas: "A" | "C";
  top_methods: "A" | "C";
};

type BibliometricSummary = {
  total_papers: number;
  median_year: number | null;
  mean_citations: number;
  most_cited: MostCited | null;
  publications_by_year: YearCount[];
  language_dist: LangCount[];
  top_areas: NamedCount[];
  top_methods: NamedCount[];
  confidence: BibliometricConfidence;
};

const containerVariants: Variants = {
  hidden: { opacity: 1 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.08, delayChildren: 0.04 },
  },
};

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 4 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.24, ease: [0.16, 1, 0.3, 1] },
  },
};

const LANG_LABEL: Record<string, string> = {
  en: "Ingilizce",
  tr: "Turkce",
  id: "Endonezce",
  unknown: "Bilinmiyor",
};

const LANG_TONE: Record<string, string> = {
  en: "#0E4F4A",
  tr: "#E8A157",
  id: "#A855F7",
  unknown: "#94a3b8",
};

function langTone(code: string): string {
  return LANG_TONE[code.toLowerCase()] ?? "#64748b";
}

function langLabel(code: string): string {
  return LANG_LABEL[code.toLowerCase()] ?? code.toUpperCase();
}

export function BibliometricSummaryPage() {
  const reduceMotion = useReducedMotion();
  const initial = reduceMotion ? "visible" : "hidden";
  const params = useParams<{ id: string }>();
  const projectId = params?.id ?? "";

  const summaryQuery = useQuery<BibliometricSummary>({
    queryKey: ["bibliometrics", projectId],
    queryFn: () =>
      apiFetch<BibliometricSummary>(
        `/api/project/${projectId}/bibliometrics`,
        { method: "POST", body: { paper_ids: [] } }
      ),
    enabled: projectId.length > 0,
    retry: false,
    staleTime: 60_000,
  });

  if (summaryQuery.isLoading) {
    return <BibliometricSummaryPageSkeleton />;
  }

  if (summaryQuery.isError) {
    return (
      <div
        className="rounded-md p-4"
        style={{
          background: "var(--color-bg-soft)",
          border: "1px solid var(--color-rule)",
          fontSize: 13,
          color: "var(--color-ink-mute)",
        }}
      >
        Bibliyometrik veri yuklenemedi. Lutfen tekrar deneyin.
      </div>
    );
  }

  const data = summaryQuery.data;
  const total = data?.total_papers ?? 0;
  const yearDist = data?.publications_by_year ?? [];
  const langDist = data?.language_dist ?? [];
  const topAreas = data?.top_areas ?? [];
  const topMethods = data?.top_methods ?? [];
  const mostCited = data?.most_cited;
  const totalLang = langDist.reduce((acc, l) => acc + l.count, 0);
  // N-13: backend metrik-bazlı confidence (warehouse aggregate var mı?).
  const conf = data?.confidence ?? {
    card_metrics: "C" as const,
    beauty_metrics: "C" as const,
    top_areas: "C" as const,
    top_methods: "C" as const,
  };

  return (
    <motion.div
      data-zone="discovery"
      className="space-y-6"
      variants={containerVariants}
      initial={initial}
      animate="visible"
    >
      <motion.header variants={itemVariants} className="space-y-2">
        <div
          className="font-mono uppercase"
          style={{
            fontSize: 10,
            letterSpacing: "0.12em",
            color: "var(--color-ink-faint, #64748b)",
          }}
        >
          Kesif · 1.3
        </div>
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1">
            <h1
              className="font-display italic"
              style={{ fontSize: 28, color: "var(--color-ink)", lineHeight: 1.2 }}
            >
              Bibliyometrik panorama
            </h1>
            <p style={{ fontSize: 14.5, color: "var(--color-ink-mute)", lineHeight: 1.5 }}>
              Konunla ilgili {total} makalenin niceliksel ozeti — yil, dil, alan, yontem.
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
            Havuz · N={total}
          </span>
        </div>
      </motion.header>

      <motion.div variants={itemVariants}>
        <AdvisorBanner
          zone="discovery"
          message="Iste konunun nicel haritasi: kim yaziyor, ne zaman, hangi alanda, hangi yontemle."
        />
      </motion.div>

      {/* Block 1 — Top metric cards */}
      <motion.section
        variants={itemVariants}
        aria-label="Top metrikler"
        className="grid grid-cols-2 gap-3 md:grid-cols-4"
      >
        <MetricCard
          icon={FileText}
          label="Toplam makale"
          value={total.toString()}
          sub="havuz buyuklugu"
          provenance={{
            source: "warehouse · project_seed_papers",
            n: total,
            method: "Proje seed havuzundaki paper_id sayisi.",
            confidence: conf.card_metrics,
            updatedAt: "live",
          }}
        />
        <MetricCard
          icon={TrendingUp}
          label="Medyan yil"
          value={data?.median_year != null ? data.median_year.toString() : "—"}
          sub="yayin merkezi"
          provenance={{
            source: "warehouse · fact_paper_id_card.year",
            n: total,
            method: "Yayin yili medyani (Python statistics.median).",
            confidence: conf.card_metrics,
            updatedAt: "live",
          }}
        />
        <MetricCard
          icon={Users}
          label="Ortalama atif"
          value={data ? data.mean_citations.toFixed(1) : "—"}
          sub="paper basina"
          provenance={{
            source: "warehouse · fact_paper_beauty.total_cites",
            n: total,
            method: "AVG(total_cites) — havuzda paper basina aritmetik ortalama.",
            confidence: conf.beauty_metrics,
            updatedAt: "live",
          }}
        />
        <MetricCard
          icon={BookOpen}
          label="En cok atiflanan"
          value={mostCited ? mostCited.citations.toString() : "—"}
          sub={
            mostCited ? `PMID-${mostCited.pmid ?? mostCited.paper_id}` : "veri yok"
          }
          subTruncate
          provenance={{
            source:
              "warehouse · fact_paper_beauty ORDER BY total_cites DESC LIMIT 1",
            n: total,
            method:
              "En yuksek total_cites'a sahip tek paper. Title V2'de papers tablosundan lazy-fill.",
            confidence: conf.beauty_metrics,
            updatedAt: "live",
          }}
        />
      </motion.section>

      {/* Block 2 — Year distribution */}
      <motion.div variants={itemVariants}>
        <ChartCard
          title="Yil dagilimi"
          subtitle={
            yearDist.length > 0
              ? `${yearDist[0]!.year}-${yearDist[yearDist.length - 1]!.year}`
              : "veri yok"
          }
          provenance={{
            source: "warehouse · fact_paper_id_card.year",
            n: total,
            method: "GROUP BY year, COUNT(*) (Python aggregation).",
            confidence: conf.card_metrics,
            updatedAt: "live",
          }}
        >
          {yearDist.length === 0 ? (
            <EmptyState />
          ) : (
            <div className="flex h-32 items-end gap-1.5">
              {yearDist.map((y) => {
                const max = Math.max(...yearDist.map((x) => x.count), 1);
                const h = Math.round((y.count / max) * 100);
                return (
                  <div key={y.year} className="flex flex-1 flex-col items-center gap-1">
                    <motion.div
                      title={`${y.year}: ${y.count} makale`}
                      initial={{ opacity: 0.75 }}
                      whileHover={reduceMotion ? undefined : { opacity: 1, scaleY: 1.04 }}
                      transition={{ duration: 0.12 }}
                      style={{
                        width: "100%",
                        height: `${h}%`,
                        background: "var(--color-accent)",
                        borderRadius: "3px 3px 0 0",
                        transformOrigin: "bottom",
                      }}
                    />
                    <span
                      className="font-mono"
                      style={{ fontSize: 9, color: "var(--color-ink-faint)" }}
                    >
                      {y.year % 100}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </ChartCard>
      </motion.div>

      {/* Block 3 + 4 — Language donut + Top methods */}
      <motion.div variants={itemVariants} className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <ChartCard
          title="Dil dagilimi"
          subtitle="ISO 639-1 dil kodu"
          provenance={{
            source: "warehouse · fact_paper_id_card.language",
            n: total,
            method: "Dil koduna gore yuzde dagilimi.",
            confidence: conf.card_metrics,
            updatedAt: "live",
          }}
        >
          {langDist.length === 0 ? (
            <EmptyState />
          ) : (
            <div className="space-y-2.5">
              {langDist.map((l) => {
                const pct = totalLang > 0 ? Math.round((l.count / totalLang) * 100) : 0;
                return (
                  <div key={l.code} className="space-y-1">
                    <div className="flex justify-between" style={{ fontSize: 12.5 }}>
                      <span style={{ color: "var(--color-ink)" }}>
                        <span className="font-mono">{l.code.toUpperCase()}</span> ·{" "}
                        {langLabel(l.code)}
                      </span>
                      <span
                        className="font-mono"
                        style={{ color: "var(--color-ink-faint)" }}
                      >
                        %{pct}
                      </span>
                    </div>
                    <div
                      style={{
                        width: "100%",
                        height: 6,
                        background: "var(--color-bg-soft)",
                        borderRadius: 3,
                        overflow: "hidden",
                      }}
                    >
                      <div
                        style={{
                          width: `${pct}%`,
                          height: "100%",
                          background: langTone(l.code),
                          borderRadius: 3,
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </ChartCard>

        <TopBarList
          title="Yontem dagilimi"
          items={topMethods}
          unitLabel="makale"
          provenance={{
            source: "warehouse · fact_paper_sentence_role.dominant_role",
            n: total,
            method:
              "Cumle rol siniflamasinin baskin etiketi (METHOD/RESULT/...) GROUP BY.",
            confidence: conf.top_methods,
            updatedAt: "live",
          }}
        />
      </motion.div>

      {/* Block 5 — Top areas */}
      <motion.div variants={itemVariants}>
        <TopBarList
          title="Top alan"
          items={topAreas}
          unitLabel="makale"
          provenance={{
            source: "warehouse · fact_paper_field.primary_field + dim_field.name_en",
            n: total,
            method:
              "Birincil alana gore COUNT(*), DESC sirali ilk 10. dim_field name_en JOIN.",
            confidence: conf.top_areas,
            updatedAt: "live",
          }}
        />
      </motion.div>
    </motion.div>
  );
}

// ── Helpers ──────────────────────────────────────────────────────────────

function EmptyState() {
  return (
    <div
      style={{
        fontSize: 12.5,
        color: "var(--color-ink-faint)",
        padding: "8px 0",
      }}
    >
      Bu havuzda yeterli veri yok.
    </div>
  );
}

function MetricCard({
  icon: Icon,
  label,
  value,
  sub,
  subTruncate = false,
  provenance,
}: {
  icon: typeof FileText;
  label: string;
  value: string;
  sub: string;
  subTruncate?: boolean;
  provenance?: DataProvenanceProps;
}) {
  return (
    <div
      className="rounded-xl p-4"
      style={{
        background: "var(--color-bg-card)",
        border: "1px solid var(--color-rule)",
      }}
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <Icon className="h-4 w-4 shrink-0" style={{ color: "var(--color-ink-mute)" }} strokeWidth={1.6} />
          <span
            className="font-mono uppercase truncate"
            style={{ fontSize: 9.5, letterSpacing: "0.08em", color: "var(--color-ink-faint)" }}
          >
            {label}
          </span>
        </div>
        {provenance && <DataProvenance {...provenance} />}
      </div>
      <div
        className="font-display"
        style={{ fontSize: 26, color: "var(--color-ink)", lineHeight: 1.1 }}
      >
        {value}
      </div>
      <div
        className={subTruncate ? "truncate" : ""}
        style={{
          fontSize: 11.5,
          color: "var(--color-ink-mute)",
          marginTop: 4,
          lineHeight: 1.35,
        }}
        title={subTruncate ? sub : undefined}
      >
        {sub}
      </div>
    </div>
  );
}

function ChartCard({
  title,
  subtitle,
  provenance,
  children,
}: {
  title: string;
  subtitle?: string;
  provenance?: DataProvenanceProps;
  children: React.ReactNode;
}) {
  return (
    <section
      className="rounded-xl p-5"
      style={{
        background: "var(--color-bg-card)",
        border: "1px solid var(--color-rule)",
      }}
    >
      <header className="mb-3 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h2
            className="font-display"
            style={{ fontSize: 16, color: "var(--color-ink)", lineHeight: 1.2 }}
          >
            {title}
          </h2>
          {subtitle && (
            <p style={{ fontSize: 12.5, color: "var(--color-ink-mute)", marginTop: 2 }}>
              {subtitle}
            </p>
          )}
        </div>
        {provenance && <DataProvenance {...provenance} />}
      </header>
      {children}
    </section>
  );
}

function TopBarList({
  title,
  items,
  unitLabel,
  provenance,
}: {
  title: string;
  items: { name: string; count: number }[];
  unitLabel: string;
  provenance?: DataProvenanceProps;
}) {
  if (items.length === 0) {
    return (
      <ChartCard title={title} provenance={provenance}>
        <EmptyState />
      </ChartCard>
    );
  }
  const max = Math.max(...items.map((i) => i.count), 1);
  return (
    <ChartCard title={title} provenance={provenance}>
      <ol className="space-y-1.5">
        {items.map((it, idx) => {
          const w = Math.round((it.count / max) * 100);
          return (
            <li
              key={`${title}-${idx}`}
              className="-mx-2 flex items-center gap-3 rounded px-2 py-0.5 transition-colors duration-150 hover:bg-[var(--color-bg-soft)]"
            >
              <span
                className="font-mono"
                style={{
                  fontSize: 10,
                  color: "var(--color-ink-faint)",
                  width: 18,
                  textAlign: "right",
                }}
              >
                {idx + 1}
              </span>
              <div className="min-w-0 flex-1">
                <div
                  className="flex items-center justify-between gap-2"
                  style={{ fontSize: 12.5 }}
                >
                  <span className="truncate" style={{ color: "var(--color-ink)" }} title={it.name}>
                    {it.name}
                  </span>
                  <span
                    className="font-mono whitespace-nowrap"
                    style={{ color: "var(--color-ink-faint)", fontSize: 11 }}
                  >
                    {it.count} {unitLabel}
                  </span>
                </div>
                <div
                  style={{
                    width: "100%",
                    height: 4,
                    background: "var(--color-bg-soft)",
                    borderRadius: 2,
                    marginTop: 4,
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      width: `${w}%`,
                      height: "100%",
                      background: "var(--color-accent)",
                      opacity: 0.75,
                      borderRadius: 2,
                    }}
                  />
                </div>
              </div>
            </li>
          );
        })}
      </ol>
    </ChartCard>
  );
}
