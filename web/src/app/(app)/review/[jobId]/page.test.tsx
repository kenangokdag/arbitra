// F14 Hakemlik — ilerleme görünümü (2D / G4): backend per-stage emit ettiğinde
// StageTimeline çıplak çark yerine GERÇEK aşama listesini gösterir; sürmekte olan
// aşama vurgulanır (aria-current) ve düşürülmüş aşama nedeni görünür.
// Not: tam sayfa `use(params)` (React 19 suspense) jsdom'da çözülmediği için
// 2D mantığını taşıyan ProgressView'i doğrudan render ederiz (gerçek wiring).

import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { ProgressView } from "./page";
import type { ReviewStageState } from "@/lib/review-api";

const STAGES: ReviewStageState[] = [
  {
    stage: "parse_document",
    status: "completed",
    progress: 1,
    started_at: null,
    completed_at: null,
    error_code: null,
    degraded_reason: null,
    summary: null,
  },
  {
    stage: "resolve_references",
    status: "degraded",
    progress: 1,
    started_at: null,
    completed_at: null,
    error_code: null,
    degraded_reason: "2 kaynak indekste eşlenemedi",
    summary: null,
  },
  {
    stage: "run_reviewer_council",
    status: "running",
    progress: 0.5,
    started_at: null,
    completed_at: null,
    error_code: null,
    degraded_reason: null,
    summary: "Hakem heyeti görüşüyor",
  },
];

afterEach(() => cleanup());

describe("ProgressView — gerçek ilerleme (2D / G4)", () => {
  it("canlı stages'i StageTimeline'a basar ve sürmekte olan aşamayı vurgular", () => {
    render(
      <ProgressView
        label="Hakem değerlendirmesi yürütülüyor"
        progress={0.6}
        stages={STAGES}
      />,
    );

    // çıplak çark değil — gerçek aşama çizelgesi
    expect(screen.getByTestId("stage-timeline")).toBeInTheDocument();

    // sürmekte olan aşama (running) aria-current="step" ile vurgulanır
    const rows = screen.getAllByTestId("stage-row");
    const running = rows.find(
      (r) => r.getAttribute("data-stage") === "run_reviewer_council",
    );
    expect(running).toHaveAttribute("aria-current", "step");

    // tamamlanmış/düşürülmüş aşamalar VURGULU DEĞİL (yalnız running)
    const completed = rows.find(
      (r) => r.getAttribute("data-stage") === "parse_document",
    );
    expect(completed).not.toHaveAttribute("aria-current");

    // düşürülmüş aşama nedeni görünür (sessiz değil)
    expect(screen.getByTestId("stage-degraded-reason")).toHaveTextContent(
      "2 kaynak indekste eşlenemedi",
    );
  });

  it("stages yokken (henüz emit edilmedi) çöker değil, yüzde ilerleme gösterir", () => {
    render(<ProgressView label="Sıraya alındı" progress={0.1} />);
    expect(screen.queryByTestId("stage-timeline")).toBeNull();
    expect(screen.getByText("%10")).toBeInTheDocument();
  });
});
