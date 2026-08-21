// F14 Hakemlik — iş/ilerleme + rapor sayfası.
// status'u ~2sn poll et (done/failed olunca dur). done değilken dönen çark +
// insan cümlesi (STATUS_LABELS). done olunca raporu çek → ReviewReportView.

"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertTriangle, ArrowLeft, Loader2, Trash2 } from "lucide-react";

import { ReviewReportView } from "@/components/review/ReviewReportView";
import { StageTimeline } from "@/components/review/StageTimeline";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import {
  useReviewReport,
  useReviewStatus,
  useVersionComparison,
} from "@/hooks/useReview";
import {
  STATUS_LABELS,
  deleteReviewJob,
  type ReviewStageState,
} from "@/lib/review-api";
import { useSetChatboxContext } from "@/stores/ui";

export default function ReviewJobPage({
  params,
}: {
  params: Promise<{ jobId: string }>;
}) {
  const { jobId } = use(params);

  const statusQuery = useReviewStatus(jobId);
  const status = statusQuery.data?.status;
  const isDone = status === "done";
  const isFailed = status === "failed";

  const reportQuery = useReviewReport(jobId, isDone);
  // VERSIYON_KARSILASTIRMA_FAZ1_2026-08-17 §3.4 — comparison=null (parent yok)
  // ya da hata durumunda sessizce atlanır, rapor çökmesin diye ana veri değil.
  const comparisonQuery = useVersionComparison(jobId, isDone);

  // DANISMAN_CHAT_BAGLAM_SENKRONU_2026-08-19: panel AÇIK olsun ya da olmasın,
  // bu rapor sayfası mount olunca (ya da jobId değişince) context'i senkronize
  // et — kullanıcı "Danışman'a sor" butonuna TEKRAR tıklamasa bile panel
  // ESKİ rapora göre konuşmaya devam ETMEZ (bulunan gerçek hata). `open`'a
  // dokunmaz — panel kendiliğinden açılmaz.
  const setChatboxContext = useSetChatboxContext();
  useEffect(() => {
    setChatboxContext({ kind: "advisor", mode: "review_advisor", reportId: jobId });
  }, [jobId, setChatboxContext]);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between gap-3">
        <Link
          href="/review"
          className="inline-flex w-fit items-center gap-1.5 text-[13px] text-ink-mute transition-colors hover:text-ink"
        >
          <ArrowLeft className="h-3.5 w-3.5" aria-hidden />
          Yeni inceleme
        </Link>
        <DeleteReviewAction jobId={jobId} />
      </div>

      {/* Status çekilemedi */}
      {statusQuery.isError ? (
        <ErrorBox
          title="Durum alınamadı"
          message={statusQuery.error.message}
          onRetry={() => statusQuery.refetch()}
        />
      ) : isFailed ? (
        <ErrorBox
          title="İnceleme tamamlanamadı"
          message={
            statusQuery.data?.error ??
            "İşlem sırasında bir sorun oluştu. Dosyayı tekrar yüklemeyi dene."
          }
        />
      ) : isDone ? (
        reportQuery.isError ? (
          <ErrorBox
            title="Rapor yüklenemedi"
            message={reportQuery.error.message}
            onRetry={() => reportQuery.refetch()}
          />
        ) : reportQuery.data ? (
          <ReviewReportView
            report={reportQuery.data.report}
            jobId={jobId}
            comparison={comparisonQuery.data?.comparison ?? null}
          />
        ) : (
          <ProgressView label="Rapor hazırlanıyor" progress={1} />
        )
      ) : (
        <ProgressView
          label={status ? STATUS_LABELS[status] : "Sıraya alındı"}
          progress={statusQuery.data?.progress ?? 0}
          stages={statusQuery.data?.stages}
        />
      )}
    </div>
  );
}

/** Bu değerlendirmeyi sil — sahip-yalnız, kalıcı (hesap silmeden hafif: tek onay,
 *  yazım metni YOK). 204 → /review; 404/hata → ConfirmDialog içinde okunur mesaj.
 *  Çift-gönderim kilidi + spinner ConfirmDialog tarafından sağlanır. */
