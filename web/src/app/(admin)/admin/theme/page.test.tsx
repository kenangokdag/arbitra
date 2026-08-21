// FAZ 4B — /admin/theme formu: 5 durum (idle/loading/success/error) + kontrast
// readout + submit→updateTheme çağrısı + yetkisiz (403) net mesaj.
// Hook'lar mock'lanır (ağ yok); "gördüm" kanıtı = render + etkileşim.

import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import AdminThemePage from "./page";
import { ApiError } from "@/lib/api";
import type { ThemeSettings } from "@/lib/review-api";

vi.mock("@/hooks/useReview", () => ({
  useTheme: vi.fn(),
  useUpdateTheme: vi.fn(),
}));
import { useTheme, useUpdateTheme } from "@/hooks/useReview";
const mockUseTheme = vi.mocked(useTheme);
const mockUseUpdateTheme = vi.mocked(useUpdateTheme);

const THEME: ThemeSettings = {
  accent_color: "#4F46E5",
  bg_color: "#f8fafc",
  ink_color: "#0f172a",
  font_sans: "inter",
  font_serif: "lora",
};

function themeQuery(over: Partial<ReturnType<typeof useTheme>> = {}) {
  return {
    data: THEME,
    isPending: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
    ...over,
  } as unknown as ReturnType<typeof useTheme>;
}

function mutationMock(over: Record<string, unknown> = {}) {
  return {
    mutate: vi.fn(),
    reset: vi.fn(),
    isPending: false,
    isError: false,
    isSuccess: false,
    error: null,
    ...over,
  } as unknown as ReturnType<typeof useUpdateTheme>;
}

afterEach(() => {
  mockUseTheme.mockReset();
  mockUseUpdateTheme.mockReset();
});

describe("AdminThemePage", () => {
  it("yükleniyor durumunda iskelet (skeleton) gösterir", () => {
    mockUseTheme.mockReturnValue(themeQuery({ data: undefined, isPending: true }));
    mockUseUpdateTheme.mockReturnValue(mutationMock());

    render(<AdminThemePage />);
    expect(screen.getByText("Tema yükleniyor…")).toBeInTheDocument();
  });

  it("yüklenince form + canlı önizleme + kontrast okuması render edilir (idle)", () => {
    mockUseTheme.mockReturnValue(themeQuery());
    mockUseUpdateTheme.mockReturnValue(mutationMock());

    render(<AdminThemePage />);

    // form alanları seed edilmiş
    expect(screen.getByLabelText("Vurgu rengi renk seçici")).toBeInTheDocument();
    expect(screen.getByLabelText(/Gövde yazı tipi/)).toBeInTheDocument();

    // canlı önizleme
    expect(screen.getByTestId("theme-preview")).toBeInTheDocument();

    // WCAG kontrast okuması — iki satır, oran + rozet
    expect(screen.getByText("Metin / Zemin")).toBeInTheDocument();
    expect(screen.getByText("Vurgu / Zemin")).toBeInTheDocument();
    // varsayılan ink/bg AA geçer
    const textRow = screen.getByText("Metin / Zemin").closest("div")
      ?.parentElement as HTMLElement;
    expect(within(textRow).getByText("geçer")).toBeInTheDocument();
  });

  it("submit → updateTheme.mutate doğru body ile çağrılır", async () => {
    const user = userEvent.setup();
    const mutate = vi.fn();
    mockUseTheme.mockReturnValue(themeQuery());
    mockUseUpdateTheme.mockReturnValue(mutationMock({ mutate }));

    render(<AdminThemePage />);

    // vurgu rengini değiştir (hex text input)
    // 3 hex text input sıralı: [accent, bg, ink] → ilki vurgu.
    const accentText = screen.getAllByPlaceholderText("#RRGGBB")[0]!;
    await user.clear(accentText);
    await user.type(accentText, "#112233");

    await user.click(screen.getByRole("button", { name: "Temayı kaydet" }));

    expect(mutate).toHaveBeenCalledTimes(1);
    expect(mutate).toHaveBeenCalledWith({
      accent_color: "#112233",
      bg_color: "#f8fafc",
      ink_color: "#0f172a",
      font_sans: "inter",
      font_serif: "lora",
    });
  });

  it("geçersiz hex → submit kilitli + uyarı, mutate çağrılmaz", async () => {
    const user = userEvent.setup();
    const mutate = vi.fn();
    mockUseTheme.mockReturnValue(themeQuery());
    mockUseUpdateTheme.mockReturnValue(mutationMock({ mutate }));

    render(<AdminThemePage />);

    // 3 hex text input sıralı: [accent, bg, ink] → ilki vurgu.
    const accentText = screen.getAllByPlaceholderText("#RRGGBB")[0]!;
    await user.clear(accentText);
    await user.type(accentText, "nope");

    expect(
      screen.getByText(/Renkler #RRGGBB biçiminde olmalı/),
    ).toBeInTheDocument();
    const save = screen.getByRole("button", { name: "Temayı kaydet" });
    expect(save).toBeDisabled();

    await user.click(save);
    expect(mutate).not.toHaveBeenCalled();
  });

  it("loading durumunda buton kilitli + 'Kaydediliyor…' (çift-submit engeli)", () => {
    mockUseTheme.mockReturnValue(themeQuery());
    mockUseUpdateTheme.mockReturnValue(mutationMock({ isPending: true }));

    render(<AdminThemePage />);
    const save = screen.getByRole("button", { name: /Kaydediliyor/ });
    expect(save).toBeDisabled();
  });

  it("başarı durumunda onay bildirimi gösterir", () => {
    mockUseTheme.mockReturnValue(themeQuery());
    mockUseUpdateTheme.mockReturnValue(mutationMock({ isSuccess: true }));

    render(<AdminThemePage />);
    expect(screen.getByText("Tema kaydedildi")).toBeInTheDocument();
  });

  it("403 → 'yöneticilere özel' mesajı (beyaz ekran değil)", () => {
    mockUseTheme.mockReturnValue(themeQuery());
    mockUseUpdateTheme.mockReturnValue(
      mutationMock({
        isError: true,
        error: new ApiError(403, { detail: "forbidden" }, "API 403"),
      }),
    );

    render(<AdminThemePage />);
    expect(
      screen.getByText("Bu sayfa yöneticilere özel"),
    ).toBeInTheDocument();
  });

  it("genel hata → mesaj gösterir (403 değil)", () => {
    mockUseTheme.mockReturnValue(themeQuery());
    mockUseUpdateTheme.mockReturnValue(
      mutationMock({
        isError: true,
        error: new ApiError(500, null, "API 500: sunucu hatası"),
      }),
    );

    render(<AdminThemePage />);
    expect(screen.getByText("Kaydedilemedi")).toBeInTheDocument();
    expect(screen.getByText("API 500: sunucu hatası")).toBeInTheDocument();
  });
});
