// FAZ 4B — ThemeProvider: tema gelince document.documentElement'e setProperty
// uygulanır; veri-yok/hata-durumunda HİÇBİR şey uygulanmaz (uygulama kırılmaz).
// "Gördüm" kanıtı: setProperty spy'ı + render edilen children (browser yok).

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import { ThemeProvider } from "./ThemeProvider";
import type { ThemeSettings } from "@/lib/review-api";

// useTheme'i mock'la — ağ yok, deterministik. data'yı test başına değiştiririz.
vi.mock("@/hooks/useReview", () => ({ useTheme: vi.fn() }));
import { useTheme } from "@/hooks/useReview";
const mockUseTheme = vi.mocked(useTheme);

const THEME: ThemeSettings = {
  accent_color: "#aa0000",
  bg_color: "#ffffff",
  ink_color: "#111111",
  font_sans: "source-sans",
  font_serif: "newsreader",
};

describe("ThemeProvider", () => {
  let setSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    // Önceki testlerin bıraktığı inline değişkenleri temizle.
    document.documentElement.removeAttribute("style");
    setSpy = vi.spyOn(document.documentElement.style, "setProperty");
  });

  afterEach(() => {
    setSpy.mockRestore();
    mockUseTheme.mockReset();
  });

  it("tema gelince renk + font CSS değişkenlerini setProperty ile uygular", () => {
    mockUseTheme.mockReturnValue({ data: THEME } as ReturnType<typeof useTheme>);

    render(
      <ThemeProvider>
        <span>içerik</span>
      </ThemeProvider>,
    );

    expect(screen.getByText("içerik")).toBeInTheDocument();
    expect(setSpy).toHaveBeenCalledWith("--color-accent", "#aa0000");
    expect(setSpy).toHaveBeenCalledWith("--color-bg", "#ffffff");
    expect(setSpy).toHaveBeenCalledWith("--color-ink", "#111111");
    expect(setSpy).toHaveBeenCalledWith(
      "--font-sans",
      expect.stringContaining("var(--font-source-sans)"),
    );
    expect(setSpy).toHaveBeenCalledWith(
      "--font-serif",
      expect.stringContaining("var(--font-newsreader)"),
    );
  });

  it("veri yokken (loading/hata) hiçbir setProperty çağrılmaz, children yine render edilir", () => {
    mockUseTheme.mockReturnValue({ data: undefined } as ReturnType<
      typeof useTheme
    >);

    render(
      <ThemeProvider>
        <span>içerik</span>
      </ThemeProvider>,
    );

    expect(screen.getByText("içerik")).toBeInTheDocument();
    expect(setSpy).not.toHaveBeenCalled();
  });
});
