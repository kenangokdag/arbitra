import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { ProjectClosurePage } from "./ProjectClosurePage";

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "11111111-1111-1111-1111-111111111111" }),
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
}));

const apiFetchMock = vi.fn();

vi.mock("@/lib/api", () => ({
  apiFetch: (path: string, opts?: unknown) => apiFetchMock(path, opts),
  ApiError: class ApiError extends Error {
    status = 0;
    detail: unknown = null;
  },
}));

const PROJECT_ID = "11111111-1111-1111-1111-111111111111";

const snapshotStub = {
  completion_id: "33333333-3333-3333-3333-333333333333",
  project_id: PROJECT_ID,
  completed_at: "2026-05-11T10:00:00Z",
  delete_after: "2027-05-11T10:00:00Z",
  snapshot: {
    summary_paragraph: "Tezini bitirdin — 5 tezgah, 87 makale, 14 prova.",
    badges: { basarili: 18, gelistirilmeli: 4 },
    graduate_advice: [
      "Tezini makale formatına dönüştürmeyi düşün.",
      "Jüri savunması sonrası 4 hafta dinlen.",
    ],
    step_reviews: [
      {
        step_id: "discovery-1",
        label: "Araştırma alanı",
        status: "basarili" as const,
        score: 0.92,
        comment: "Net ve odaklı bir alan seçimi.",
      },
      {
        step_id: "defense-2",
        label: "Tez içeriği",
        status: "gelistirilmeli" as const,
        score: 0.55,
        comment: "Yöntem bölümü zayıf bırakılmış.",
      },
    ],
  },
};

const feedbackStub = {
  completion_id: "33333333-3333-3333-3333-333333333333",
  project_id: PROJECT_ID,
  updated_at: "2026-05-11T10:05:00Z",
  feedback: {
    topic_suggestion_rating: 5,
    process_rating: 5,
    missing_features: "",
    overall_satisfaction: 5,
    nps: 9,
  },
};

beforeEach(() => {
  apiFetchMock.mockReset();
});

afterEach(() => cleanup());

describe("ProjectClosurePage", () => {
  it("ilk render: snapshot yok → fallback letter + 'Mezuniyet ozetini olustur' butonu", () => {
    render(<ProjectClosurePage />);
    expect(screen.getByRole("heading", { name: /Tezini bitirdin/i })).toBeTruthy();
    expect(screen.getByRole("button", { name: /Mezuniyet ozetini olustur/i })).toBeTruthy();
    expect(screen.getByText(/504K hucrelik/)).toBeTruthy();
  });

  it("Mezuniyet ozetini olustur → POST snapshot + step_reviews + badges + advice render", async () => {
    apiFetchMock.mockResolvedValueOnce(snapshotStub);
    render(<ProjectClosurePage />);
    fireEvent.click(screen.getByRole("button", { name: /Mezuniyet ozetini olustur/i }));

    await waitFor(() => {
      expect(screen.getByText(/Tezini bitirdin — 5 tezgah/)).toBeTruthy();
    });
    expect(screen.getByText("Araştırma alanı")).toBeTruthy();
    expect(screen.getByText("Tez içeriği")).toBeTruthy();
    expect(screen.getByText("%92")).toBeTruthy();
    expect(screen.getByText("%55")).toBeTruthy();
    expect(screen.getByText("18")).toBeTruthy();
    expect(screen.getByText("4")).toBeTruthy();
    expect(screen.getByText(/Tezini makale formatına/)).toBeTruthy();

    expect(apiFetchMock).toHaveBeenCalledWith(
      "/api/completion/snapshot",
      expect.objectContaining({
        method: "POST",
        body: expect.objectContaining({ project_id: PROJECT_ID }),
      }),
    );
  });

  it("Geri bildirim ver → form → Gonder → POST /feedback/project-completion + tesekkur banner", async () => {
    render(<ProjectClosurePage />);
    fireEvent.click(screen.getByRole("button", { name: /^Geri bildirim ver$/i }));

    expect(screen.getByText(/Konu onerisi puani/)).toBeTruthy();

    apiFetchMock.mockResolvedValueOnce(feedbackStub);
    fireEvent.click(screen.getByRole("button", { name: /^Gonder$/i }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/api/feedback/project-completion",
        expect.objectContaining({
          method: "POST",
          body: expect.objectContaining({
            project_id: PROJECT_ID,
            feedback: expect.objectContaining({
              topic_suggestion_rating: 5,
              process_rating: 5,
              overall_satisfaction: 5,
              nps: 9,
            }),
          }),
        }),
      );
    });

    await waitFor(() => {
      expect(screen.getByText(/Tesekkurler — geri-bildirimin kaydedildi/)).toBeTruthy();
    });
  });

  it("close + back actions ve footer", () => {
    render(<ProjectClosurePage />);
    expect(screen.getByRole("button", { name: /Projeyi kapat/i })).toBeTruthy();
    expect(screen.getByRole("button", { name: /5\.5 Simulasyona don/i })).toBeTruthy();
    expect(screen.getByText(/Bilim, sabirla yapilir/)).toBeTruthy();
  });
});
