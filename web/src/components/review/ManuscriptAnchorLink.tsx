// Arbitra v2 — metin çıpası bağlantısı (yapısal kabuk).
// Bulgu → makaledeki yere köprü. Buton, erişilebilir bir ada sahip (bölüm +
// alıntı önizleme); onOpen ile drawer'ı açar. Klavye ile erişilebilir (button).

import { Quote } from "lucide-react";

import { cn } from "@/lib/cn";
import type { ManuscriptAnchor } from "@/lib/review-api";

export type ManuscriptAnchorLinkProps = {
  anchor: ManuscriptAnchor;
  onOpen?: () => void;
  className?: string;
};

export function ManuscriptAnchorLink({ anchor, onOpen, className }: ManuscriptAnchorLinkProps) {
  const sectionLabel = anchor.section ?? "Makale";
  const quote = anchor.quote?.trim();
  const preview = quote && quote.length > 80 ? `${quote.slice(0, 80)}…` : quote;
  const accessibleName = preview
    ? `${sectionLabel} bölümüne git: ${preview}`
    : `${sectionLabel} bölümüne git`;

  return (
    <button
      type="button"
      data-testid="manuscript-anchor-link"
      data-anchor-id={anchor.anchor_id}
      onClick={onOpen}
      aria-label={accessibleName}
      className={cn(
        "group inline-flex max-w-full items-start gap-1.5 rounded-md border border-[color:var(--color-rule)] bg-[color:var(--color-bg-card)] px-2 py-1 text-left text-xs text-[color:var(--color-ink-soft)] transition-colors hover:border-[color:var(--color-accent)] hover:text-[color:var(--color-accent)]",
        className,
      )}
    >
      <Quote aria-hidden className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-[color:var(--color-ink-faint)]" />
      <span className="flex flex-col">
        <span className="font-medium">{sectionLabel}</span>
        {preview ? (
          <span className="truncate text-[color:var(--color-ink-mute)]">{preview}</span>
        ) : null}
      </span>
    </button>
  );
}
