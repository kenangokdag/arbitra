"use client";

import { FileText } from "lucide-react";

const BAND_STRIPE = [
  "stripe-ok",
  "stripe-info",
  "stripe-accent",
  "stripe-warn",
  "stripe-ok",
  "stripe-info",
] as const;

const STATIC_FALLBACK_STRIPE = [
  "stripe-ok",
  "stripe-info",
  "stripe-accent",
] as const;

export function SearchPending({
  label = "Sizin için akademik makaleler aranıyor",
}: {
  label?: string;
}) {
  return (
    <div
      role="status"
      aria-live="polite"
      aria-label={label}
      className="relative flex h-[280px] w-full items-center justify-center overflow-hidden"
    >
      {/* prefers-reduced-motion fallback — 3 statik skeleton kart */}
      <div
        className="hidden w-full max-w-md flex-col gap-3 motion-reduce:flex"
        data-testid="searchpending-static"
      >
        {STATIC_FALLBACK_STRIPE.map((stripe, i) => (
          <div
            key={i}
            className={`flex h-20 items-center gap-3 rounded-[14px] border border-rule border-l-[3px] ${stripe} bg-bg-card px-4 shadow-sm`}
          >
            <FileText className="h-5 w-5 text-ink-faint" aria-hidden />
            <div className="flex flex-1 flex-col gap-2">
              <div className="h-2 w-3/4 animate-pulse rounded-sm bg-bg-hover" />
              <div className="h-2 w-1/2 animate-pulse rounded-sm bg-bg-hover" />
            </div>
          </div>
        ))}
      </div>

      {/* 3D rotating carousel (motion-safe) */}
      <div
        className="relative motion-reduce:hidden"
        style={{ width: 140, height: 200, perspective: "1000px" }}
        data-testid="searchpending-carousel"
      >
        <div
          className="absolute inset-0"
          style={{
            transformStyle: "preserve-3d",
            transform: "rotateX(-15deg)",
          }}
        >
          <div
            className="anim-searchpending absolute inset-0"
            style={{ transformStyle: "preserve-3d" }}
          >
            {BAND_STRIPE.map((stripe, i) => (
              <article
                key={i}
                className={`absolute inset-0 flex flex-col gap-2 rounded-[14px] border border-rule border-l-[3px] ${stripe} bg-bg-card p-3 shadow-md`}
                style={{
                  transform: `rotateY(${(360 / 6) * i}deg) translateZ(140px)`,
                  backfaceVisibility: "hidden",
                  WebkitBackfaceVisibility: "hidden",
                }}
                aria-hidden
              >
                <FileText className="h-5 w-5 text-ink-faint" aria-hidden />
                <div className="h-2 w-3/4 rounded-sm bg-bg-hover" />
                <div className="h-2 w-1/2 rounded-sm bg-bg-hover" />
                {/* PMID 12-segment stripe brand seal paralel — 6 segment placeholder */}
                <div className="mt-auto flex gap-1">
                  {[0, 1, 2, 3, 4, 5].map((j) => (
                    <span
                      key={j}
                      className="h-1 flex-1 rounded-sm bg-bg-soft"
                    />
                  ))}
                </div>
              </article>
            ))}
          </div>
        </div>
      </div>

      {/* Akademik dergi imza — Lora italic alt başlık */}
      <p className="serif absolute bottom-4 text-[13px] italic tracking-[-0.005em] text-ink-mute">
        {label}…
      </p>
    </div>
  );
}
