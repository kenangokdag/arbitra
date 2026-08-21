import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { DefenseFormatPage } from "./DefenseFormatPage";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
  useParams: () => ({ id: "demo-project" }),
}));

const apiFetchMock = vi.fn();

vi.mock("@/lib/api", () => ({
  apiFetch: (path: string, opts?: unknown) => apiFetchMock(path, opts),
  ApiError: class ApiError extends Error {
    status = 0;
    detail: unknown = null;
  },
}));

const sessionStub = {
  id: "sess-1",
  project_id: "demo-project",
  session_type: "tez" as const,
  scheduled_date: null,
  jury_size: 5,
  title: "Tez X",
  field: "Yöneylem",
  preferred_lang: "tr" as const,
  jury_members: [],
  question_pool: [],
};

const suggestStub = {
  project_id: "demo-project",
  field: "Yöneylem",
  suggestions: [
    {
      name: "Dr. Ali Veli",
      affiliation: "Boğaziçi Üniv.",
      paper_count: 12,
      total_citations: 340,
      top_paper_ids: ["p1", "p2"],
    },
  ],
};

beforeEach(() => {
  apiFetchMock.mockReset();
});

afterEach(() => cleanup());

describe("DefenseFormatPage — static UI", () => {
  it("renders thesis as default selected format with 5 timeline rows", () => {
    render(<DefenseFormatPage />);
    const thesisCard = screen.getByRole("button", { name: /Tez Savunmasi/i });
    expect(thesisCard.getAttribute("aria-pressed")).toBe("true");
    expect(screen.getByText(/Tez Savunmasi Akisi \(90 dk\)/i)).toBeTruthy();
    expect(screen.getAllByText(/^\d+-\d+ dk$/).length).toBe(5);
  });

  it("switches timeline rows + jury readout when qualifying is selected", () => {
    render(<DefenseFormatPage />);
    fireEvent.click(screen.getByRole("button", { name: /Yeterlilik Sinavi/i }));
    expect(screen.getByText(/Yeterlilik Sinavi Akisi \(30 dk\)/i)).toBeTruthy();
    expect(screen.getByText(/3 juri uyesi/i)).toBeTruthy();
    expect(screen.getAllByText(/^\d+-\d+ dk$/).length).toBe(5);
  });

  it("conference format shows 4 timeline rows + open audience", () => {
    render(<DefenseFormatPage />);
    fireEvent.click(screen.getByRole("button", { name: /Konferans Bildirisi/i }));
    expect(screen.getByText(/Konferans Bildirisi Akisi \(20 dk\)/i)).toBeTruthy();
    expect(screen.getByText(/Acik dinleyici/i)).toBeTruthy();
    expect(screen.getAllByText(/^\d+-\d+ dk$/).length).toBe(4);
  });
});

describe("DefenseFormatPage — endpoint binding", () => {
  it("kaydet butonu title/field bos iken disabled", () => {
    render(<DefenseFormatPage />);
    const btn = screen.getByRole("button", { name: /Oturumu Kaydet/i }) as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
  });

  it("title+field doldurulunca saveSession POST atar ve session bilgisi gosterilir", async () => {
    apiFetchMock.mockResolvedValueOnce(sessionStub);
    render(<DefenseFormatPage />);

    const titleInput = screen.getByPlaceholderText(/Bibliometric/i);
    const fieldInput = screen.getByPlaceholderText(/Isletme/i);
    fireEvent.change(titleInput, { target: { value: "Tez X" } });
    fireEvent.change(fieldInput, { target: { value: "Yöneylem" } });

    fireEvent.click(screen.getByRole("button", { name: /Oturumu Kaydet/i }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/api/workshop/defense/session",
        expect.objectContaining({ method: "POST" }),
      );
    });

    await waitFor(() => {
      expect(screen.getByText(/0\/5 juri uyesi/i)).toBeTruthy();
    });
  });

  it("session sonrasi Oneri Al cagrisi suggest-jury GET atar", async () => {
    apiFetchMock.mockResolvedValueOnce(sessionStub);
    render(<DefenseFormatPage />);
    fireEvent.change(screen.getByPlaceholderText(/Bibliometric/i), {
      target: { value: "Tez X" },
    });
    fireEvent.change(screen.getByPlaceholderText(/Isletme/i), {
      target: { value: "Yöneylem" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Oturumu Kaydet/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Oneri Al/i })).toBeTruthy();
    });

    apiFetchMock.mockResolvedValueOnce(suggestStub);
    fireEvent.click(screen.getByRole("button", { name: /Oneri Al/i }));

    await waitFor(() => {
      expect(screen.getByText(/Dr\. Ali Veli/)).toBeTruthy();
      expect(screen.getByText(/Bogazici|Boğaziçi/)).toBeTruthy();
    });

    const paths = apiFetchMock.mock.calls.map((c) => c[0] as string);
    expect(paths.some((p) => p.startsWith("/api/workshop/defense/suggest-jury"))).toBe(true);
    expect(paths.some((p) => p.includes("field=Y%C3%B6neylem"))).toBe(true);
  });

  it("hata durumunda banner gosterilir", async () => {
    apiFetchMock.mockRejectedValueOnce(new Error("500: db_error"));
    render(<DefenseFormatPage />);
    fireEvent.change(screen.getByPlaceholderText(/Bibliometric/i), {
      target: { value: "Tez X" },
    });
    fireEvent.change(screen.getByPlaceholderText(/Isletme/i), {
      target: { value: "Yöneylem" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Oturumu Kaydet/i }));

    await waitFor(() => {
      expect(screen.getByText(/Oturum kaydedilemedi|db_error/)).toBeTruthy();
    });
  });
});
