// Arbitra v2 — aksiyon kartı (yapısal kabuk).
// Bir eleştiriyi revizyon adımına çevirir: öncelik / efor / beklenen kazanç /
// hedef bölüm / talimat / kabul kontrolü. Çıplak rozet değil; her alan etiketli.

import { cn } from "@/lib/cn";
import type { ActionItem, ActionPriority, EffortGain } from "@/lib/review-api";

// RAPOR_ONCELIKLI_DUZELTME_LISTESI_2026-08-16: export edildi — ReviewReportView'daki
// yeni öncelikli-liste bölümü grup başlıklarında AYNI etiket/renk setini reuse eder
// (yeni bir A/B/C taksonomisi icat edilmedi, Kenan kararı).
export const PRIORITY_LABEL: Record<ActionPriority, string> = {
  P0: "P0 · Önce bu",
  P1: "P1 · Sonra",
  P2: "P2 · İsteğe bağlı",
};

export const PRIORITY_TOKEN: Record<ActionPriority, string> = {
  P0: "var(--arb-risk-critical)",
  P1: "var(--arb-risk-major)",
  P2: "var(--arb-risk-moderate)",
};

const GAIN_LABEL: Record<EffortGain, string> = {
  low: "Düşük",
  medium: "Orta",
  high: "Yüksek",
};

export type ActionItemCardProps = {
  item: ActionItem;
  className?: string;
};

export function ActionItemCard({ item, className }: ActionItemCardProps) {
  return (
    <article
      data-testid="action-item-card"
      data-action-id={item.action_id}
      className={cn(
        "flex flex-col gap-3 rounded-lg border border-[color:var(--color-rule)] bg-[color:var(--color-bg-card)] p-4",
        className,
      )}
    >
      <header className="flex flex-wrap items-center gap-2">
        <span
          data-testid="action-priority"
          className="inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium"
          style={{ color: PRIORITY_TOKEN[item.priority], borderColor: PRIORITY_TOKEN[item.priority] }}
        >
          {PRIORITY_LABEL[item.priority]}
        </span>
        {item.target_section ? (
          <span className="text-xs text-[color:var(--color-ink-mute)]">
            Hedef bölüm: <span className="font-medium text-[color:var(--color-ink-soft)]">{item.target_section}</span>
          </span>
        ) : null}
      </header>

      <p className="text-sm leading-relaxed text-[color:var(--color-ink)]">{item.instruction}</p>

      <dl className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-[color:var(--color-ink-mute)]">
        <div className="flex items-center gap-1.5">
          <dt>Efor:</dt>
          <dd className="font-medium text-[color:var(--color-ink-soft)]">{GAIN_LABEL[item.effort]}</dd>
        </div>
        <div className="flex items-center gap-1.5">
          <dt>Beklenen kazanç:</dt>
          <dd className="font-medium text-[color:var(--color-ink-soft)]">{GAIN_LABEL[item.expected_gain]}</dd>
        </div>
      </dl>

      {item.acceptance_check ? (
        <div className="rounded-md bg-[color:var(--color-bg-soft)] p-2.5 text-xs text-[color:var(--color-ink-soft)]">
          <span className="font-medium text-[color:var(--color-ink-mute)]">Kabul kontrolü: </span>
          {item.acceptance_check}
        </div>
      ) : null}
    </article>
  );
}
