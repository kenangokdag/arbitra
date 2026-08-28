"use client";

/* ============================================================
   SplashOverlay — Arbitra calm curtain-raise (de-branded).
   ------------------------------------------------------------
   Eski animasyonlu logo bağımlılığı kaldırıldı. Yerine sakin/
   otoriter bir ArbitraWordmark açılışı (design-language "verdict"
   sesi): gradyan/glow YOK, tek aksan ince bir kural.

   Repo deseni (SimulationCurtain): ref + sınıf/stil ile sürülür,
   setState YOK → react-hooks/set-state-in-effect tetiklenmez.
   İlk render statik (overlay görünür) → SSR-safe, hydration mismatch
   yok. Session başına bir kez (sessionStorage). prefers-reduced-motion:
   global CSS transition süresini 0.01ms'e indirir + hold kısaltılır.
   ============================================================ */

import { useEffect, useRef } from "react";
import { ArbitraWordmark } from "@/components/review/ArbitraWordmark";
import { BRAND_TAGLINE_TR } from "@/lib/brand";

const SESSION_KEY = "arbitra_splash_seen";
const HOLD_MS = 1100;
const FADE_OUT_MS = 420;

export function SplashOverlay() {
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const node = overlayRef.current;
    if (!node) return;

    const seen = window.sessionStorage.getItem(SESSION_KEY) === "1";
    if (seen) {
      node.style.display = "none";
      return;
    }
    try {
      window.sessionStorage.setItem(SESSION_KEY, "1");
    } catch {
      /* sessionStorage engelli — overlay yine de kapanır */
    }

    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const hold = reduce ? 200 : HOLD_MS;

    let t2: number | undefined;
    const t1 = window.setTimeout(() => {
      node.style.opacity = "0";
      node.style.pointerEvents = "none";
      t2 = window.setTimeout(() => {
        node.style.display = "none";
      }, FADE_OUT_MS);
    }, hold);

    return () => {
      window.clearTimeout(t1);
      if (t2) window.clearTimeout(t2);
    };
  }, []);

  return (
    <div
      ref={overlayRef}
      aria-hidden
      style={{
        position: "fixed",
        inset: 0,
        display: "grid",
        placeItems: "center",
        background: "var(--color-bg)",
        zIndex: 9999,
        opacity: 1,
        transition: `opacity ${FADE_OUT_MS}ms ease-out`,
      }}
    >
      <div
        className="flex flex-col items-center"
        style={{ animation: "fadeInUp 0.5s ease-out both" }}
      >
        <ArbitraWordmark size="xl" />
        <span
          aria-hidden
          className="mt-5 h-px"
          style={{ width: 64, background: "var(--color-accent)" }}
        />
        <p
          className="mt-5 font-crimson text-[15px] italic"
          style={{ color: "var(--color-ink-faint)" }}
        >
          {BRAND_TAGLINE_TR}
        </p>
      </div>
    </div>
  );
}
