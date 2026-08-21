"use client";

// V1-S13 P005: veri kaynagi pili + Base UI Popover (openOnHover).
// Plan: docs/plans/V1_S13_demo_path_polish.md §2.4 + KD-V1-S13-05.
//
// Reusable: ChartCard / DataVizCard / herhangi bir veri yuzeyi sag-ust kosesinde
// kullanilabilir. Her gostergenin kaynak/orneklem/hesaplama/guncellik/kanit
// seviyesini tek pill icinde acar — akademik epistemik sinyal (Yol C).

import { Info } from "lucide-react";
import { Popover } from "@base-ui/react/popover";

export type DataConfidence = "A" | "B" | "C";

export interface DataProvenanceProps {
  /** "warehouse aggregate", "Pinecone metadata", "synthetic mock", vb. */
  source: string;
  /** Orneklem buyuklugu */
  n: number;
  /** Eksik veri sayisi (0 ise pill'de gorunmez) */
  missing?: number;
  /** 1-2 cumle hesaplama ozeti */
  method: string;
  /** ISO tarih ya da gun ay yil string'i */
  updatedAt: string;
  /** A = warehouse aggregate · B = cached · C = estimate / synthetic */
  confidence: DataConfidence;
}

const CONFIDENCE_TONE: Record<DataConfidence, { fg: string; bg: string; label: string; desc: string }> = {
  A: {
    fg: "#047857", // emerald-700
    bg: "rgba(16, 185, 129, 0.08)",
    label: "Birincil kaynak",
    desc: "Warehouse aggregate — canli SQL hesabi, dogrudan birincil kaynaktan turetildi.",
  },
  B: {
    fg: "#B45309", // amber-700
    bg: "rgba(217, 119, 6, 0.10)",
    label: "Onbellek",
    desc: "Onbellekten okundu (Pinecone metadata / ghost-card). Birincil kaynak ile kuçuk gecikme olabilir.",
  },
  C: {
    fg: "#C2410C", // orange-700
    bg: "rgba(234, 88, 12, 0.10)",
    label: "Tahmin",
    desc: "Sentetik / tahmini deger (mock fixture). Bilimsel karar icin birincil kaynak dogrulamasi sart.",
  },
};

export function DataProvenance({
  source,
  n,
  missing,
  method,
  updatedAt,
  confidence,
}: DataProvenanceProps) {
  const tone = CONFIDENCE_TONE[confidence];

  return (
    <Popover.Root>
      <Popover.Trigger
        openOnHover
        delay={120}
        closeDelay={120}
        className="font-mono inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-wider transition-colors hover:bg-[var(--color-bg-soft)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 data-[popup-open]:bg-[var(--color-bg-soft)]"
        style={{
          borderColor: "var(--color-rule)",
          color: "var(--color-ink-faint)",
        }}
        aria-label={`Veri kaynagi: ${source}, N=${n}, kanit ${confidence}`}
      >
        <Info className="h-3 w-3" strokeWidth={1.6} />
        <span>N={n}</span>
        <span style={{ color: tone.fg }}>·</span>
        <span style={{ color: tone.fg, fontWeight: 600 }}>{confidence}</span>
      </Popover.Trigger>

      <Popover.Portal>
        <Popover.Positioner sideOffset={8} side="bottom" align="end">
          <Popover.Popup
            className="data-[ending-style]:opacity-0 data-[starting-style]:opacity-0 transition-opacity"
            style={{
              background: "var(--color-bg-card)",
              border: "1px solid var(--color-rule)",
              borderRadius: 10,
              boxShadow: "0 8px 24px -8px rgba(15, 23, 42, 0.18), 0 2px 6px -2px rgba(15, 23, 42, 0.10)",
              padding: "12px 14px",
              maxWidth: 320,
              minWidth: 260,
              fontSize: 12,
              color: "var(--color-ink)",
              lineHeight: 1.5,
            }}
          >
            <Popover.Title
              className="font-mono uppercase"
              style={{
                fontSize: 9.5,
                letterSpacing: "0.08em",
                color: "var(--color-ink-faint)",
                marginBottom: 8,
              }}
            >
              Veri kaynagi
            </Popover.Title>

            <dl className="space-y-2">
              <ProvenanceRow label="Kaynak" value={source} />
              <ProvenanceRow
                label="Orneklem"
                value={
                  missing && missing > 0
                    ? `${n} kayit (${missing} eksik)`
                    : `${n} kayit`
                }
              />
              <ProvenanceRow label="Hesaplama" value={method} />
              <ProvenanceRow label="Guncellik" value={updatedAt} />
            </dl>

            <div
              className="mt-3 rounded px-2.5 py-2"
              style={{
                background: tone.bg,
                borderLeft: `2px solid ${tone.fg}`,
              }}
            >
              <div
                className="font-mono uppercase"
                style={{
                  fontSize: 9,
                  letterSpacing: "0.08em",
                  color: tone.fg,
                  fontWeight: 700,
                }}
              >
                Kanit · {confidence} · {tone.label}
              </div>
              <p style={{ fontSize: 11.5, color: "var(--color-ink-mute)", marginTop: 3, lineHeight: 1.4 }}>
                {tone.desc}
              </p>
            </div>
          </Popover.Popup>
        </Popover.Positioner>
      </Popover.Portal>
    </Popover.Root>
  );
}

function ProvenanceRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-[80px_1fr] gap-2">
      <dt
        className="font-mono uppercase"
        style={{
          fontSize: 9,
          letterSpacing: "0.06em",
          color: "var(--color-ink-faint)",
          paddingTop: 1,
        }}
      >
        {label}
      </dt>
      <dd style={{ fontSize: 12, color: "var(--color-ink)" }}>{value}</dd>
    </div>
  );
}
