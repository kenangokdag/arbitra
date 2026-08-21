"use client";

/**
 * F13-S1-P005 — Araştırma Defteri sidebar tab.
 * kaynak: docs/plans/F13_sayfa_plani_v2_implementation.md §3 (F13-S1-P005)
 * sayfa: Page_Design/Sayfa_Plani_v2/S1_arastirma_defteri.rtf §(3) FRONTEND
 *
 * Proje-bazlı zaman çizgisi: GET /api/diary/timeline + günlük grup.
 * Üst aksiyon: "Bu projede son 30 günü özetle" → pre-advisor-summary mutation.
 * 3 satır aksiyonu (Düzenle / Resolve / Geri Dön) P006'da bağlanır — şimdilik stub.
 */

import { useMemo, useState } from "react";
import {
  BookmarkPlus,
  BookOpen,
  MessageCircle,
  Sparkles,
  StickyNote,
} from "lucide-react";

import {
  useDiaryTimeline,
  usePatchDiaryEvent,
  usePreAdvisorSummary,
} from "@/hooks/useDiary";
import type {
  DiaryEventApi,
  DiaryEventType,
} from "@/lib/diary-api";

const EVENT_LABEL: Record<DiaryEventType, string> = {
  kayit: "Ajandaya kayıt",
  danismana_sor: "Danışmana sor",
  kutuphane_ekle: "Kütüphaneye ekle",
  not: "Serbest not",
};

const EVENT_ICON: Record<DiaryEventType, React.ComponentType<{ className?: string }>> = {
  kayit: BookOpen,
  danismana_sor: MessageCircle,
  kutuphane_ekle: BookmarkPlus,
  not: StickyNote,
};

function dayKey(iso: string): string {
  return iso.slice(0, 10);
}

function formatDayHeading(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("tr-TR", {
    day: "numeric",
    month: "long",
    year: "numeric",
    weekday: "long",
  });
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" });
}

function groupByDay(events: DiaryEventApi[]): { day: string; rows: DiaryEventApi[] }[] {
  const map = new Map<string, DiaryEventApi[]>();
  for (const ev of events) {
    const key = dayKey(ev.createdAt);
    const list = map.get(key) ?? [];
    list.push(ev);
    map.set(key, list);
  }
  return Array.from(map.entries())
    .sort((a, b) => (a[0] < b[0] ? 1 : -1))
    .map(([day, rows]) => ({ day, rows }));
}

interface DiarySidebarProps {
  projectId: string;
}

