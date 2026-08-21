import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { StageTimeline } from "./StageTimeline";
import type { ReviewStageState } from "@/lib/review-api";

function stage(over: Partial<ReviewStageState> & Pick<ReviewStageState, "stage" | "status">): ReviewStageState {
  return {
    progress: 0,
    started_at: null,
    completed_at: null,
    error_code: null,
    degraded_reason: null,
    summary: null,
    ...over,
  };
}

const stages: ReviewStageState[] = [
  stage({ stage: "parse_document", status: "completed" }),
  stage({ stage: "run_academic_engines", status: "running" }),
  stage({ stage: "retrieve_evidence", status: "degraded", degraded_reason: "Sağlayıcı zaman aşımı." }),
  stage({ stage: "prepare_exports", status: "queued" }),
];

describe("StageTimeline", () => {
  it("her aşamayı durum METNİyle gösterir (çıplak spinner değil)", () => {
    render(<StageTimeline stages={stages} />);
    expect(screen.getByText("Tamamlandı")).toBeInTheDocument();
    expect(screen.getByText("Sürüyor")).toBeInTheDocument();
    expect(screen.getByText("Sınırlı")).toBeInTheDocument();
    expect(screen.getByText("Sırada")).toBeInTheDocument();
  });

  it("degraded aşama degraded_reason'ı gösterir", () => {
    render(<StageTimeline stages={stages} />);
    expect(screen.getByTestId("stage-degraded-reason")).toHaveTextContent("Sağlayıcı zaman aşımı.");
  });

  it("currentStage aria-current=step ile işaretlenir", () => {
    const { container } = render(
      <StageTimeline stages={stages} currentStage="run_academic_engines" />,
    );
    const current = container.querySelector('[data-stage="run_academic_engines"]');
    expect(current?.getAttribute("aria-current")).toBe("step");
  });

  it("tüm aşamaları liste olarak render eder", () => {
    const { container } = render(<StageTimeline stages={stages} />);
    expect(container.querySelectorAll('[data-testid="stage-row"]').length).toBe(4);
  });
});
