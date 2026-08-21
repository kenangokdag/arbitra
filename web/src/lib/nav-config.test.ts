// V1-S17 P007 (KD-V1-S17-05) — curation-1 label "Onerilen Literatur" KORUNUR.
// AnchorRecommendationsPage curation-1'e taşındıktan sonra etiket gerçek
// "önerilen literatür" sayfası olduğu için label revizesi iptal.

import { describe, expect, it } from "vitest";
import { buildBreadcrumb, workbenches } from "./nav-config";

describe("nav-config — V1-S17 P007", () => {
  it("curation-1 label 'Onerilen Literatur' olarak korunur", () => {
    const curation = workbenches.find((w) => w.id === "curation");
    expect(curation, "curation workbench mevcut").toBeTruthy();
    const page = curation!.pages.find((p) => p.id === "curation-1");
    expect(page?.label).toBe("Onerilen Literatur");
  });

  it("buildBreadcrumb curation-1 için sidebar label'ı kullanır", () => {
    const crumbs = buildBreadcrumb("curation-1", "Tez 1");
    expect(crumbs).toEqual(["Projelerim", "Tez 1", "Inceleme", "Onerilen Literatur"]);
  });
});
