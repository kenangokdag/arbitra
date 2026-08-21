// F14 Hakemlik admin — iş durumu rozeti (insan cümlesi + statü rengi).

import { STATUS_LABELS, type JobStatus } from "@/lib/review-api";

const STATUS_TOKEN: Record<JobStatus, { color: string; pale: string }> = {
  queued: { color: "var(--color-ink-mute)", pale: "var(--color-bg-soft)" },
  parsing: { color: "var(--color-info)", pale: "var(--color-info-pale)" },
  checking_citations: {
    color: "var(--color-info)",
    pale: "var(--color-info-pale)",
  },
  checking_context: {
    color: "var(--color-info)",
    pale: "var(--color-info-pale)",
  },
  coverage: { color: "var(--color-info)", pale: "var(--color-info-pale)" },
  orchestrating: { color: "var(--color-info)", pale: "var(--color-info-pale)" },
  assembling: { color: "var(--color-info)", pale: "var(--color-info-pale)" },
  done: { color: "var(--color-ok)", pale: "var(--color-ok-pale)" },
  failed: { color: "var(--color-danger)", pale: "var(--color-danger-pale)" },
};

export function StatusPill({ status }: { status: JobStatus }) {
  const t = STATUS_TOKEN[status];
  return (
    <span
      className="inline-flex items-center rounded-sm px-2 py-0.5 text-[12px] font-medium"
      style={{ background: t.pale, color: t.color }}
    >
      {STATUS_LABELS[status]}
    </span>
  );
}
