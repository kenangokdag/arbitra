// V1-S17 P010 (KD-V1-S17-05) — AnchorRecommendationsPage 3-yol render testleri.
// Plan: docs/plans/V1_S17_cascade_5rc.md §2 P010 (3 vitest).

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

import { AnchorRecommendationsPage } from "./AnchorRecommendationsPage";

const apiFetchMock = vi.fn();

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "prj-1" }),
}));

vi.mock("@/lib/api", () => ({
  apiFetch: (path: string, opts?: unknown) => apiFetchMock(path, opts),
}));

function withQuery(ui: ReactNode): ReactNode {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{ui}</QueryClientProvider>;
}

beforeEach(() => {
  apiFetchMock.mockReset();
});

afterEach(() => cleanup());

describe("AnchorRecommendationsPage — V1-S17 P010", () => {
  it("cluster_status='expanding' iken pending spinner gosterir", async () => {
    apiFetchMock.mockImplementation(async (path: string) => {
      if (path.includes("/cluster/status")) {
        return {
          project_id: "prj-1",
          anchor_paper_id: "W777",
          cluster_status: "expanding",
          cluster_size: 0,
        };
      }
      throw new Error(`unexpected fetch: ${path}`);
    });

    render(withQuery(<AnchorRecommendationsPage />));
    const pending = await screen.findByTestId("anchor-recs-pending");
    expect(pending.textContent).toMatch(/Cluster genisliyor/i);
    expect(pending.textContent).toContain("W777");
  });

  it("cluster_status='failed' iken hata banner + capa secimine don Link gosterir", async () => {
    apiFetchMock.mockImplementation(async (path: string) => {
      if (path.includes("/cluster/status")) {
        return {
          project_id: "prj-1",
          anchor_paper_id: null,
          cluster_status: "failed",
          cluster_size: 0,
          cluster_error: { reason: "OpenAlex 429 rate-limit" },
        };
      }
      throw new Error(`unexpected fetch: ${path}`);
    });

    render(withQuery(<AnchorRecommendationsPage />));
    const failed = await screen.findByTestId("anchor-recs-failed");
    expect(failed.textContent).toMatch(/Cluster expand basarisiz/i);
    expect(failed.textContent).toContain("OpenAlex 429 rate-limit");
    const back = await screen.findByRole("link", { name: /Capa secimine don/i });
    expect(back.getAttribute("href")).toBe("/project/prj-1/discovery-1");
  });

  it("cluster_status='ready' iken anchor header + top-5 listesi cizer", async () => {
    apiFetchMock.mockImplementation(async (path: string) => {
      if (path.includes("/cluster/status")) {
        return {
          project_id: "prj-1",
          anchor_paper_id: "W777",
          cluster_status: "ready",
          cluster_size: 50,
        };
      }
      if (path.includes("/api/project/prj-1/papers?rank_max=5")) {
        return {
          project_id: "prj-1",
          hydrated_count: 3,
          papers: [
            {
              paper_id: "W101",
              title: "Top Paper One",
              abstract: null,
              authors: ["Alice", "Bob"],
              year: 2023,
              venue: "Nature",
              doi: null,
              citations_count: 12,
            },
            {
              paper_id: "W102",
              title: "Top Paper Two",
              abstract: null,
              authors: ["Carol"],
              year: 2024,
              venue: "Science",
              doi: null,
              citations_count: 9,
            },
            {
              paper_id: "W103",
              title: "Top Paper Three",
              abstract: null,
              authors: ["Dan", "Eve", "Fay", "Greg"],
              year: 2022,
              venue: null,
              doi: null,
              citations_count: 5,
            },
          ],
        };
      }
      throw new Error(`unexpected fetch: ${path}`);
    });

    render(withQuery(<AnchorRecommendationsPage />));
    const ready = await screen.findByTestId("anchor-recs-ready");
    expect(ready.textContent).toContain("W777");
    expect(ready.textContent).toMatch(/Cluster boyutu: 50/);

    await screen.findByText("Top Paper One");
    await screen.findByText("Top Paper Two");
    await screen.findByText("Top Paper Three");

    // "Incele" linki her satirda /paper/{paper_id}'ye gidiyor
    await waitFor(() => {
      const links = screen.getAllByRole("link", { name: /Incele/i });
      const hrefs = links.map((l) => l.getAttribute("href"));
      expect(hrefs).toContain("/paper/W101");
      expect(hrefs).toContain("/paper/W102");
      expect(hrefs).toContain("/paper/W103");
    });

    // 4+ yazar et al. takisi
    expect(ready.textContent).toMatch(/Dan, Eve, Fay et al\./);
  });
});
