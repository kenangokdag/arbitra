// kaynak: docs/plans/V1_S10_vitrin_tek_sayfa.md §7
// V1-S10-06: pure helper testleri — applyLocalFilters / selectAllClamped /
// isAllVisibleSelected. Davranış kanıtı (CLAUDE.md §3.6).

import { describe, it, expect } from "vitest";

import {
  applyLocalFilters,
  selectAllClamped,
  isAllVisibleSelected,
  DEFAULT_LOCAL_FILTERS,
} from "./q-filters";
import type { PaperPreviewApi } from "./q-api";

function mkPaper(over: Partial<PaperPreviewApi>): PaperPreviewApi {
  return {
    id: over.id ?? "W1",
    doi: null,
    title: over.title ?? "T",
    abstract: over.abstract ?? null,
    year: over.year ?? null,
    venue: null,
    authors: [],
    authorsLabel: "—",
    citedByCount: over.citedByCount ?? 0,
    ...over,
  };
}

describe("applyLocalFilters", () => {
  it("default filtreler → liste değişmez (sıra korunur)", () => {
    const papers = [
      mkPaper({ id: "A", citedByCount: 5 }),
      mkPaper({ id: "B", citedByCount: 100 }),
      mkPaper({ id: "C", citedByCount: 0 }),
    ];
    const out = applyLocalFilters(papers, DEFAULT_LOCAL_FILTERS);
    expect(out.map((p) => p.id)).toEqual(["A", "B", "C"]);
  });

  it("minCitations filtre — eşiğin altındaki makaleler atılır", () => {
    const papers = [
      mkPaper({ id: "A", citedByCount: 5 }),
      mkPaper({ id: "B", citedByCount: 50 }),
      mkPaper({ id: "C", citedByCount: 100 }),
    ];
    const out = applyLocalFilters(papers, {
      ...DEFAULT_LOCAL_FILTERS,
      minCitations: 50,
    });
    expect(out.map((p) => p.id)).toEqual(["B", "C"]);
  });

  it("hasAbstractOnly filtre — abstract'ı null olanlar atılır", () => {
    const papers = [
      mkPaper({ id: "A", abstract: "var" }),
      mkPaper({ id: "B", abstract: null }),
      mkPaper({ id: "C", abstract: "var2" }),
    ];
    const out = applyLocalFilters(papers, {
      ...DEFAULT_LOCAL_FILTERS,
      hasAbstractOnly: true,
    });
    expect(out.map((p) => p.id)).toEqual(["A", "C"]);
  });

  it("sort=citations_desc — atıfa göre azalan", () => {
    const papers = [
      mkPaper({ id: "A", citedByCount: 5 }),
      mkPaper({ id: "B", citedByCount: 100 }),
      mkPaper({ id: "C", citedByCount: 50 }),
    ];
    const out = applyLocalFilters(papers, {
      ...DEFAULT_LOCAL_FILTERS,
      sort: "citations_desc",
    });
    expect(out.map((p) => p.id)).toEqual(["B", "C", "A"]);
  });

  it("sort=year_desc — yılı null olanlar 0 sayılır, yenisi başa", () => {
    const papers = [
      mkPaper({ id: "A", year: 2010 }),
      mkPaper({ id: "B", year: 2024 }),
      mkPaper({ id: "C", year: null }),
      mkPaper({ id: "D", year: 2018 }),
    ];
    const out = applyLocalFilters(papers, {
      ...DEFAULT_LOCAL_FILTERS,
      sort: "year_desc",
    });
    expect(out.map((p) => p.id)).toEqual(["B", "D", "A", "C"]);
  });

  it("filter + sort kombinasyonu — önce filtre sonra sıralama", () => {
    const papers = [
      mkPaper({ id: "A", citedByCount: 5, year: 2024 }),
      mkPaper({ id: "B", citedByCount: 100, year: 2020 }),
      mkPaper({ id: "C", citedByCount: 50, year: 2022 }),
    ];
    const out = applyLocalFilters(papers, {
      minCitations: 50,
      hasAbstractOnly: false,
      sort: "year_desc",
    });
    expect(out.map((p) => p.id)).toEqual(["C", "B"]);
  });
});

describe("selectAllClamped", () => {
  it("anon (max=3) — ilk 3 ID set'e girer", () => {
    const papers = ["A", "B", "C", "D", "E"].map((id) => mkPaper({ id }));
    const out = selectAllClamped(papers, 3);
    expect(Array.from(out).sort()).toEqual(["A", "B", "C"]);
  });

  it("authed (max=25) — 5 makale varsa hepsi seçilir", () => {
    const papers = ["A", "B", "C", "D", "E"].map((id) => mkPaper({ id }));
    const out = selectAllClamped(papers, 25);
    expect(out.size).toBe(5);
  });
});

describe("isAllVisibleSelected", () => {
  it("hiç seçili yoksa → false (boş liste de false)", () => {
    const papers = ["A", "B"].map((id) => mkPaper({ id }));
    expect(isAllVisibleSelected(papers, new Set(), 25)).toBe(false);
    expect(isAllVisibleSelected([], new Set(), 25)).toBe(false);
  });

  it("anon (max=3) — ilk 3 seçiliyse true (geri kalan önemsiz)", () => {
    const papers = ["A", "B", "C", "D", "E"].map((id) => mkPaper({ id }));
    expect(isAllVisibleSelected(papers, new Set(["A", "B", "C"]), 3)).toBe(
      true,
    );
  });

  it("kısmi seçim → false (indeterminate UI tarafı)", () => {
    const papers = ["A", "B", "C"].map((id) => mkPaper({ id }));
    expect(isAllVisibleSelected(papers, new Set(["A"]), 25)).toBe(false);
  });
});
