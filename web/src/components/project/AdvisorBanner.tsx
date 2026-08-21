"use client";

import type { CSSProperties } from "react";

export type AdvisorZone =
  | "discovery"
  | "curation"
  | "gapatlas"
  | "authoring"
  | "defense";

const DEFAULT_MESSAGE: Record<AdvisorZone, string> = {
  discovery: "Tanisalim once — birkac sorum var. 90 saniye yeter.",
  curation: "Simdi okuma sirasi: konuna gore makale hazirladim.",
  gapatlas: "Literaturun bosluk haritasi: 504K hucre. Beraber inceleyelim.",
  authoring: "Yazim turunu secelim once: tez, makale, bildiri.",
  defense: "Provayi planlayalim: tez savunmasi mi, yeterlilik mi?",
};

const ZONE_STRIPE: Record<AdvisorZone, string> = {
  discovery: "#E8A157",
  curation: "#E8A157",
  authoring: "#E8A157",
  gapatlas: "#0E4F4A",
  defense: "#C9A961",
};

function PenIcon({ size = 16 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M14 2L7 13l4 4 11-7-8-8z" />
      <path d="M7 13l-4 8 8-4" />
      <line x1={11} y1={17} x2={7} y2={13} />
    </svg>
  );
}

function ChatBubbleIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}

export function AdvisorBanner({
  zone,
  message,
  onChatOpen,
  compact = false,
}: {
  zone?: AdvisorZone;
  message?: string;
  onChatOpen?: () => void;
  compact?: boolean;
}) {
  const stripe = zone ? ZONE_STRIPE[zone] : "var(--color-ink)";
  const text = message ?? (zone ? DEFAULT_MESSAGE[zone] : undefined);
  const padY = compact ? "9px" : "13px";
  const padX = compact ? "14px" : "16px";
  const iconBox = compact ? 26 : 32;
  const iconRadius = compact ? 6 : 8;

  const wrapperStyle: CSSProperties = {
    borderLeft: `3px solid ${stripe}`,
    border: "1px solid var(--color-rule-soft)",
    borderLeftWidth: 3,
    borderLeftColor: stripe,
    background: "var(--color-bg-card)",
    borderRadius: 8,
    padding: `${padY} ${padX}`,
    boxShadow: "0 1px 3px rgba(15,23,42,0.06)",
    animation: "fadeInUp 200ms ease-out",
  };

  return (
    <div className="mb-4 flex items-center gap-3" style={wrapperStyle}>
      <div
        className="flex flex-shrink-0 items-center justify-center"
        style={{
          width: iconBox,
          height: iconBox,
          borderRadius: iconRadius,
          background: "var(--color-bg-soft)",
          border: "1px solid var(--color-rule)",
          color: "var(--color-ink-mute)",
        }}
      >
        <PenIcon size={compact ? 14 : 16} />
      </div>

      <div className="min-w-0 flex-1">
        <div
          className="font-mono uppercase"
          style={{
            fontSize: 9.5,
            letterSpacing: "0.08em",
            color: "var(--color-ink-faint)",
            lineHeight: 1.4,
          }}
        >
          Danisman
        </div>
        <p
          className="font-display italic"
          style={{
            fontSize: compact ? 13.5 : 14.5,
            color: "var(--color-ink)",
            lineHeight: 1.45,
            margin: 0,
          }}
        >
          {text}
        </p>
      </div>

      {onChatOpen && (
        <button
          type="button"
          onClick={onChatOpen}
          className="flex flex-shrink-0 items-center justify-center text-white transition-transform duration-150 hover:scale-[1.05]"
          style={{
            width: compact ? 26 : 32,
            height: compact ? 26 : 32,
            borderRadius: compact ? 6 : 8,
            background: "var(--color-ink)",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = "#1e293b";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "var(--color-ink)";
          }}
          aria-label="Danisman ile sohbet"
        >
          <ChatBubbleIcon />
        </button>
      )}
    </div>
  );
}
