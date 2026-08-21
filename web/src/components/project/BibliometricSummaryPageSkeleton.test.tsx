// V1-S13 P004: skeleton render + a11y test.
// Plan: docs/plans/V1_S13_demo_path_polish.md §5.

import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { BibliometricSummaryPageSkeleton } from "./BibliometricSummaryPageSkeleton";

afterEach(() => cleanup());

describe("BibliometricSummaryPageSkeleton", () => {
  it("renders aria-busy region with descriptive label", () => {
    const { container } = render(<BibliometricSummaryPageSkeleton />);
    const root = screen.getByLabelText(/Bibliyometrik panorama yukleniyor/i);
    expect(root.getAttribute("aria-busy")).toBe("true");
    expect(container.querySelector("[data-zone='discovery']")).toBeTruthy();
  });

  it("renders 4 metric placeholder cards", () => {
    const { container } = render(<BibliometricSummaryPageSkeleton />);
    const grid = container.querySelector("section.grid.grid-cols-2.md\\:grid-cols-4");
    expect(grid).toBeTruthy();
    expect(grid?.children.length).toBe(4);
  });

  it("renders 2 top-10 list skeletons with 10 rows each", () => {
    const { container } = render(<BibliometricSummaryPageSkeleton />);
    const lists = container.querySelectorAll("ol");
    expect(lists.length).toBe(2);
    lists.forEach((ol) => {
      expect(ol.children.length).toBe(10);
    });
  });
});
