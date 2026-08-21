// F14 Hakemlik admin — özet istatistik. Sade stat kartları (BI-dashboard değil,
// sakin enstrüman; rakam yanında etiket — çıplak rakam yok).

"use client";

import Link from "next/link";
import { AlertTriangle, CheckCircle2, Layers, Loader2 } from "lucide-react";

import { useAdminStats } from "@/hooks/useReview";

export default function AdminStatsPage() {
  const { data, isPending, isError, error, refetch } = useAdminStats();

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1.5">
        <h1 className="serif text-[28px] font-medium italic leading-tight tracking-[-0.015em]">
          İstatistik
        </h1>
        <p className="text-[14px] text-ink-mute">
          ARBITRA hakemlik işlerinin özet durumu. 5 saniyede bir yenilenir.
        </p>
      </header>

      {isError ? (
        <ErrorBox message={error.message} onRetry={() => refetch()} />
      ) : isPending ? (
        <LoadingBox />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            label="Toplam iş"
            value={data.total}
            icon={<Layers className="h-4 w-4" aria-hidden />}
            color="var(--color-ink-mute)"
          />
          <StatCard
            label="Tamamlandı"
            value={data.done}
            icon={<CheckCircle2 className="h-4 w-4" aria-hidden />}
            color="var(--color-ok)"
          />
          <StatCard
            label="Sürüyor"
            value={data.in_progress}
            icon={<Loader2 className="h-4 w-4" aria-hidden />}
            color="var(--color-info)"
          />
          <StatCard
            label="Başarısız"
            value={data.failed}
            icon={<AlertTriangle className="h-4 w-4" aria-hidden />}
            color="var(--color-danger)"
          />
        </div>
      )}

      <Link
        href="/admin/jobs"
        className="w-fit text-[13px] text-accent no-underline transition-opacity hover:opacity-80"
      >
        Tüm işleri gör →
      </Link>
    </div>
  );
}

function StatCard({
  label,
  value,
  icon,
  color,
}: {
  label: string;
  value: number;
  icon: React.ReactNode;
  color: string;
}) {
  return (
    <div className="flex flex-col gap-2 rounded-md border border-rule bg-bg-card px-4 py-4 shadow-sm">
      <span className="flex items-center gap-1.5" style={{ color }}>
        {icon}
        <span className="text-[12px] font-medium uppercase tracking-wider text-ink-mute">
          {label}
        </span>
      </span>
      <span className="font-mono-pmid text-[28px] font-medium tabular-nums text-ink">
        {value}
      </span>
    </div>
  );
}

function LoadingBox() {
  return (
    <div
      role="status"
      className="flex items-center justify-center gap-2 rounded-md border border-rule bg-bg-card px-6 py-12 text-ink-mute"
    >
      <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
      <span className="text-[13px]">Yükleniyor…</span>
    </div>
  );
}

function ErrorBox({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div
      role="alert"
      className="flex flex-col items-start gap-2 rounded-md border px-4 py-4"
      style={{
        borderColor: "var(--color-danger)",
        background: "var(--color-danger-pale)",
      }}
    >
      <p className="text-[14px] font-medium" style={{ color: "var(--color-danger)" }}>
        İstatistik alınamadı
      </p>
      <p className="text-[13px] text-ink-mute">{message}</p>
      <button
        type="button"
        onClick={onRetry}
        className="mt-1 rounded-sm border px-3 py-1 text-[13px] font-medium"
        style={{
          borderColor: "var(--color-danger)",
          color: "var(--color-danger)",
        }}
      >
        Tekrar dene
      </button>
    </div>
  );
}
