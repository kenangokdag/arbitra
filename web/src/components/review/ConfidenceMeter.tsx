// Arbitra v2 — güven ölçer (yapısal kabuk).
// Güven tooltip'te SAKLANMAZ: sayısal + niteliksel (yüksek/orta/düşük) görünür.
// role="meter" + aria-valuenow ile ekran-okuyucuya da açık. Renk değeri
// --arb-confidence-* token SLOT'larından (premium palet: insan tasarım geçişi).

import { cn } from "@/lib/cn";

type Band = "high" | "medium" | "low";

type BandMeta = { className: string; token: string; label: string };

const BAND_META: Record<Band, BandMeta> = {
  high: { className: "arb-confidence-high", token: "var(--arb-confidence-high)", label: "Yüksek güven" },
  medium: { className: "arb-confidence-medium", token: "var(--arb-confidence-medium)", label: "Orta güven" },
  low: { className: "arb-confidence-low", token: "var(--arb-confidence-low)", label: "Düşük güven" },
};

function bandOf(value: number): Band {
  if (value >= 0.66) return "high";
  if (value >= 0.33) return "medium";
  return "low";
}

export type ConfidenceMeterProps = {
  value: number;
  label?: string;
  showNumeric?: boolean;
  className?: string;
};

export function ConfidenceMeter({
  value,
  label,
  showNumeric = true,
  className,
}: ConfidenceMeterProps) {
  const clamped = Math.min(1, Math.max(0, value));
  const band = bandOf(clamped);
  const meta = BAND_META[band];
  const percent = Math.round(clamped * 100);
  const valueText = `${meta.label}, %${percent}`;

  return (
    <div
      data-testid="confidence-meter"
      className={cn("arb-confidence-meter flex flex-col gap-1", meta.className, className)}
    >
      <div className="flex items-center justify-between gap-2 text-xs">
        <span className="text-[color:var(--color-ink-mute)]">{label ?? "Güven"}</span>
        <span className="flex items-center gap-1.5 font-medium" style={{ color: meta.token }}>
          <span>{meta.label}</span>
          {showNumeric ? (
            <span data-testid="confidence-numeric" className="tabular-nums">
              %{percent}
            </span>
          ) : null}
        </span>
      </div>
      <div
        role="meter"
        aria-label={label ?? "Güven"}
        aria-valuenow={clamped}
        aria-valuemin={0}
        aria-valuemax={1}
        aria-valuetext={valueText}
        className="h-1.5 w-full overflow-hidden rounded-full bg-[color:var(--color-bg-hover)]"
      >
        <div
          className="h-full rounded-full"
          style={{ width: `${percent}%`, background: meta.token }}
        />
      </div>
    </div>
  );
}
