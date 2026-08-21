import Link from "next/link";

function EmptyShelfIllustration() {
  return (
    <svg
      width="80"
      height="60"
      viewBox="0 0 80 60"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      style={{ color: "var(--color-ink-faint)" }}
    >
      <line x1="6" y1="14" x2="74" y2="14" />
      <line x1="6" y1="34" x2="74" y2="34" />
      <line x1="6" y1="54" x2="74" y2="54" />
      <rect x="10" y="4" width="6" height="10" />
      <rect x="18" y="6" width="5" height="8" />
      <rect x="25" y="3" width="7" height="11" />
      <rect x="50" y="24" width="6" height="10" />
      <rect x="58" y="26" width="5" height="8" />
      <line
        x1="40"
        y1="48"
        x2="55"
        y2="42"
        stroke="var(--color-accent)"
        strokeWidth="1.8"
      />
      <circle cx="55" cy="42" r="1.5" fill="var(--color-accent)" />
    </svg>
  );
}

export default function NotFound() {
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
            <EmptyShelfIllustration />
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
          404
        </span>
        <h1
          className="font-display mb-2 text-[22px] font-semibold italic leading-snug"
          style={{ color: "var(--color-ink)" }}
        >
          Bu sayfa bulunamadi. Belki yanlis raf?
        </h1>
        <p
          className="mb-6 text-[13.5px] leading-relaxed"
          style={{ color: "var(--color-ink-mute)" }}
        >
          Aradigin sayfa mevcut degil ya da tasinmis olabilir.
        </p>

        <div className="flex flex-wrap items-center justify-center gap-2">
          <Link
            href="/"
            className="font-display inline-flex h-10 items-center rounded-[8px] px-4 text-[14px] font-semibold italic transition-colors"
            style={{
              background: "#E8A157",
              color: "var(--color-ink)",
              border: "1px solid #E8A157",
              boxShadow: "0 1px 3px rgba(232,161,87,0.25)",
            }}
          >
            ← Ana sayfaya don
          </Link>
          <Link
            href="/chat"
            className="inline-flex h-10 items-center rounded-[8px] px-4 text-[14px] font-medium transition-colors"
            style={{
              background: "transparent",
              border: "1px solid var(--color-rule)",
              color: "var(--color-ink-mute)",
            }}
          >
            Danismana sor
          </Link>
        </div>
      </div>
    </div>
  );
}
