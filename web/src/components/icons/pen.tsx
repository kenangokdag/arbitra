import type { SVGProps } from "react";

// PenIcon — D16-Chatbox.html L423-430 inline <symbol id="pen"> birebir geometri.
// Lucide PenLine yerine mockup canon path'leri (HK-2 D16 referansı).
// Danışman avatar + Topbar trigger + chat empty-state ring içinde kullanılır.
export function PenIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      <path d="M14 2L7 13l4 4 11-7-8-8z" />
      <path d="M7 13l-4 8 8-4" />
      <line x1="11" y1="17" x2="7" y2="13" />
    </svg>
  );
}
