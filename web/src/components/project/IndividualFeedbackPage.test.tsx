import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { IndividualFeedbackPage } from "./IndividualFeedbackPage";

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

const SESSION_ID = "22222222-2222-2222-2222-222222222222";
const PROJECT_ID = "11111111-1111-1111-1111-111111111111";
const STORAGE_KEY = `defense_session:${PROJECT_ID}`;

const checklistStub = {
  version: "v1",
  language: "tr" as const,
  doc_type: "tez" as const,
  note: null,
  categories: [
    {
      id: "etik",
      label: "Etik Kurul",
      items: [
        {
          id: "etik-1",
          soru: "Etik kurul onayı alındı mı?",
          aciklama: "Veri toplama öncesi onay zorunlu.",
          evet_metin: "Evet, ek-1'de.",
          hayir_metin: "Hayır, alınmadı.",
          yapamadim_metin: "Başvurdum, bekliyor.",
          kritik: true,
          link: null,
        },
      ],
    },
  ],
};

const counterStub = {
  session_id: SESSION_ID,
  total_items_answered: 1,
  evet_count: 0,
  hayir_count: 1,
  yapamadim_count: 0,
  critical_blocked: true,
};

const journalsStub = {
  journals: [
    {
      journal_id: "j1",
      name: "JORS",
      indices: ["SSCI"],
      sjr_quartile: "Q1",
      scope_match: 0.81,
      source: "seed_json" as const,
    },
  ],
  source_attribution: ["seed_json"],
  fallback_used: true,
};

const feedbackStub = {
  session_id: SESSION_ID,
  feedback_paragraph: "Yöntem bölümü güçlü; etik kapısı hala açık değil — tezi savunmaya çıkmadan önce çözmelisiniz.",
  weak_areas: ["etik", "veri toplama"],
};

beforeEach(() => {
  apiFetchMock.mockReset();
  window.localStorage.clear();
});

afterEach(() => cleanup());

describe("IndividualFeedbackPage", () => {
  it("session yokken uyari banner gosterir + checklist GET cagrir", async () => {
    apiFetchMock.mockResolvedValueOnce(checklistStub);
    render(<IndividualFeedbackPage />);

    await waitFor(() => {
      expect(screen.getByText(/Etik kurul onayı alındı mı/)).toBeTruthy();
    });
    expect(screen.getByText(/5\.1 Savunma Formatı/)).toBeTruthy();

    const paths = apiFetchMock.mock.calls.map((c) => c[0] as string);
    expect(paths.some((p) => p.startsWith("/api/workshop/checklist"))).toBe(true);
    expect(paths.some((p) => p.includes("doc_type=tez"))).toBe(true);
    expect(paths.some((p) => p.includes("lang=tr"))).toBe(true);
  });

  it("docType degisince yeni checklist GET tetikler", async () => {
    apiFetchMock.mockResolvedValue(checklistStub);
    render(<IndividualFeedbackPage />);
    await waitFor(() => expect(screen.getByText(/Etik kurul onayı/)).toBeTruthy());

    apiFetchMock.mockClear();
    apiFetchMock.mockResolvedValue({ ...checklistStub, doc_type: "makale" });
    fireEvent.click(screen.getByRole("button", { name: /^Makale$/ }));

    await waitFor(() => {
      const paths = apiFetchMock.mock.calls.map((c) => c[0] as string);
      expect(paths.some((p) => p.includes("doc_type=makale"))).toBe(true);
    });
  });

  it("session varken radio tikla → PUT individual-check + critical_blocked banner", async () => {
    window.localStorage.setItem(STORAGE_KEY, SESSION_ID);
    apiFetchMock.mockResolvedValueOnce(checklistStub);
    render(<IndividualFeedbackPage />);
    await waitFor(() => expect(screen.getByText(/Etik kurul onayı/)).toBeTruthy());

    apiFetchMock.mockResolvedValueOnce(counterStub);
    fireEvent.click(screen.getByRole("button", { name: /^Hayır$/ }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/workshop/individual-check"),
        expect.objectContaining({
          method: "PUT",
          body: expect.objectContaining({
            session_id: SESSION_ID,
            checklist_id: "etik",
            item_id: "etik-1",
            response: "hayir",
          }),
        }),
      );
    });

    await waitFor(() => {
      expect(screen.getByText(/Kritik kapı kapalı/)).toBeTruthy();
    });
  });

  it("Dergi öner butonu journal-suggest GET cagirir + listeyi render eder", async () => {
    apiFetchMock.mockResolvedValueOnce(checklistStub);
    render(<IndividualFeedbackPage />);
    await waitFor(() => expect(screen.getByText(/Etik kurul onayı/)).toBeTruthy());

    apiFetchMock.mockResolvedValueOnce(journalsStub);
    fireEvent.click(screen.getByRole("button", { name: /Dergi öner/i }));

    await waitFor(() => {
      expect(screen.getByText("JORS")).toBeTruthy();
      expect(screen.getByText(/81% scope/)).toBeTruthy();
    });

    const paths = apiFetchMock.mock.calls.map((c) => c[0] as string);
    expect(paths.some((p) => p.startsWith("/api/workshop/journal-suggest"))).toBe(true);
    expect(paths.some((p) => p.includes(`project_id=${PROJECT_ID}`))).toBe(true);
  });

  it("Geri-bildirim al → personal-feedback POST + paragraf + weak_areas", async () => {
    window.localStorage.setItem(STORAGE_KEY, SESSION_ID);
    apiFetchMock.mockResolvedValueOnce(checklistStub);
    render(<IndividualFeedbackPage />);
    await waitFor(() => expect(screen.getByText(/Etik kurul onayı/)).toBeTruthy());

    apiFetchMock.mockResolvedValueOnce(feedbackStub);
    fireEvent.click(screen.getByRole("button", { name: /Geri-bildirim al/i }));

    await waitFor(() => {
      expect(screen.getByText(/Yöntem bölümü güçlü/)).toBeTruthy();
      expect(screen.getByText("etik")).toBeTruthy();
      expect(screen.getByText("veri toplama")).toBeTruthy();
    });

    expect(apiFetchMock).toHaveBeenCalledWith(
      "/api/workshop/personal-feedback",
      expect.objectContaining({
        method: "POST",
        body: expect.objectContaining({
          project_id: PROJECT_ID,
          session_id: SESSION_ID,
          doc_type: "tez",
          lang: "tr",
        }),
      }),
    );
  });

  it("session yok iken geri-bildirim butonu disabled", async () => {
    apiFetchMock.mockResolvedValueOnce(checklistStub);
    render(<IndividualFeedbackPage />);
    await waitFor(() => expect(screen.getByText(/Etik kurul onayı/)).toBeTruthy());
    const btn = screen.getByRole("button", { name: /Geri-bildirim al/i }) as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
  });
});
