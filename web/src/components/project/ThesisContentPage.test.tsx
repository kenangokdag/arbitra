import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { ThesisContentPage } from "./ThesisContentPage";

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "11111111-1111-1111-1111-111111111111" }),
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

const baseSection = (
  section_type: "intro" | "methods" | "findings" | "discussion" | "conclusion",
  content = "",
  word_count = 0,
  flag: "ok" | "sahte" | null = null,
  reason: string | null = null,
) => ({
  section_type,
  content,
  word_count,
  ai_quality_flag: flag,
  ai_quality_reason: reason,
  updated_at: "2026-05-11T00:00:00Z",
});

const manuscriptStubEmpty = {
  project_id: PROJECT_ID,
  sections: [baseSection("intro"), baseSection("methods")],
  gate_status: { filled_count: 0, gate_open: false, quality_blocked: false },
};

const manuscriptStubOpenGate = {
  project_id: PROJECT_ID,
  sections: [
    baseSection("intro", "Lorem 50 kelime intro içeriği.", 60, "ok"),
    baseSection("methods", "Yöntem", 55, "ok"),
    baseSection("findings", "Bulgular", 52, "ok"),
  ],
  gate_status: { filled_count: 3, gate_open: true, quality_blocked: false },
};

const manuscriptStubBlocked = {
  project_id: PROJECT_ID,
  sections: [
    baseSection("intro", "lorem ipsum", 50, "sahte", "Lorem ipsum tespit edildi."),
  ],
  gate_status: { filled_count: 1, gate_open: false, quality_blocked: true },
};

const upsertResultStub = baseSection("intro", "Yeni içerik.", 2, null);

const qualityResultStub = {
  section_type: "intro" as const,
  flag: "ok" as const,
  reason: "Akademik dil tutarlı.",
  cache_hit: false,
};

const autoDraftStub = {
  section_type: "methods" as const,
  draft_content: "Otomatik taslak: yöntem bölümü için 1 paragraf.",
  source_steps: ["3.3", "4.2"],
};

beforeEach(() => {
  apiFetchMock.mockReset();
});

afterEach(() => cleanup());

describe("ThesisContentPage", () => {
  it("mount'ta manuscript GET cagirir + 5 bolum render", async () => {
    apiFetchMock.mockResolvedValueOnce(manuscriptStubEmpty);
    render(<ThesisContentPage />);

    await waitFor(() => {
      expect(screen.getByText("Giriş")).toBeTruthy();
    });
    expect(screen.getByText("Yöntem")).toBeTruthy();
    expect(screen.getByText("Bulgular")).toBeTruthy();
    expect(screen.getByText("Tartışma")).toBeTruthy();
    expect(screen.getByText("Sonuç")).toBeTruthy();

    const paths = apiFetchMock.mock.calls.map((c) => c[0] as string);
    expect(paths.some((p) => p.startsWith("/api/workshop/manuscript?project_id="))).toBe(true);
  });

  it("gate_open=true iken 6.2 kapisi acik rozeti render", async () => {
    apiFetchMock.mockResolvedValueOnce(manuscriptStubOpenGate);
    render(<ThesisContentPage />);
    await waitFor(() => expect(screen.getByText(/6\.2 Savunma kapısı açık/)).toBeTruthy());
    expect(screen.getByText(/Doluluk: 3\/5 bölüm/)).toBeTruthy();
  });

  it("quality_blocked=true iken sahte rozet + sebep render", async () => {
    apiFetchMock.mockResolvedValueOnce(manuscriptStubBlocked);
    render(<ThesisContentPage />);
    await waitFor(() => expect(screen.getByText(/Kalite engeli/)).toBeTruthy());
    expect(screen.getByText(/Lorem ipsum tespit edildi/)).toBeTruthy();
    expect(screen.getByText(/Kalite: sahte/)).toBeTruthy();
  });

  it("textarea edit + Kaydet → PUT /manuscript/intro", async () => {
    apiFetchMock.mockResolvedValueOnce(manuscriptStubEmpty);
    render(<ThesisContentPage />);
    await waitFor(() => expect(screen.getByText("Giriş")).toBeTruthy());

    const introTextarea = screen.getByLabelText(/Giriş içerik/i) as HTMLTextAreaElement;
    fireEvent.change(introTextarea, { target: { value: "Yeni giriş içeriği." } });

    apiFetchMock.mockResolvedValueOnce(upsertResultStub);
    apiFetchMock.mockResolvedValueOnce(manuscriptStubEmpty);

    const saveBtns = screen.getAllByRole("button", { name: /Kaydet/i });
    fireEvent.click(saveBtns[0]!);

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/api/workshop/manuscript/intro",
        expect.objectContaining({
          method: "PUT",
          body: expect.objectContaining({
            project_id: PROJECT_ID,
            content: "Yeni giriş içeriği.",
          }),
        }),
      );
    });
  });

  it("Kalite kontrolu → POST /quality-check", async () => {
    apiFetchMock.mockResolvedValueOnce(manuscriptStubOpenGate);
    render(<ThesisContentPage />);
    await waitFor(() => expect(screen.getByText(/Doluluk: 3\/5/)).toBeTruthy());

    apiFetchMock.mockResolvedValueOnce(qualityResultStub);
    apiFetchMock.mockResolvedValueOnce(manuscriptStubOpenGate);

    const qBtns = screen.getAllByRole("button", { name: /Kalite kontrolü/i });
    fireEvent.click(qBtns[0]!);

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/api/workshop/manuscript/quality-check",
        expect.objectContaining({
          method: "POST",
          body: expect.objectContaining({
            project_id: PROJECT_ID,
            section_type: "intro",
          }),
        }),
      );
    });
  });

  it("Taslak cikar → POST /auto-draft → preview modal + Editore yapistir textarea'yi gunceller", async () => {
    apiFetchMock.mockResolvedValueOnce(manuscriptStubEmpty);
    render(<ThesisContentPage />);
    await waitFor(() => expect(screen.getByText("Yöntem")).toBeTruthy());

    apiFetchMock.mockResolvedValueOnce(autoDraftStub);

    const draftBtns = screen.getAllByRole("button", { name: /Taslak çıkar/i });
    // methods = 2. butona tikla (intro=0, methods=1)
    fireEvent.click(draftBtns[1]!);

    await waitFor(() => {
      expect(screen.getByText(/Otomatik taslak — Yöntem/)).toBeTruthy();
      expect(screen.getByText(/Otomatik taslak: yöntem bölümü/)).toBeTruthy();
      expect(screen.getByText(/Kaynak adımlar: 3\.3, 4\.2/)).toBeTruthy();
    });

    expect(apiFetchMock).toHaveBeenCalledWith(
      "/api/workshop/manuscript/auto-draft",
      expect.objectContaining({
        method: "POST",
        body: expect.objectContaining({
          project_id: PROJECT_ID,
          section_type: "methods",
        }),
      }),
    );

    fireEvent.click(screen.getByRole("button", { name: /Editöre yapıştır/i }));
    await waitFor(() => {
      const methodsTextarea = screen.getByLabelText(/Yöntem içerik/i) as HTMLTextAreaElement;
      expect(methodsTextarea.value).toBe("Otomatik taslak: yöntem bölümü için 1 paragraf.");
    });
  });
});
