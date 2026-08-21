// V1-S13 P005: DataProvenance pill render + a11y test.
// Plan: docs/plans/V1_S13_demo_path_polish.md §5.
// Popover icerik testi yapilmaz — Base UI portal/openOnHover JSDOM'da
// render edilmiyor; pill (Trigger) ve aria-label kontrolu yeterli.

import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { DataProvenance } from "./DataProvenance";

afterEach(() => cleanup());

const baseProps = {
  source: "warehouse aggregate · papers.published_year",
  n: 240,
  method: "GROUP BY published_year, COUNT(*).",
  updatedAt: "2026-05-09",
} as const;

describe("DataProvenance", () => {
  it("renders pill with N=<n> and confidence letter", () => {
    render(<DataProvenance {...baseProps} confidence="A" />);
    const trigger = screen.getByRole("button", { name: /Veri kaynagi/i });
    expect(trigger.textContent).toContain("N=240");
    expect(trigger.textContent).toContain("A");
  });

  it("includes source and N in aria-label for screen readers", () => {
    render(<DataProvenance {...baseProps} confidence="B" />);
    const trigger = screen.getByRole("button", { name: /Veri kaynagi/i });
    const label = trigger.getAttribute("aria-label") ?? "";
    expect(label).toContain("warehouse aggregate");
    expect(label).toContain("N=240");
    expect(label).toContain("B");
  });

  it("supports A/B/C confidence levels", () => {
    const { rerender } = render(<DataProvenance {...baseProps} confidence="A" />);
    expect(screen.getByRole("button").textContent).toContain("A");
    rerender(<DataProvenance {...baseProps} confidence="B" />);
    expect(screen.getByRole("button").textContent).toContain("B");
    rerender(<DataProvenance {...baseProps} confidence="C" />);
    expect(screen.getByRole("button").textContent).toContain("C");
  });
});
