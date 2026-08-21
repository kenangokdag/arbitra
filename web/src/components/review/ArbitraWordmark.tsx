// ARBITRA wordmark — sakin/otoriter marka vurgusu (design-language "verdict" sesi).
// Serif (font-display), hafif letter-spacing. Aksan VERİDE değil; yalnız markanın
// son harfinde ölçülü bir imza tonu. Gradyan/glow/parıltı YOK (design-language §8).
// Boyut prop'lu, tekrar kullanılır.

import { BRAND } from "@/lib/brand";

const SIZES = {
  sm: "text-[15px]",
  md: "text-[20px]",
  lg: "text-[28px]",
  xl: "text-[40px]",
} as const;

export type ArbitraWordmarkSize = keyof typeof SIZES;

export function ArbitraWordmark({
  size = "md",
  className = "",
}: {
  size?: ArbitraWordmarkSize;
  className?: string;
}) {
  return (
    <span
      className={`font-display font-medium tracking-[0.04em] text-ink ${SIZES[size]} ${className}`}
      aria-label={BRAND}
    >
      {/* ölçülü aksan imzası: yalnız son harf — calm, dekoratif değil */}
      {BRAND.slice(0, -1)}
      <span style={{ color: "var(--color-accent)" }}>{BRAND.slice(-1)}</span>
    </span>
  );
}
