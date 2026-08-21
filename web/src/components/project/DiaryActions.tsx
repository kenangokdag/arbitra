"use client";

/**
 * F13-S1-P006 — sayfa-içi 3-buton (shared) komponenti.
 * kaynak: docs/plans/F13_sayfa_plani_v2_implementation.md §3 (F13-S1-P006)
 * sayfa: Page_Design/Sayfa_Plani_v2/S1_arastirma_defteri.rtf §(2) BACKEND
 *
 * Her sayfada (27 sayfa) "Ajandama Kaydet / Danışmana Sor / Kütüphaneme Ekle"
 * butonları. Hepsi POST /api/diary/event'e gider, event_type ile ayrışır.
 * Yan etkiler (advisor flow tetikleme, library upsert) F13-S2+ kapsamında —
 * P006 yalnız event log yazar.
 */

import { useState } from "react";
import {
  BookmarkPlus,
  BookOpen,
  Check,
  MessageCircle,
} from "lucide-react";

import { useCreateDiaryEvent } from "@/hooks/useDiary";
import type { DiaryEventType } from "@/lib/diary-api";

interface DiaryActionsProps {
  projectId: string;
  pageSlug: string;
  paperId?: string;
}

const ACTIONS: { type: DiaryEventType; label: string; Icon: React.ComponentType<{ className?: string }> }[] = [
  { type: "kayit", label: "Ajandama Kaydet", Icon: BookOpen },
  { type: "danismana_sor", label: "Danışmana Sor", Icon: MessageCircle },
  { type: "kutuphane_ekle", label: "Kütüphaneme Ekle", Icon: BookmarkPlus },
];

export function DiaryActions({ projectId, pageSlug, paperId }: DiaryActionsProps) {
  const [note, setNote] = useState("");
  const [savedType, setSavedType] = useState<DiaryEventType | null>(null);
  const create = useCreateDiaryEvent();

  function handle(eventType: DiaryEventType) {
    create.mutate(
      {
        projectId,
        pageSlug,
        eventType,
        paperId: paperId ?? null,
        payload: note ? { note } : {},
      },
      {
        onSuccess: () => {
          setSavedType(eventType);
          setNote("");
          window.setTimeout(() => setSavedType(null), 2000);
        },
      },
    );
  }

  return (
    <div
      className="space-y-2 rounded-xl border border-stone-200 bg-white p-3"
      data-testid="diary-actions"
    >
      <textarea
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="Bu sayfayla ilgili kısa not (opsiyonel)…"
        aria-label="Defter notu"
        rows={2}
        className="w-full resize-none rounded-lg border border-stone-200 bg-stone-50 px-3 py-2 text-sm placeholder:text-stone-400 focus:bg-white focus:outline-none"
      />
      <div className="flex flex-wrap gap-2">
        {ACTIONS.map(({ type, label, Icon }) => (
          <button
            key={type}
            type="button"
            onClick={() => handle(type)}
            disabled={create.isPending}
            aria-label={label}
            className="inline-flex items-center gap-1.5 rounded-lg border border-stone-200 bg-white px-3 py-1.5 text-sm text-stone-700 transition-colors hover:bg-amber-50 hover:text-amber-800 disabled:opacity-50"
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
            {savedType === type && (
              <Check className="h-3.5 w-3.5 text-emerald-600" />
            )}
          </button>
        ))}
      </div>
      {create.isError && (
        <p className="text-xs text-red-600">Kayıt başarısız. Sonra tekrar deneyin.</p>
      )}
    </div>
  );
}