function DeleteReviewAction({ jobId }: { jobId: string }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="inline-flex w-fit items-center gap-1.5 rounded-md border px-3 py-1.5 text-[13px] font-medium transition-colors"
        style={{
          borderColor: "color-mix(in oklab, var(--color-warn) 40%, var(--color-rule))",
          color: "var(--color-warn)",
        }}
      >
        <Trash2 className="h-3.5 w-3.5" aria-hidden />
        Bu değerlendirmeyi sil
      </button>

      <ConfirmDialog
        open={open}
        onClose={() => setOpen(false)}
        onConfirm={() => deleteReviewJob(jobId)}
        onSuccess={() => router.push("/review")}
        title="Değerlendirmeyi sil"
        confirmLabel="Sil"
        cancelLabel="Vazgeç"
        description={
          <>
            Bu değerlendirme ve raporu{" "}
            <strong className="font-semibold text-ink">kalıcı olarak</strong>{" "}
            silinecek. Bu işlem geri alınamaz.
          </>
        }
        success={{
          title: "Değerlendirme silindi",
          description: "İncelemeler sayfasına dönülüyor…",
        }}
      />
    </>
  );
}

export function ProgressView({
  label,
  progress,
  stages,
}: {
  label: string;
  progress: number;
  stages?: ReviewStageState[];
}) {
  const pct = Math.round(Math.min(1, Math.max(0, progress)) * 100);
  // 2D / G4 — sürmekte olan aşamayı türet (StageTimeline aria-current vurgusu).
  const currentStage = stages?.find((s) => s.status === "running")?.stage;
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex flex-col items-center justify-center gap-5 rounded-md border border-rule bg-bg-card px-6 py-16 text-center shadow-sm"
    >
      {/* motion-safe dönen çark; reduced-motion'da statik durum metni kalır */}
      <Loader2
        className="h-8 w-8 animate-spin text-accent motion-reduce:hidden"
        strokeWidth={1.75}
        aria-hidden
      />
      <div>
        <p className="serif text-[20px] italic text-ink">
          İnceleme sürüyor
        </p>
        <p className="mt-1.5 text-[14px] text-ink-mute">{label}…</p>
      </div>

      {/* İlerleme çubuğu */}
      <div className="w-full max-w-sm">
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-bg-hover">
          <div
            className="h-full rounded-full bg-accent transition-[width] duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]"
            style={{ width: `${pct}%` }}
          />
        </div>
        <p className="mt-2 font-mono-pmid text-[11px] uppercase tracking-[0.08em] text-ink-faint">
          %{pct}
        </p>
      </div>

      {/* Aşama zaman çizelgesi — G4: backend her aşamada stages yazar; gerçek
          ilerleme görünür (çıplak çark değil). Sürmekte olan aşama vurgulanır;
          düşürülmüş aşama nedeni gösterilir. */}
      {stages && stages.length > 0 ? (
        <div className="w-full max-w-sm text-left">
          <StageTimeline stages={stages} currentStage={currentStage} />
        </div>
      ) : null}
    </div>
  );
}

function ErrorBox({
  title,
  message,
  onRetry,
}: {
  title: string;
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div
      role="alert"
      className="flex flex-col items-center gap-3 rounded-md border px-6 py-12 text-center"
      style={{
        borderColor: "var(--color-danger)",
        background: "var(--color-danger-pale)",
      }}
    >
      <AlertTriangle
        className="h-7 w-7"
        style={{ color: "var(--color-danger)" }}
        aria-hidden
      />
      <div>
        <p
          className="text-[15px] font-medium"
          style={{ color: "var(--color-danger)" }}
        >
          {title}
        </p>
        <p className="mt-1 text-[13px] text-ink-mute">{message}</p>
      </div>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="mt-1 rounded-sm border px-3.5 py-1.5 text-[13px] font-medium transition-colors"
          style={{
            borderColor: "var(--color-danger)",
            color: "var(--color-danger)",
          }}
        >
          Tekrar dene
        </button>
      ) : null}
    </div>
  );
}