export function DiarySidebar({ projectId }: DiarySidebarProps) {
  const [pageSlug, setPageSlug] = useState("");
  const [paperId, setPaperId] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingNote, setEditingNote] = useState("");

  const filters = useMemo(
    () => ({
      projectId,
      pageSlug: pageSlug || undefined,
      paperId: paperId || undefined,
    }),
    [projectId, pageSlug, paperId],
  );

  const timeline = useDiaryTimeline(filters);
  const summary = usePreAdvisorSummary();
  const patch = usePatchDiaryEvent();

  function startEdit(ev: DiaryEventApi) {
    setEditingId(ev.id);
    setEditingNote(typeof ev.payload?.note === "string" ? ev.payload.note : "");
  }

  function cancelEdit() {
    setEditingId(null);
    setEditingNote("");
  }

  function saveEdit(ev: DiaryEventApi) {
    const nextPayload = { ...ev.payload, note: editingNote };
    patch.mutate(
      { eventId: ev.id, patch: { payload: nextPayload } },
      { onSuccess: () => cancelEdit() },
    );
  }

  function toggleResolved(ev: DiaryEventApi) {
    const resolvedAt = ev.resolvedAt ? null : new Date().toISOString();
    patch.mutate({ eventId: ev.id, patch: { resolvedAt } });
  }

  const grouped = useMemo(
    () => (timeline.data ? groupByDay(timeline.data.items) : []),
    [timeline.data],
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="font-display text-xl font-semibold text-stone-800">
          Araştırma Defteri
        </h2>
        <button
          type="button"
          onClick={() => summary.mutate(projectId)}
          disabled={summary.isPending}
          className="inline-flex items-center gap-1.5 rounded-lg bg-amber-50 px-3 py-1.5 text-sm font-medium text-amber-800 transition-colors hover:bg-amber-100 disabled:opacity-50"
        >
          <Sparkles className="h-3.5 w-3.5" />
          {summary.isPending ? "Özetleniyor…" : "Bu projede son 30 günü özetle"}
        </button>
      </div>

      {summary.data && (
        <div className="rounded-xl border border-amber-200 bg-amber-50/50 p-4">
          <p className="text-sm leading-relaxed text-stone-700">
            {summary.data.summary}
          </p>
          <p className="mt-2 text-xs text-stone-500">
            {summary.data.eventCount} olay · son 30 gün
          </p>
        </div>
      )}
      {summary.isError && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          Özet alınamadı. Sonra tekrar deneyin.
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        <input
          type="text"
          value={pageSlug}
          onChange={(e) => setPageSlug(e.target.value)}
          placeholder="Sayfa filtresi (örn: 4.2_bosluk_profili)"
          aria-label="Sayfa filtresi"
          className="flex-1 rounded-lg border border-stone-200 bg-white px-3 py-1.5 text-sm placeholder:text-stone-400"
        />
        <input
          type="text"
          value={paperId}
          onChange={(e) => setPaperId(e.target.value)}
          placeholder="Paper ID"
          aria-label="Paper ID filtresi"
          className="w-40 rounded-lg border border-stone-200 bg-white px-3 py-1.5 text-sm placeholder:text-stone-400"
        />
      </div>

      {timeline.isPending && (
        <p className="text-sm text-stone-400">Zaman çizgisi yükleniyor…</p>
      )}
      {timeline.isError && (
        <p className="text-sm text-red-600">Zaman çizgisi alınamadı.</p>
      )}

      {timeline.isSuccess && grouped.length === 0 && (
        <div className="rounded-xl border border-dashed border-stone-300 bg-stone-50 p-6 text-center">
          <p className="text-sm text-stone-500">
            Henüz kayıt yok. Sayfa altında &quot;Ajandama Kaydet&quot; ile başla.
          </p>
        </div>
      )}

      {grouped.map(({ day, rows }) => (
        <section key={day} className="space-y-2">
          <h3 className="font-display text-xs font-semibold uppercase tracking-wide text-stone-400">
            {formatDayHeading(day)}
          </h3>
          <ul className="space-y-2">
            {rows.map((ev) => {
              const Icon = EVENT_ICON[ev.eventType];
              const note =
                typeof ev.payload?.note === "string" ? ev.payload.note : "";
              const isEditing = editingId === ev.id;
              return (
                <li
                  key={ev.id}
                  className="rounded-xl border border-stone-200 bg-white p-3 shadow-sm"
                  data-testid="diary-event-row"
                >
                  <div className="flex items-start gap-3">
                    <Icon className="mt-0.5 h-4 w-4 flex-shrink-0 text-stone-500" />
                    <div className="min-w-0 flex-1 space-y-1">
                      <div className="flex flex-wrap items-center gap-2 text-xs">
                        <span className="font-medium text-stone-700">
                          {EVENT_LABEL[ev.eventType]}
                        </span>
                        <span className="rounded-full bg-stone-100 px-2 py-0.5 text-stone-600">
                          {ev.pageSlug}
                        </span>
                        {ev.paperId && (
                          <span className="rounded-full bg-amber-50 px-2 py-0.5 text-amber-700">
                            {ev.paperId}
                          </span>
                        )}
                        <span className="text-stone-400">
                          {formatTime(ev.createdAt)}
                        </span>
                        {ev.resolvedAt === null && (
                          <span className="rounded-full bg-blue-50 px-2 py-0.5 text-blue-700">
                            açık
                          </span>
                        )}
                      </div>
                      {isEditing ? (
                        <textarea
                          value={editingNote}
                          onChange={(e) => setEditingNote(e.target.value)}
                          aria-label="not düzenle"
                          rows={2}
                          className="w-full rounded-lg border border-stone-200 px-2 py-1 text-sm focus:border-stone-400 focus:outline-none"
                        />
                      ) : (
                        note && <p className="text-sm text-stone-600">{note}</p>
                      )}
                      <div className="flex gap-3 text-xs text-stone-400">
                        {isEditing ? (
                          <>
                            <button
                              type="button"
                              onClick={() => saveEdit(ev)}
                              disabled={patch.isPending}
                              className="hover:text-stone-600 disabled:opacity-40"
                            >
                              Kaydet
                            </button>
                            <button
                              type="button"
                              onClick={cancelEdit}
                              className="hover:text-stone-600"
                            >
                              Vazgeç
                            </button>
                          </>
                        ) : (
                          <>
                            <button
                              type="button"
                              onClick={() => startEdit(ev)}
                              className="hover:text-stone-600"
                            >
                              Düzenle
                            </button>
                            <button
                              type="button"
                              onClick={() => toggleResolved(ev)}
                              disabled={patch.isPending}
                              className="hover:text-stone-600 disabled:opacity-40"
                            >
                              {ev.resolvedAt ? "Geri aç" : "Çözüldü"}
                            </button>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </div>
  );
}
