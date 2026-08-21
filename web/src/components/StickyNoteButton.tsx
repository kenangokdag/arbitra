"use client";

import { useState } from "react";
import { Check, PenLine, X } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api";
import { useNavigation } from "@/lib/navigation-context";
import { getPageTitle } from "@/lib/nav-config";
import type { NoteItem } from "@/lib/types";

export function StickyNoteButton() {
  const [open, setOpen] = useState(false);
  const [content, setContent] = useState("");
  const [saved, setSaved] = useState(false);
  const { currentPageId } = useNavigation();
  const queryClient = useQueryClient();

  const pageTitle = currentPageId ? getPageTitle(currentPageId) : "Genel";

  const save = useMutation({
    mutationFn: () =>
      apiFetch<NoteItem>("/api/notes", {
        method: "POST",
        body: {
          paper_id: null,
          content: `[${pageTitle}] ${content.trim()}`,
          tags: [pageTitle],
        },
      }),
    onSuccess: () => {
      setSaved(true);
      queryClient.invalidateQueries({ queryKey: ["notes"] });
      setTimeout(() => {
        setOpen(false);
        setContent("");
        setSaved(false);
      }, 1500);
    },
  });

  return (
    <>
      <style>{`
        @keyframes pmPopIn {
          from { opacity: 0; transform: translateY(8px) scale(0.97); }
          to   { opacity: 1; transform: translateY(0) scale(1); }
        }
      `}</style>

      {/* Floating button */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        title="Nota ekle"
        aria-label="Nota ekle"
        className="fixed bottom-5 right-5 z-40 flex h-[46px] w-[46px] items-center justify-center text-white transition-transform duration-150 hover:scale-[1.06]"
        style={{
          background: "var(--color-ink)",
          borderRadius: 12,
          boxShadow: "0 2px 8px rgba(15,23,42,0.2)",
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = "var(--color-ink-soft)";
          e.currentTarget.style.boxShadow = "0 4px 16px rgba(15,23,42,0.28)";
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = "var(--color-ink)";
          e.currentTarget.style.boxShadow = "0 2px 8px rgba(15,23,42,0.2)";
        }}
      >
        <PenLine className="h-[18px] w-[18px]" strokeWidth={2} />
      </button>

      {open && (
        <div
          className="fixed bottom-[72px] right-5 z-50 w-[280px] overflow-hidden bg-white"
          style={{
            border: "1px solid var(--color-rule-soft)",
            borderRadius: 12,
            boxShadow: "0 4px 24px rgba(15,23,42,0.12)",
            animation: "pmPopIn 180ms ease-out",
          }}
        >
          <div
            className="flex items-center justify-between px-3 py-2"
            style={{ borderBottom: "1px solid var(--color-rule-soft)" }}
          >
            <span
              className="text-[13px] font-semibold"
              style={{ color: "var(--color-ink)" }}
            >
              Nota ekle
            </span>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="flex h-[22px] w-[22px] items-center justify-center rounded-md transition-colors hover:bg-stone-100"
              style={{ color: "var(--color-ink-mute)" }}
              aria-label="Kapat"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>

          {saved ? (
            <div
              className="font-display flex items-center justify-center gap-2 px-5 py-5 text-[14px] italic"
              style={{ color: "var(--color-ink-soft)" }}
            >
              <Check
                className="h-[18px] w-[18px]"
                strokeWidth={2.5}
                style={{ color: "var(--color-accent)" }}
              />
              Not kaydedildi
            </div>
          ) : (
            <>
              <div
                className="px-3 py-1.5 font-mono text-[10px]"
                style={{
                  background: "var(--color-bg-soft)",
                  borderBottom: "1px solid var(--color-rule-soft)",
                  color: "var(--color-ink-faint)",
                }}
              >
                Kaynak: {pageTitle}
              </div>

              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="Notunu yaz…"
                className="font-display block min-h-[80px] w-full resize-none px-3 py-3 text-[13.5px] italic outline-none"
                style={{
                  border: "none",
                  color: "var(--color-ink)",
                  background: "white",
                }}
              />

              <div
                className="flex items-center justify-end gap-2 px-3 py-2"
                style={{ borderTop: "1px solid var(--color-rule-soft)" }}
              >
                <button
                  type="button"
                  onClick={() => save.mutate()}
                  disabled={!content.trim() || save.isPending}
                  className="inline-flex h-[30px] items-center gap-1.5 rounded-md px-3 text-xs font-semibold text-white transition-colors disabled:cursor-not-allowed disabled:opacity-60"
                  style={{ background: "var(--color-ink)" }}
                  onMouseEnter={(e) => {
                    if (!save.isPending && content.trim()) {
                      e.currentTarget.style.background =
                        "var(--color-ink-soft)";
                    }
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = "var(--color-ink)";
                  }}
                >
                  <Check className="h-3 w-3" strokeWidth={3} />
                  {save.isPending ? "Kaydediliyor…" : "Kaydet"}
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </>
  );
}
