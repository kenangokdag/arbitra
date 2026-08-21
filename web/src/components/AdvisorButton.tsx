"use client";

// F8 AdvisorButton — "Danışmana Sor" shared component (DM-LLM-8)
// mode + pageState prop ile her sayfaya copy-paste enjekte edilir.
// 15 sayfa mount F9-S2 sprint'e ertelendi.

import { useOpenChatbox } from "@/stores/ui";

interface AdvisorButtonProps {
  mode: string;
  pageState?: Record<string, unknown>;
  label?: string;
}

export function AdvisorButton({ mode, pageState, label = "Danışmana Sor" }: AdvisorButtonProps) {
  const openChatbox = useOpenChatbox();

  return (
    <button
      type="button"
      onClick={() => openChatbox({ kind: "advisor", mode, pageState })}
      className="rounded-md border border-stone-300 bg-white px-3 py-1.5 text-sm font-medium text-stone-700 hover:bg-stone-50"
    >
      {label}
    </button>
  );
}
