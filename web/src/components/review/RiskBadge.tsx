// Arbitra v2 — risk severity rozeti (yapısal kabuk).
// Renk TEK sinyal değil: her zaman metin etiketi + ikon taşır (a11y kuralı).
// Renk değeri --arb-risk-* token SLOT'larından gelir (premium palet sonra,
// insan tasarım geçişinde). class severity'ye göre değişir → görsel ayrım + test.

import { AlertOctagon, AlertTriangle, Info, MinusCircle } from "lucide-react";

import { cn } from "@/lib/cn";
import type { ActionPriority, SeverityV2 } from "@/lib/review-api";

type SeverityMeta = {
  className: string;
  token: string;
  label: string;
  Icon: typeof AlertOctagon;
};

const SEVERITY_META: Record<SeverityV2, SeverityMeta> = {
  critical: {
    className: "arb-risk-critical",
    token: "var(--arb-risk-critical)",
    label: "Kritik",
    Icon: AlertOctagon,
  },
  major: {
    className: "arb-risk-major",
    token: "var(--arb-risk-major)",
    label: "Önemli",
    Icon: AlertTriangle,
  },
  moderate: {
    className: "arb-risk-moderate",
    token: "var(--arb-risk-moderate)",
    label: "Orta",
    Icon: Info,
  },
  minor: {
    className: "arb-risk-minor",
    token: "var(--arb-risk-minor)",
    label: "Küçük",
    Icon: MinusCircle,
  },
  info: {
    className: "arb-risk-info",
    token: "var(--color-info)",
    label: "Bilgi",
    Icon: Info,
  },
};

export type RiskBadgeProps = {
  severity: SeverityV2;
  priority?: ActionPriority;
  label?: string;
  className?: string;
};

export function RiskBadge({ severity, priority, label, className }: RiskBadgeProps) {
  const meta = SEVERITY_META[severity];
  const text = label ?? meta.label;
  const Icon = meta.Icon;

  return (
    <span
      data-testid="risk-badge"
      data-severity={severity}
      className={cn(
        "arb-risk-badge",
        meta.className,
        "inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs font-medium",
        className,
      )}
      style={{ color: meta.token, borderColor: meta.token }}
    >
      <Icon aria-hidden className="h-3.5 w-3.5 flex-shrink-0" />
      <span>{text}</span>
      {priority ? (
        <span
          data-testid="risk-badge-priority"
          className="rounded-sm border border-current px-1 text-[10px] leading-4 tracking-wide"
        >
          {priority}
        </span>
      ) : null}
    </span>
  );
}
