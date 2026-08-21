// Arbitra v2 — düşürülmüş hizmet uyarısı (yapısal kabuk).
// Dürüstlük kuralı: bir aşama tam çalışmadıysa kullanıcıdan SAKLANMAZ; görünür
// bir sınırlama bandı ile söylenir. Renk tek sinyal değil; ikon + metin etiketi.

import { AlertTriangle } from "lucide-react";

import { cn } from "@/lib/cn";

export type DegradedNoticeProps = {
  reason: string;
  className?: string;
};

export function DegradedNotice({ reason, className }: DegradedNoticeProps) {
  return (
    <div
      data-testid="degraded-notice"
      role="status"
      className={cn(
        "flex items-start gap-2.5 rounded-md border border-[color:var(--color-warn)] bg-[color:var(--color-warn-pale)] px-3 py-2.5 text-sm text-[color:var(--color-warn)]",
        className,
      )}
    >
      <AlertTriangle aria-hidden className="mt-0.5 h-4 w-4 flex-shrink-0" />
      <div className="flex flex-col gap-0.5">
        <span className="font-medium">Sınırlı sonuç</span>
        <span className="text-[color:var(--color-ink-soft)]">{reason}</span>
      </div>
    </div>
  );
}
