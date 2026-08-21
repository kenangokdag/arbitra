// V1-S17 P008 RC3 — ConnectedPapersPage proje anchor default + URL override.
// Plan: docs/plans/V1_S17_cascade_5rc.md §2 P008 (2 vitest).

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

import { ConnectedPapersPage } from "./ConnectedPapersPage";

const apiFetchMock = vi.fn();
const searchParams = new URLSearchParams();

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "prj-1" }),
  useSearchParams: () => searchParams,
}));

vi.mock("@/lib/api", () => ({
  apiFetch: (path: string, opts?: unknown) => apiFetchMock(path, opts),
}));

function withQuery(ui: ReactNode): ReactNode {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{ui}</QueryClientProvider>;
}

const clusterReady = {
  project_id: "prj-1",
  anchor_paper_id: "W777",
  cluster_status: "ready",
  cluster_size: 50,
};

const connectedStub = {
  source_paper_id: "W777",
  neighbors: [
    { paper_id: "W101", title: "Neighbor One", cosine_score: 0.82, raw_count: 12, rank: 1 },
    { paper_id: "W102", title: "Neighbor Two", cosine_score: 0.71, raw_count: 9, rank: 2 },
  ],
  total: 2,
};

beforeEach(() => {
  apiFetchMock.mockReset();
  // Reset URL params (default: no override)
  for (const key of Array.from(searchParams.keys())) {
    searchParams.delete(key);
  }
});

afterEach(() => cleanup());

describe("ConnectedPapersPage — V1-S17 P008", () => {
  it("URL paper_id YOKSA cluster_status'tan anchor_paper_id'yi default kullanir", async () => {
    apiFetchMock.mockImplementation(async (path: string) => {
      if (path.includes("/cluster/status")) return clusterReady;
      if (path.includes("/api/connected-papers/W777")) return connectedStub;
      throw new Error(`unexpected fetch: ${path}`);
    });

    const { findByText } = render(withQuery(<ConnectedPapersPage />));
    // anchor_paper_id'yi başlıkta gör
    await findByText("W777");
    // "proje capasi" rozeti
    await findByText(/proje capasi/i);
    // Connected-papers çağrısı anchor ile yapıldı
    await waitFor(() => {
      const paths = apiFetchMock.mock.calls.map((c) => c[0]);
      expect(paths.some((p) => p.startsWith("/api/connected-papers/W777"))).toBe(true);
    });
  });

  it("URL ?paper_id= anchor'i override eder ve 'capaya don' linki gosterir", async () => {
    searchParams.set("paper_id", "W999");
    apiFetchMock.mockImplementation(async (path: string) => {
      if (path.includes("/cluster/status")) return clusterReady;
      if (path.includes("/api/connected-papers/W999")) return connectedStub;
      throw new Error(`unexpected fetch: ${path}`);
    });

    const { findByText } = render(withQuery(<ConnectedPapersPage />));
    await findByText("W999");
    // Override aktifken capaya geri dön linki var
    const back = await findByText(/capaya don/i);
    expect(back.getAttribute("href")).toContain("/project/prj-1/");
    // connected-papers çağrısı override ID ile yapıldı
    await waitFor(() => {
      const paths = apiFetchMock.mock.calls.map((c) => c[0]);
      expect(paths.some((p) => p.startsWith("/api/connected-papers/W999"))).toBe(true);
    });
  });

  // V1-S17 P009 RC5 — "Incele" Link aktif: /paper/{paper_id}
  it("dugume tiklandiginda detay panelinde 'Incele' Link aktif olur", async () => {
    apiFetchMock.mockImplementation(async (path: string) => {
      if (path.includes("/cluster/status")) return clusterReady;
      if (path.includes("/api/connected-papers/W777")) return connectedStub;
      throw new Error(`unexpected fetch: ${path}`);
    });

    render(withQuery(<ConnectedPapersPage />));
    // Komşu W101 SVG düğümü click — selectedNode set olur
    const neighborLabel = await screen.findByText(/Neighbor One/i);
    const clickable = neighborLabel.closest("g");
    expect(clickable, "neighbor group container").toBeTruthy();
    act(() => {
      fireEvent.click(clickable!);
    });
    // Detay panelinde Incele linki var
    const incele = await screen.findByRole("link", { name: /Incele/i });
    expect(incele.getAttribute("href")).toBe("/paper/W101");
  });
});
