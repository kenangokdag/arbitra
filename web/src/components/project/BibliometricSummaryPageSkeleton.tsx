"use client";

// V1-S13 P004: BibliometricSummaryPage iskelet bileseni.
// Plan: docs/plans/V1_S13_demo_path_polish.md §2.3 + §4 P004.
// Phase 2 backend bagliligi geldiginde useQuery({isLoading}) ile tetiklenir;
// simdi ayri export, gercek sayfayla otomatik bagli DEGIL (KD-V1-S13-04).

import { motion, useReducedMotion, type Variants } from "motion/react";

import { cn } from "@/lib/cn";

const shimmerVariants: Variants = {
  initial: { backgroundPosition: "200% 0" },
  animate: {
    backgroundPosition: "-200% 0",
    transition: { duration: 1.6, repeat: Infinity, ease: "linear" },
  },
};

function ShimmerBox({ className, style }: { className?: string; style?: React.CSSProperties }) {
  const reduce = useReducedMotion();
  const baseStyle: React.CSSProperties = reduce
    ? { background: "var(--color-bg-soft)" }
    : {
        background:
          "linear-gradient(90deg, var(--color-bg-soft) 0%, var(--color-rule) 50%, var(--color-bg-soft) 100%)",
        backgroundSize: "200% 100%",
      };
  return (
    <motion.div
      className={cn("rounded", className)}
      variants={reduce ? undefined : shimmerVariants}
      initial={reduce ? undefined : "initial"}
      animate={reduce ? undefined : "animate"}
      style={{ ...baseStyle, ...style }}
      aria-hidden
    />
  );
}

function MetricCardSkeleton() {
  return (
    <div
      className="rounded-xl p-4"
      style={{
        background: "var(--color-bg-card)",
        border: "1px solid var(--color-rule)",
      }}
    >
      <ShimmerBox className="mb-3 h-3 w-20" />
      <ShimmerBox className="h-7 w-16" />
      <ShimmerBox className="mt-2 h-3 w-28" />
    </div>
  );
}

function ChartCardSkeleton({ height = 128, withBars = false }: { height?: number; withBars?: boolean }) {
  return (
    <section
      className="rounded-xl p-5"
      style={{
        background: "var(--color-bg-card)",
        border: "1px solid var(--color-rule)",
      }}
    >
      <ShimmerBox className="mb-2 h-4 w-40" />
      <ShimmerBox className="mb-4 h-3 w-56" />
      {withBars ? (
        <div className="flex items-end gap-1.5" style={{ height }}>
          {Array.from({ length: 16 }).map((_, i) => (
            <ShimmerBox
              key={i}
              className="flex-1"
              style={{ height: `${30 + ((i * 13) % 70)}%` }}
            />
          ))}
        </div>
      ) : (
        <div className="space-y-2.5">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="space-y-1">
              <ShimmerBox className="h-3 w-32" />
              <ShimmerBox className="h-1.5 w-full" />
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function TopBarListSkeleton() {
  return (
    <section
      className="rounded-xl p-5"
      style={{
        background: "var(--color-bg-card)",
        border: "1px solid var(--color-rule)",
      }}
    >
      <ShimmerBox className="mb-3 h-4 w-32" />
      <ol className="space-y-2">
        {Array.from({ length: 10 }).map((_, i) => (
          <li key={i} className="flex items-center gap-3">
            <ShimmerBox className="h-3 w-4" />
            <div className="flex-1">
              <div className="flex justify-between gap-2">
                <ShimmerBox className="h-3" style={{ width: `${40 + ((i * 7) % 40)}%` }} />
                <ShimmerBox className="h-3 w-16" />
              </div>
              <ShimmerBox className="mt-1 h-1 w-full" />
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

export function BibliometricSummaryPageSkeleton() {
  return (
    <div data-zone="discovery" className="space-y-6" aria-busy aria-label="Bibliyometrik panorama yukleniyor">
      {/* Header */}
      <header className="space-y-2">
        <ShimmerBox className="h-3 w-24" />
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 space-y-2">
            <ShimmerBox className="h-7 w-72" />
            <ShimmerBox className="h-4 w-96" />
          </div>
          <ShimmerBox className="h-7 w-28 rounded-full" />
        </div>
      </header>

      {/* Block 1 — 4 metric cards */}
      <section className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <MetricCardSkeleton key={i} />
        ))}
      </section>

      {/* Block 2 — Year distribution */}
      <ChartCardSkeleton withBars />

      {/* Block 3 + 4 — Lang + Lotka grid */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <ChartCardSkeleton />
        <ChartCardSkeleton withBars height={128} />
      </div>

      {/* Block 5 — Top-10 grid */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <TopBarListSkeleton />
        <TopBarListSkeleton />
      </div>
    </div>
  );
}
