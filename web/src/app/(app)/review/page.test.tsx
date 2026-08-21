// F14 Hakemlik — yükleme sayfası gizlilik/rıza kontrolleri (SEC-2 / FAZ E2).
// Doğruladığı iki şey: (1) seçilen gizlilik alanları uploadReview'a backend
// Form adlarıyla (is_author/confidentiality_mode/external_ai_consent/
// retention_days) gider; (2) gizli + rıza-yok seçilince DÜRÜST
// "deterministik-only" açıklaması görünür (consent_gate gerçek davranışı).

import { afterEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";

const pushMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

const uploadReviewMock = vi.fn();
// VERSIYON_KARSILASTIRMA_FAZ1_2026-08-17: page.tsx mount'ta fetchMyReviewJobs
// çağırıyor — mock'lanmazsa "is not a function" ile çöker. Boş liste →
// önceki-versiyon seçici hiç render edilmez (mevcut testlerin varsayımı bozulmaz).
const fetchMyReviewJobsMock = vi.fn().mockResolvedValue({ jobs: [] });
vi.mock("@/lib/review-api", () => ({
  uploadReview: (args: unknown) => uploadReviewMock(args),
  fetchMyReviewJobs: (...args: unknown[]) => fetchMyReviewJobsMock(...args),
}));

// REVIEW_ONBOARDING_TURU_2026-08-17: bu dosyanın testleri upload akışını
// doğrular, turu DEĞİL — hasSeenReviewTour varsayılan olarak true (tur hiç
// açılmaz). Tur-özel davranış aşağıdaki AYRI describe bloğunda, kendi
// mock'uyla test edilir.
const hasSeenReviewTourMock = vi.fn().mockReturnValue(true);
const markReviewTourSeenMock = vi.fn();
vi.mock("@/lib/reviewTourPreference", () => ({
  hasSeenReviewTour: () => hasSeenReviewTourMock(),
  markReviewTourSeen: () => markReviewTourSeenMock(),
}));

import ReviewUploadPage from "./page";

afterEach(() => {
  cleanup();
  pushMock.mockReset();
  uploadReviewMock.mockReset();
  fetchMyReviewJobsMock.mockReset();
  hasSeenReviewTourMock.mockReset();
  hasSeenReviewTourMock.mockReturnValue(true);
  markReviewTourSeenMock.mockReset();
  fetchMyReviewJobsMock.mockResolvedValue({ jobs: [] });
});

function attachFile() {
  const input = document.querySelector(
    'input[type="file"]',
  ) as HTMLInputElement;
  const file = new File(["%PDF-1.7 body"], "paper.pdf", {
    type: "application/pdf",
  });
  fireEvent.change(input, { target: { files: [file] } });
  return file;
}

describe("ReviewUploadPage — gizlilik/rıza", () => {
  it("gizli hakemlik + rıza-yok seçilince açıklamayı gösterir ve doğru alanları gönderir", async () => {
    uploadReviewMock.mockResolvedValue({ job_id: "job-1", status: "queued" });
    render(<ReviewUploadPage />);

    const file = attachFile();

    // "Başkasının makalesi" → is_author=false + gizlilik=reviewer_confidential
    // + güvenli default consent=blocked (consent_gate aynası).
    fireEvent.click(screen.getByText("Başkasının makalesi"));

    // Gizli + rıza-yok → dürüst deterministik-only açıklaması görünür.
    expect(
      screen.getByText(/harici yapay zekâ varsayılan olarak/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/hakem-paneli \(LLM\) yargısı çalıştırılmaz/i),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByText("İncelemeyi başlat"));

    await waitFor(() => expect(uploadReviewMock).toHaveBeenCalledTimes(1));
    const arg = uploadReviewMock.mock.calls[0]![0];
    expect(arg).toMatchObject({
      file,
      isAuthor: false,
      confidentialityMode: "reviewer_confidential",
      externalAiConsent: "blocked",
      retentionDays: 30,
    });
    await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/review/job-1"));
  });

  it("yazar akışında author_owned + allowed gönderir (backend default'larıyla aynı)", async () => {
    uploadReviewMock.mockResolvedValue({ job_id: "job-2", status: "queued" });
    render(<ReviewUploadPage />);

    attachFile();
    fireEvent.click(screen.getByText("İncelemeyi başlat"));

    await waitFor(() => expect(uploadReviewMock).toHaveBeenCalledTimes(1));
    expect(uploadReviewMock.mock.calls[0]![0]).toMatchObject({
      isAuthor: true,
      confidentialityMode: "author_owned",
      externalAiConsent: "allowed",
      retentionDays: 30,
    });
  });

  it("gizli makalede açıkça 'İzin ver' seçilince deterministik-only uyarısı kaybolur", () => {
    render(<ReviewUploadPage />);
    attachFile();

    fireEvent.click(screen.getByText("Başkasının makalesi"));
    expect(
      screen.getByText(/hakem-paneli \(LLM\) yargısı çalıştırılmaz/i),
    ).toBeInTheDocument();

    // "İzin ver" rıza seçeneği → harici YZ çalışır, deterministik-only kalkar.
    fireEvent.click(screen.getByText("İzin ver"));
    expect(
      screen.queryByText(/hakem-paneli \(LLM\) yargısı çalıştırılmaz/i),
    ).not.toBeInTheDocument();
    // Gizli + açık rıza → politika uyarısı görünür.
    expect(
      screen.getByText(/harici yapay zekâ sağlayıcılara gönderilecek/i),
    ).toBeInTheDocument();
  });

  it("çift gönderimi kilitler (submitting iken ikinci tık yeni çağrı yapmaz)", async () => {
    let resolveUpload: (v: { job_id: string; status: string }) => void = () => {};
    uploadReviewMock.mockImplementation(
      () =>
        new Promise((r) => {
          resolveUpload = r;
        }),
    );
    render(<ReviewUploadPage />);
    attachFile();

    const startBtn = screen
      .getByText("İncelemeyi başlat")
      .closest("button") as HTMLButtonElement;
    fireEvent.click(startBtn); // 1. tık → submitting=true → buton disabled
    fireEvent.click(startBtn); // 2. tık → disabled, onClick tetiklenmez

    await waitFor(() => expect(uploadReviewMock).toHaveBeenCalledTimes(1));
    resolveUpload({ job_id: "job-3", status: "queued" });
  });
});

describe("ReviewUploadPage — önceki versiyon seçici (VERSIYON_KARSILASTIRMA_FAZ1_2026-08-17)", () => {
  it("geçmiş job yoksa seçici HİÇ render edilmez (ilk yükleme deneyimi bozulmaz)", async () => {
    fetchMyReviewJobsMock.mockResolvedValue({ jobs: [] });
    render(<ReviewUploadPage />);
    await waitFor(() => expect(fetchMyReviewJobsMock).toHaveBeenCalled());
    expect(screen.queryByLabelText(/önceki bir versiyonu var mı/i)).toBeNull();
  });

  it("geçmiş job'lar varsa seçici görünür, varsayılan seçim 'yeni makale'dir", async () => {
    fetchMyReviewJobsMock.mockResolvedValue({
      jobs: [
        {
          job_id: "old-job-1",
          mode: "author",
          language: "tr",
          status: "done",
          source_name: "eski-makale-v1.pdf",
          source_kind: "pdf",
          created_at: "2026-08-01T00:00:00Z",
          updated_at: "2026-08-01T00:00:00Z",
        },
      ],
    });
    render(<ReviewUploadPage />);

    const select = await screen.findByLabelText(/önceki bir versiyonu var mı/i);
    expect((select as HTMLSelectElement).value).toBe("");
    expect(screen.getByText(/eski-makale-v1\.pdf/)).toBeInTheDocument();
  });

  it("kullanıcı önceki versiyonu seçerse parentJobId uploadReview'a gider", async () => {
    fetchMyReviewJobsMock.mockResolvedValue({
      jobs: [
        {
          job_id: "old-job-1",
          mode: "author",
          language: "tr",
          status: "done",
          source_name: "eski-makale-v1.pdf",
          source_kind: "pdf",
          created_at: "2026-08-01T00:00:00Z",
          updated_at: "2026-08-01T00:00:00Z",
        },
      ],
    });
    uploadReviewMock.mockResolvedValue({ job_id: "job-4", status: "queued" });
    render(<ReviewUploadPage />);

    attachFile();
    const select = await screen.findByLabelText(/önceki bir versiyonu var mı/i);
    fireEvent.change(select, { target: { value: "old-job-1" } });

    fireEvent.click(screen.getByText("İncelemeyi başlat"));

    await waitFor(() => expect(uploadReviewMock).toHaveBeenCalledTimes(1));
    expect(uploadReviewMock.mock.calls[0]![0]).toMatchObject({
      parentJobId: "old-job-1",
    });
  });

  it("seçim yapılmazsa (varsayılan 'yeni makale') parentJobId gönderilmez", async () => {
    fetchMyReviewJobsMock.mockResolvedValue({
      jobs: [
        {
          job_id: "old-job-1",
          mode: "author",
          language: "tr",
          status: "done",
          source_name: "eski-makale-v1.pdf",
          source_kind: "pdf",
          created_at: "2026-08-01T00:00:00Z",
          updated_at: "2026-08-01T00:00:00Z",
        },
      ],
    });
    uploadReviewMock.mockResolvedValue({ job_id: "job-5", status: "queued" });
    render(<ReviewUploadPage />);

    attachFile();
    await screen.findByLabelText(/önceki bir versiyonu var mı/i);
    fireEvent.click(screen.getByText("İncelemeyi başlat"));

    await waitFor(() => expect(uploadReviewMock).toHaveBeenCalledTimes(1));
    expect(uploadReviewMock.mock.calls[0]![0].parentJobId).toBeUndefined();
  });
});

describe("ReviewUploadPage — onboarding turu (REVIEW_ONBOARDING_TURU_2026-08-17)", () => {
  it("tercih yoksa (ilk giriş) tur otomatik açılır", async () => {
    hasSeenReviewTourMock.mockReturnValue(false);
    render(<ReviewUploadPage />);
    expect(
      await screen.findByTestId("review-onboarding-tour"),
    ).toBeInTheDocument();
  });

  it("tercih zaten VARSA tur açılmaz", () => {
    hasSeenReviewTourMock.mockReturnValue(true);
    render(<ReviewUploadPage />);
    expect(screen.queryByTestId("review-onboarding-tour")).toBeNull();
  });

  it("turu kapatmak markReviewTourSeen'i çağırır ve turu gizler", async () => {
    hasSeenReviewTourMock.mockReturnValue(false);
    render(<ReviewUploadPage />);
    await screen.findByTestId("review-onboarding-tour");

    fireEvent.click(screen.getByTestId("review-onboarding-tour-skip"));

    expect(markReviewTourSeenMock).toHaveBeenCalledTimes(1);
    expect(screen.queryByTestId("review-onboarding-tour")).toBeNull();
  });
});
