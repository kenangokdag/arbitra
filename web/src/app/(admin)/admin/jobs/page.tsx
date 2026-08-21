// F14 Hakemlik admin — son işler tablosu (dosya, mod, durum, tarih).
// Tabular sayılar, 1px çizgiler, sakin enstrüman. Tamamlanan işe rapor linki.

"use client";

import Link from "next/link";
import { ExternalLink, Loader2 } from "lucide-react";

import { StatusPill } from "@/components/admin/StatusPill";
import { useAdminJobs } from "@/hooks/useReview";
import type { AdminJob, ReviewMode } from "@/lib/review-api";

const MODE_LABELS: Record<ReviewMode, string> = {
  author: "Yazar",
  editor: "Editör",
};

export default function AdminJobsPage() {
  const { data, isPending, isError, error, refetch } = useAdminJobs();
  const jobs = data?.jobs ?? [];

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1.5">
        <h1 className="serif text-[28px] font-medium italic leading-tight tracking-[-0.015em]">
          İşler
        </h1>
        <p className="text-[14px] text-ink-mute">
          Son hakemlik işleri. 5 saniyede bir yenilenir.
        </p>
      </header>

      {isError ? (
        <ErrorBox message={error.message} onRetry={() => refetch()} />
      ) : isPending ? (
        <LoadingBox />
      ) : jobs.length === 0 ? (
        <EmptyBox />
      ) : (
        <div className="overflow-x-auto rounded-md border border-rule bg-bg-card shadow-sm">
          <table className="w-full border-collapse text-left">
            <thead>
              <tr className="border-b border-rule">
                <Th>Dosya / İş</Th>
                <Th>Mod</Th>
                <Th>Dil</Th>
                <Th>Durum</Th>
                <Th>Oluşturuldu</Th>
                <Th className="text-right">Rapor</Th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <JobRow key={job.job_id} job={job} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function JobRow({ job }: { job: AdminJob }) {
  const created = new Date(job.created_at);
  const createdLabel = Number.isNaN(created.getTime())
    ? job.created_at
    : created.toLocaleString("tr-TR");
  const name = job.filename?.trim() || `${job.job_id.slice(0, 8)}…`;

  return (
    <tr className="border-b border-rule-soft last:border-b-0 transition-colors hover:bg-bg-soft">
      <Td>
        <span className="block max-w-[280px] truncate text-[13.5px] font-medium text-ink">
          {name}
        </span>
        <span className="font-mono-pmid text-[11px] text-ink-faint">
          {job.job_id.slice(0, 8)}
        </span>
      </Td>
      <Td>
        <span className="text-[13px] text-ink-soft">
          {MODE_LABELS[job.mode]}
        </span>
      </Td>
      <Td>
        <span className="font-mono-pmid text-[12px] uppercase text-ink-mute">
          {job.language}
        </span>
      </Td>
      <Td>
        <StatusPill status={job.status} />
      </Td>
      <Td>
        <span className="font-mono-pmid text-[12px] tabular-nums text-ink-mute">
          {createdLabel}
        </span>
      </Td>
      <Td className="text-right">
        {job.status === "done" ? (
          <Link
            href={`/review/${job.job_id}`}
            className="inline-flex items-center gap-1 text-[12.5px] text-accent no-underline transition-opacity hover:opacity-80"
          >
            Aç <ExternalLink className="h-3 w-3" aria-hidden />
          </Link>
        ) : (
          <span className="text-[12.5px] text-ink-faint">—</span>
        )}
      </Td>
    </tr>
  );
}

function Th({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <th
      className={`px-4 py-2.5 text-[11px] font-semibold uppercase tracking-wider text-ink-faint ${className}`}
    >
      {children}
    </th>
  );
}

function Td({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <td className={`px-4 py-3 align-top ${className}`}>{children}</td>;
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

function EmptyBox() {
  return (
    <div className="rounded-md border border-dashed border-rule px-6 py-12 text-center">
      <p className="text-[14px] text-ink-soft">Henüz iş yok.</p>
      <p className="mt-1 text-[12.5px] text-ink-mute">
        Bir makale yüklendiğinde burada görünür.
      </p>
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
        İşler alınamadı
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
