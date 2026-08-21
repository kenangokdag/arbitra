"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { Hint } from "@/components/Hint";
import { Button } from "@/components/ui/button";
import { apiFetch, ApiError } from "@/lib/api";
import type {
  ReadingListResponse,
  ReadingListItem,
  ReadingStatus,
} from "@/lib/types";

const TABS: { key: ReadingStatus | "all"; label: string }[] = [
  { key: "all", label: "Tümü" },
  { key: "want_to_read", label: "Okumak istiyorum" },
  { key: "reading", label: "Okuyorum" },
  { key: "finished", label: "Bitirdim" },
  { key: "skipped", label: "Atladım" },
];

const STATUS_CHIP: Record<ReadingStatus, string> = {
  want_to_read: "border-amber-200 bg-amber-50 text-amber-700",
  reading: "border-blue-200 bg-blue-50 text-blue-700",
  finished: "border-emerald-200 bg-emerald-50 text-emerald-700",
  skipped: "border-stone-200 bg-stone-50 text-stone-500",
};

const STATUS_LABEL: Record<ReadingStatus, string> = {
  want_to_read: "Okumak istiyorum",
  reading: "Okuyorum",
  finished: "Bitirdim",
  skipped: "Atladım",
};

export default function ReadingListPage() {
  const [activeTab, setActiveTab] = useState<ReadingStatus | "all">("all");
  const queryClient = useQueryClient();

  const { data, isLoading, isError, error } = useQuery<ReadingListResponse>({
    queryKey: ["reading-list"],
    queryFn: () => apiFetch<ReadingListResponse>("/api/reading-list"),
  });

  const deleteMutation = useMutation({
    mutationFn: (itemId: string) =>
      apiFetch(`/api/reading-list/${itemId}`, { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["reading-list"] }),
  });

  const updateMutation = useMutation({
    mutationFn: ({ itemId, status }: { itemId: string; status: ReadingStatus }) =>
      apiFetch<ReadingListItem>(`/api/reading-list/${itemId}`, {
        method: "PATCH",
        body: { status },
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["reading-list"] }),
  });

  const items = data?.items ?? [];
  const filtered =
    activeTab === "all" ? items : items.filter((i) => i.status === activeTab);

  return (
    <>
      <PageHeader
        title="Okuma Listem"
        lede="Kaydettiğiniz makaleler. Durumlarını güncelleyebilir, notlarınızı düzenleyebilirsiniz."
      />

      {isError && (
        <Hint>
          Liste yüklenemedi:{" "}
          {error instanceof ApiError ? error.message : "Bağlantı hatası"}
        </Hint>
      )}

      <div className="mb-5 flex gap-1.5">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setActiveTab(tab.key)}
            className={`rounded-full border px-3 py-1 text-[12.5px] font-medium transition-colors duration-150 ${
              activeTab === tab.key
                ? "border-accent bg-accent/10 text-accent"
                : "border-rule bg-bg-card text-ink-mute hover:bg-bg-hover"
            }`}
          >
            {tab.label}
            {tab.key === "all" ? ` (${items.length})` : ` (${items.filter((i) => i.status === tab.key).length})`}
          </button>
        ))}
      </div>

      {isLoading && (
        <div className="flex flex-col gap-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 animate-pulse rounded-lg border border-rule bg-bg-soft" />
          ))}
        </div>
      )}

      {!isLoading && filtered.length === 0 && (
        <p className="py-8 text-center text-[14px] text-ink-mute">
          {items.length === 0
            ? "Listeniz boş — arama sonuçlarından makale ekleyin."
            : "Bu filtrede makale yok."}
        </p>
      )}

      <div className="flex flex-col gap-3">
        {filtered.map((item) => (
          <article
            key={item.id}
            className="flex items-center gap-4 rounded-lg border border-rule bg-bg-card p-4 transition-shadow duration-200 hover:shadow-sm"
          >
            <div className="flex-1">
              <p className="text-[14px] font-medium text-ink">
                {item.paper_id}
              </p>
              {item.notes && (
                <p className="mt-1 text-[12.5px] text-ink-mute">{item.notes}</p>
              )}
              <div className="mt-2 flex items-center gap-2">
                <span
                  className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${STATUS_CHIP[item.status]}`}
                >
                  {STATUS_LABEL[item.status]}
                </span>
                <span className="text-[11px] text-ink-faint">
                  {new Date(item.added_at).toLocaleDateString("tr-TR")}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-1.5">
              <select
                value={item.status}
                onChange={(e) =>
                  updateMutation.mutate({
                    itemId: item.id,
                    status: e.target.value as ReadingStatus,
                  })
                }
                className="rounded-sm border border-rule bg-bg-card px-2 py-1 text-[12px] text-ink-soft"
              >
                {Object.entries(STATUS_LABEL).map(([val, label]) => (
                  <option key={val} value={val}>
                    {label}
                  </option>
                ))}
              </select>
              <Button
                size="sm"
                variant="ghost"
                type="button"
                onClick={() => deleteMutation.mutate(item.id)}
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </div>
          </article>
        ))}
      </div>
    </>
  );
}
