"use client";

import { useEffect } from "react";
import Link from "next/link";

function LampIllustration() {
  return (
    <svg
      width="80"
      height="80"
      viewBox="0 0 80 80"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      style={{ color: "var(--color-ink-faint)" }}
    >
      <line x1="20" y1="68" x2="42" y2="68" />
      <rect x="22" y="60" width="18" height="8" rx="1.5" />
      <line x1="31" y1="60" x2="31" y2="40" />
      <path d="M22 22 L40 22 L36 40 L26 40 Z" />
      <line x1="48" y1="14" x2="55" y2="10" stroke="var(--color-accent)" strokeWidth="1.8" />
      <line x1="50" y1="22" x2="58" y2="22" stroke="var(--color-accent)" strokeWidth="1.8" />
      <line x1="48" y1="30" x2="55" y2="34" stroke="var(--color-accent)" strokeWidth="1.8" />
      <circle cx="60" cy="58" r="1.5" fill="var(--color-ink)" opacity="0.6" />
      <circle cx="65" cy="62" r="1" fill="var(--color-ink)" opacity="0.4" />
      <circle cx="62" cy="66" r="0.8" fill="var(--color-ink)" opacity="0.3" />
    </svg>
  );
}

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[Arbitra] route error:", error);
  }, [error]);

  return (
    <div className="mx-auto flex max-w-[480px] flex-col items-center gap-4 px-6 py-24 text-center">
      <div
        className="rounded-2xl bg-white p-8"
        style={{
          border: "1px solid var(--color-rule-soft)",
          boxShadow: "0 8px 24px rgba(15,23,42,0.08)",
        }}
      >
        <div
          className="mx-auto mb-5 flex h-[120px] w-[160px] items-center justify-center rounded-[10px]"
          style={{
            background: "var(--color-bg-soft)",
            border: "1px dashed var(--color-rule)",
          }}
        >
          <div className="flex flex-col items-center gap-1.5">
            <LampIllustration />
            <span
              className="font-mono text-[9px] uppercase tracking-wider"
              style={{ color: "var(--color-ink-faint)" }}
            >
              illustrasyon
            </span>
          </div>
        </div>

        <span
          className="mb-2 inline-block font-mono text-[11px] font-semibold uppercase tracking-widest"
          style={{ color: "var(--color-ink-faint)" }}
        >
          500
        </span>
        <h1
          className="font-display mb-2 text-[22px] font-semibold italic leading-snug"
          style={{ color: "var(--color-ink)" }}
        >
          Teknik bir sorun yasiyoruz. Birazdan tekrar dene.
        </h1>
        <p
          className="mb-3 text-[13.5px] leading-relaxed"
          style={{ color: "var(--color-ink-mute)" }}
        >
          Sunucuda beklenmedik bir hata olustu. Ekibimiz haberdar edildi.
        </p>

        {error.message && (
          <p
            className="mb-6 break-all rounded-md p-2 font-mono text-[11px]"
            style={{
              background: "var(--color-bg-soft)",
              color: "var(--color-ink-faint)",
              border: "1px solid var(--color-rule-soft)",
            }}
          >
            <code>{error.message}</code>
          </p>
        )}

        <div className="flex flex-wrap items-center justify-center gap-2">
          <button
            type="button"
            onClick={reset}
            className="font-display inline-flex h-10 items-center rounded-[8px] px-4 text-[14px] font-semibold italic transition-colors"
            style={{
              background: "#E8A157",
              color: "var(--color-ink)",
              border: "1px solid #E8A157",
              boxShadow: "0 1px 3px rgba(232,161,87,0.25)",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = "#D4923E";
              e.currentTarget.style.borderColor = "#D4923E";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "#E8A157";
              e.currentTarget.style.borderColor = "#E8A157";
            }}
          >
            ↺ Tekrar dene
          </button>
          <Link
            href="/"
            className="inline-flex h-10 items-center rounded-[8px] px-4 text-[14px] font-medium transition-colors"
            style={{
              background: "var(--color-bg-card)",
              border: "1px solid var(--color-rule)",
              color: "var(--color-ink-soft)",
              boxShadow: "0 1px 2px rgba(15,23,42,0.04)",
            }}
          >
            Ana sayfaya don
          </Link>
        </div>
      </div>
    </div>
  );
}
