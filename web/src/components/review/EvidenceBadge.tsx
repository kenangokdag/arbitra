// Arbitra v2 — kanıt destek seviyesi rozeti (yapısal kabuk).
// Dürüstlük kuralı: abstract_only / unresolved, full_text_verified'tan GÖRSEL
// olarak ayrı olmalı (farklı class + farklı metin) — kullanıcı "doğrulandı" ile
// "yalnızca özet"i karıştırmaz. Renk tek sinyal değil; metin etiketi zorunlu.
// Renk değeri --arb-evidence-* token SLOT'larından (premium palet: insan geçişi).

import { BadgeCheck, FileText, HelpCircle, Info, XCircle, Ban } from "lucide-react";

import { cn } from "@/lib/cn";
import type { SupportLevel } from "@/lib/review-api";

type SupportMeta = {
  className: string;
  token: string;
  label: string;
  Icon: typeof BadgeCheck;
};

const SUPPORT_META: Record<SupportLevel, SupportMeta> = {
  full_text_verified: {
    className: "arb-evidence-verified",
    token: "var(--arb-evidence-verified)",
    label: "Tam metin doğrulandı",
    Icon: BadgeCheck,
  },
  abstract_only: {
    className: "arb-evidence-abstract",
    token: "var(--arb-evidence-abstract)",
    label: "Yalnızca özetten",
    Icon: FileText,
  },
  metadata_only: {
    className: "arb-evidence-metadata",
    token: "var(--arb-evidence-metadata)",
    label: "Yalnızca künyeden",
    Icon: Info,
  },
  unresolved: {
    className: "arb-evidence-unresolved",
    token: "var(--arb-evidence-unresolved)",
    label: "Doğrulanamadı",
    Icon: HelpCircle,
  },
  contradictory: {
    className: "arb-evidence-contradictory",
    token: "var(--color-danger)",
    label: "Çelişkili kanıt",
    Icon: XCircle,
  },
  not_applicable: {
    className: "arb-evidence-na",
    token: "var(--color-ink-faint)",
    label: "Uygulanmaz",
    Icon: Ban,
  },
};

export type EvidenceBadgeProps = {
  supportLevel: SupportLevel;
  className?: string;
};

export function EvidenceBadge({ supportLevel, className }: EvidenceBadgeProps) {
  const meta = SUPPORT_META[supportLevel];
  const Icon = meta.Icon;

  return (
    <span
      data-testid="evidence-badge"
      data-support-level={supportLevel}
      className={cn(
        "arb-evidence-badge",
        meta.className,
        "inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs font-medium",
        className,
      )}
      style={{ color: meta.token, borderColor: meta.token }}
    >
      <Icon aria-hidden className="h-3.5 w-3.5 flex-shrink-0" />
      <span>{meta.label}</span>
    </span>
  );
}
