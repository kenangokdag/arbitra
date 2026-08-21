// FAZ 4B — tema uygulama + WCAG kontrast çekirdeği (saf, test edilebilir).
// ThemeProvider ve /admin/theme bu modülü tüketir; ağ/DOM yan etkisi yalnız
// applyTheme'de (verilen element üzerinde). Bilinmeyen değer → SESSİZCE yok say
// (uygulama ASLA kırılmaz; globals.css varsayılanı kalır).

import type {
  FontSansKey,
  FontSerifKey,
  ThemeSettings,
} from "./review-api";

// #RRGGBB — backend api/models/theme.py:31 ile aynı sözleşme.
const HEX_RE = /^#[0-9a-fA-F]{6}$/;

export function isHexColor(value: string): boolean {
  return HEX_RE.test(value);
}

// Font anahtarı → CSS değer (yüklü next/font değişkeni + güvenli fallback zinciri).
// Değerler globals.css:46-48 --font-sans/--font-serif tanımlarıyla hizalı.
export const FONT_SANS_MAP: Record<FontSansKey, string> = {
  inter: 'var(--font-inter), system-ui, -apple-system, "Segoe UI", sans-serif',
  "source-sans":
    'var(--font-source-sans), system-ui, -apple-system, "Segoe UI", sans-serif',
};

export const FONT_SERIF_MAP: Record<FontSerifKey, string> = {
  lora: "var(--font-lora), Georgia, serif",
  newsreader: "var(--font-newsreader), Georgia, serif",
  "source-serif": "var(--font-source-serif), Georgia, serif",
};

// Select etiketleri (insan-okur ad — UYDURMA YOK, Google Fonts resmi adları).
export const FONT_SANS_LABELS: Record<FontSansKey, string> = {
  inter: "Inter",
  "source-sans": "Source Sans 3",
};

export const FONT_SERIF_LABELS: Record<FontSerifKey, string> = {
  lora: "Lora",
  newsreader: "Newsreader",
  "source-serif": "Source Serif 4",
};

// Kod-varsayılanı — globals.css değerleriyle BİREBİR (FOUC minimal: seed = mevcut tema).
export const DEFAULT_THEME: ThemeSettings = {
  accent_color: "#4F46E5",
  bg_color: "#f8fafc",
  ink_color: "#0f172a",
  font_sans: "inter",
  font_serif: "lora",
};

/**
 * Temayı bir element (genelde document.documentElement) üzerine uygular.
 * Her alan TEK TEK doğrulanır: geçersiz hex / bilinmeyen font anahtarı → o alan
 * ATLANIR (setProperty çağrılmaz → globals.css varsayılanı kalır). Hiçbir durumda
 * exception fırlatmaz; kısmen geçerli tema kısmen uygulanır.
 */
export function applyTheme(el: HTMLElement, theme: ThemeSettings): void {
  const { style } = el;

  if (isHexColor(theme.accent_color)) {
    style.setProperty("--color-accent", theme.accent_color);
  }
  if (isHexColor(theme.bg_color)) {
    style.setProperty("--color-bg", theme.bg_color);
  }
  if (isHexColor(theme.ink_color)) {
    style.setProperty("--color-ink", theme.ink_color);
  }

  const sans = FONT_SANS_MAP[theme.font_sans];
  if (sans) style.setProperty("--font-sans", sans);

  const serif = FONT_SERIF_MAP[theme.font_serif];
  if (serif) style.setProperty("--font-serif", serif);
}

// --- WCAG 2.x kontrast (relative luminance) --------------------------------
// Kaynak: WCAG 2.1 "relative luminance" + "contrast ratio" tanımı.

function hexToRgb(hex: string): [number, number, number] | null {
  if (!isHexColor(hex)) return null;
  const n = Number.parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function channelLuminance(c: number): number {
  const s = c / 255;
  return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
}

/** Relative luminance (0..1) veya geçersiz hex'te null. */
export function relativeLuminance(hex: string): number | null {
  const rgb = hexToRgb(hex);
  if (!rgb) return null;
  const r = channelLuminance(rgb[0]);
  const g = channelLuminance(rgb[1]);
  const b = channelLuminance(rgb[2]);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** İki renk arasındaki WCAG kontrast oranı (1..21) veya geçersiz girdide null. */
export function contrastRatio(fg: string, bg: string): number | null {
  const l1 = relativeLuminance(fg);
  const l2 = relativeLuminance(bg);
  if (l1 === null || l2 === null) return null;
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

// WCAG AA eşikleri: normal metin ≥ 4.5, büyük metin / UI bileşeni ≥ 3.
export const WCAG_AA_TEXT = 4.5;
export const WCAG_AA_UI = 3;
