// FAZ 4B — saf tema çekirdeği: kontrast (WCAG), applyTheme (bilinmeyen→atla),
// font map bütünlüğü.

import { describe, expect, it } from "vitest";

import {
  applyTheme,
  contrastRatio,
  FONT_SANS_MAP,
  FONT_SERIF_MAP,
  isHexColor,
  relativeLuminance,
} from "./theme";
import type { ThemeSettings } from "./review-api";

describe("isHexColor", () => {
  it("yalnız #RRGGBB kabul eder", () => {
    expect(isHexColor("#4F46E5")).toBe(true);
    expect(isHexColor("#abc")).toBe(false); // kısa hex reddedilir
    expect(isHexColor("rgb(0,0,0)")).toBe(false);
    expect(isHexColor("4F46E5")).toBe(false);
  });
});

describe("contrastRatio (WCAG)", () => {
  it("siyah/beyaz tam 21:1", () => {
    expect(contrastRatio("#000000", "#ffffff")).toBeCloseTo(21, 1);
  });

  it("aynı renk 1:1", () => {
    expect(contrastRatio("#777777", "#777777")).toBeCloseTo(1, 5);
  });

  it("sıra fark etmez (simetrik)", () => {
    const a = contrastRatio("#0f172a", "#f8fafc");
    const b = contrastRatio("#f8fafc", "#0f172a");
    expect(a).toBeCloseTo(b ?? -1, 6);
  });

  it("geçersiz hex → null", () => {
    expect(contrastRatio("#zzz", "#ffffff")).toBeNull();
    expect(relativeLuminance("nope")).toBeNull();
  });

  it("varsayılan ink/bg AA metin eşiğini (4.5) geçer", () => {
    const r = contrastRatio("#0f172a", "#f8fafc");
    expect(r).not.toBeNull();
    expect(r as number).toBeGreaterThanOrEqual(4.5);
  });
});

describe("applyTheme", () => {
  function makeEl(): HTMLElement {
    return document.createElement("div");
  }

  it("geçerli temayı CSS değişkenlerine yazar", () => {
    const el = makeEl();
    const theme: ThemeSettings = {
      accent_color: "#123456",
      bg_color: "#abcdef",
      ink_color: "#0a0a0a",
      font_sans: "source-sans",
      font_serif: "source-serif",
    };
    applyTheme(el, theme);
    expect(el.style.getPropertyValue("--color-accent")).toBe("#123456");
    expect(el.style.getPropertyValue("--color-bg")).toBe("#abcdef");
    expect(el.style.getPropertyValue("--color-ink")).toBe("#0a0a0a");
    expect(el.style.getPropertyValue("--font-sans")).toContain(
      "var(--font-source-sans)",
    );
    expect(el.style.getPropertyValue("--font-serif")).toContain(
      "var(--font-source-serif)",
    );
  });

  it("geçersiz renk + bilinmeyen font anahtarı SESSİZCE atlanır (varsayılan korunur)", () => {
    const el = makeEl();
    const bad = {
      accent_color: "not-a-color",
      bg_color: "#ffffff",
      ink_color: "#000000",
      font_sans: "comic-sans", // allowlist dışı
      font_serif: "lora",
    } as unknown as ThemeSettings;
    applyTheme(el, bad);
    // geçersiz accent yazılmadı
    expect(el.style.getPropertyValue("--color-accent")).toBe("");
    // bilinmeyen sans yazılmadı
    expect(el.style.getPropertyValue("--font-sans")).toBe("");
    // geçerli alanlar yazıldı
    expect(el.style.getPropertyValue("--color-bg")).toBe("#ffffff");
    expect(el.style.getPropertyValue("--font-serif")).toContain(
      "var(--font-lora)",
    );
  });
});

describe("font map bütünlüğü", () => {
  it("her sans/serif anahtarı next/font değişkenine MAP edilir", () => {
    expect(FONT_SANS_MAP.inter).toContain("var(--font-inter)");
    expect(FONT_SANS_MAP["source-sans"]).toContain("var(--font-source-sans)");
    expect(FONT_SERIF_MAP.lora).toContain("var(--font-lora)");
    expect(FONT_SERIF_MAP.newsreader).toContain("var(--font-newsreader)");
    expect(FONT_SERIF_MAP["source-serif"]).toContain(
      "var(--font-source-serif)",
    );
  });
});
