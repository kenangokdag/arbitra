// Arbitra v2 — aşama zaman çizelgesi (yapısal kabuk).
// Her aşama DURUMUYLA birlikte metin + ikon olarak görünür (çıplak spinner YOK —
// kullanıcı sahte "işleniyor" hissine bırakılmaz). Düşürülmüş aşama nedenini gösterir.

import {
  Check,
  ChevronRight,
  CircleDashed,
  Loader2,
  SkipForward,
  TriangleAlert,
  XCircle,
} from "lucide-react";

import { cn } from "@/lib/cn";
import type { ReviewStage, ReviewStageState, StageStatus } from "@/lib/review-api";

const STAGE_LABEL: Record<ReviewStage, string> = {
  file_security_scan: "Dosya güvenlik taraması",
  parse_document: "Belge ayrıştırma",
  classify: "Belge sınıflandırma",
  extract_references: "Kaynak çıkarma",
  resolve_references: "Kaynak eşleme",
  retrieve_evidence: "Kanıt toplama",
  select_guidelines: "Kılavuz seçimi",
  run_academic_engines: "Akademik motorlar",
  run_reviewer_council: "Hakem heyeti",
  editor_synthesis: "Editör sentezi",
  build_report: "Rapor oluşturma",
  prepare_exports: "Dışa aktarım hazırlığı",
};

type StatusMeta = {
  label: string;
  token: string;
  Icon: typeof Check;
  spin?: boolean;
};

const STATUS_META: Record<StageStatus, StatusMeta> = {
  queued: { label: "Sırada", token: "var(--color-ink-faint)", Icon: CircleDashed },
  running: { label: "Sürüyor", token: "var(--color-info)", Icon: Loader2, spin: true },
  completed: { label: "Tamamlandı", token: "var(--color-ok)", Icon: Check },
  degraded: { label: "Sınırlı", token: "var(--color-warn)", Icon: TriangleAlert },
  failed: { label: "Başarısız", token: "var(--color-danger)", Icon: XCircle },
  skipped: { label: "Atlandı", token: "var(--color-ink-faint)", Icon: SkipForward },
};

export type StageTimelineProps = {
  stages: ReviewStageState[];
  currentStage?: ReviewStage;
  className?: string;
};

export function StageTimeline({ stages, currentStage, className }: StageTimelineProps) {
  return (
    <ol data-testid="stage-timeline" className={cn("flex flex-col gap-1", className)}>
      {stages.map((stage) => {
        const meta = STATUS_META[stage.status];
        const Icon = meta.Icon;
        const isCurrent = currentStage === stage.stage;

        return (
          <li
            key={stage.stage}
            data-testid="stage-row"
            data-stage={stage.stage}
            data-status={stage.status}
            aria-current={isCurrent ? "step" : undefined}
            className={cn(
              "flex flex-col gap-1 rounded-md px-2.5 py-2",
              isCurrent && "bg-[color:var(--color-bg-soft)]",
            )}
          >
            <div className="flex items-center gap-2.5 text-sm">
              {isCurrent ? (
                <ChevronRight aria-hidden className="h-3.5 w-3.5 flex-shrink-0 text-[color:var(--color-accent)]" />
              ) : (
                <span aria-hidden className="h-3.5 w-3.5 flex-shrink-0" />
              )}
              <Icon
                aria-hidden
                className={cn("h-4 w-4 flex-shrink-0", meta.spin && "animate-spin")}
                style={{ color: meta.token }}
              />
              <span className="flex-1 text-[color:var(--color-ink)]">{STAGE_LABEL[stage.stage]}</span>
              <span data-testid="stage-status-label" className="text-xs font-medium" style={{ color: meta.token }}>
                {meta.label}
              </span>
            </div>
            {stage.status === "degraded" && stage.degraded_reason ? (
              <p
                data-testid="stage-degraded-reason"
                className="ml-8 text-xs text-[color:var(--color-warn)]"
              >
                {stage.degraded_reason}
              </p>
            ) : null}
            {stage.summary ? (
              <p className="ml-8 text-xs text-[color:var(--color-ink-mute)]">{stage.summary}</p>
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}
