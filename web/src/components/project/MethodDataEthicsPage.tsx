"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ExternalLink,
  Search,
  Check,
  Download,
  FileText,
  Loader2,
} from "lucide-react";
import { AdvisorBanner } from "@/components/project/AdvisorBanner";
import { DataVizCard } from "@/components/project/DataVizCard";
import { apiFetch } from "@/lib/api";

/* ── API types ── */
interface PaperCard {
  paper_id: string;
  title: string;
  year: number | null;
  abstract_excerpt: string | null;
  journal: string | null;
  n_cited: number;
  decision_band: string;
}
interface SearchResponse { papers: PaperCard[]; }

/* ── Static reference data (Tabs 2–3) ── */
interface DatasetSource { name: string; initial: string; color: string; topic: string; }
const datasets: DatasetSource[] = [
  { name: "Google Dataset Search", initial: "G", color: "#4285F4", topic: "sustainability supply chain" },
  { name: "World Bank Open Data",  initial: "W", color: "#009FDA", topic: "development indicators" },
  { name: "OECD Data",             initial: "O", color: "#003F87", topic: "economic statistics" },
  { name: "IMF Data",              initial: "I", color: "#002244", topic: "financial indicators" },
  { name: "Eurostat",              initial: "E", color: "#003399", topic: "EU economic data" },
  { name: "Kaggle Datasets",       initial: "K", color: "#20BEFF", topic: "machine learning datasets" },
];

const ethicsChecklist = [
  { id: 1, label: "Katilimci onam formu hazirlandi",        doc: "Onam formu sablonu" },
  { id: 2, label: "Kisisel veri isleme protokolu belirlendi", doc: "KVKK uyum belgesi" },
  { id: 3, label: "Arastirma amaci ve kapsami tanimli",      doc: "Arastirma protokolu" },
  { id: 4, label: "Veri saklama ve imha plani mevcut",       doc: "Veri yonetim plani" },
  { id: 5, label: "Zarar-risk degerlendirmesi yapildi",      doc: "Risk analiz formu" },
  { id: 6, label: "Gizlilik ve anonimlik onlemleri tanimli", doc: "Gizlilik protokolu" },
  { id: 7, label: "Cikar catismasi beyani hazirlandi",       doc: "Beyan formu" },
  { id: 8, label: "Etik kurul basvuru dosyasi tamamlandi",   doc: "Basvuru kontrol listesi" },
];

const BAND_COLORS: Record<string, string> = {
  canon:           "bg-emerald-100 text-emerald-700",
  frontier:        "bg-blue-100 text-blue-700",
  strong_evidence: "bg-amber-100 text-amber-700",
  risk:            "bg-red-100 text-red-700",
};

type ActiveTab = "method" | "dataset" | "ethics";

export function MethodDataEthicsPage() {
  const [activeTab, setActiveTab] = useState<ActiveTab>("method");
  const [inputText, setInputText] = useState("MCDM method comparison sustainability");
  const [query, setQuery] = useState("MCDM method comparison sustainability");
  const [checkedItems, setCheckedItems] = useState<Set<number>>(new Set());

  const { data, isLoading, isError } = useQuery({
    queryKey: ["method-papers", query],
    queryFn: () =>
      apiFetch<SearchResponse>("/api/search", {
        method: "POST",
        body: { query, k: 10, include_ghost: false },
      }),
    staleTime: 3600_000,
    enabled: !!query,
  });

  const papers = data?.papers ?? [];

  const toggleCheck = (id: number) => {
    setCheckedItems((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const tabs: { key: ActiveTab; label: string }[] = [
    { key: "method",  label: "Yontem Onerisi" },
    { key: "dataset", label: "Veri Seti Baglantilari" },
    { key: "ethics",  label: "Etik Kurul Rehberi" },
  ];

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <AdvisorBanner message="Yontem fikri, veri seti baglantilari, etik kurul rehberi — ucunu birlikte kuralim." />

      {/* Tabs */}
      <div className="flex gap-2 border-b border-stone-200 pb-px">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            className={`rounded-t-lg px-5 py-2 text-sm font-medium transition-colors ${
              activeTab === t.key ? "border-b-2 text-stone-800" : "text-stone-400 hover:text-stone-600"
            }`}
            style={activeTab === t.key ? { borderBottomColor: "#E8A157" } : undefined}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* TAB 1 — Yöntem Önerisi */}
      {activeTab === "method" && (
        <DataVizCard title="Yapisal Literatur Tablosu" badge="fact_paper_id_card" zoneTint="#E8A157">
          {/* Search */}
          <div className="mb-4 flex items-center gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400" />
              <input
                type="text"
                placeholder="Konu veya yöntem ara..."
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && setQuery(inputText)}
                className="w-full rounded-lg border border-stone-200 bg-stone-50 py-2 pl-9 pr-3 text-xs text-stone-700 outline-none focus:border-amber-300 focus:ring-1 focus:ring-amber-200"
              />
            </div>
            <button
              onClick={() => setQuery(inputText)}
              disabled={isLoading}
              className="flex items-center gap-1.5 rounded-lg bg-amber-500 px-4 py-2 text-xs font-semibold text-white hover:bg-amber-600 disabled:opacity-50"
            >
              {isLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Search className="h-3.5 w-3.5" />}
              Ara
            </button>
          </div>

          {isError && (
            <p className="py-4 text-center text-sm text-red-500">Arama başarısız. Backend bağlantısını kontrol edin.</p>
          )}

          {isLoading && (
            <div className="flex items-center justify-center gap-2 py-8 text-stone-400">
              <Loader2 className="h-5 w-5 animate-spin" />
              <span className="text-sm">Literatur yükleniyor...</span>
            </div>
          )}

          {!isLoading && papers.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-stone-100">
                    <th className="px-3 py-2 font-medium text-stone-500">Makale</th>
                    <th className="px-3 py-2 font-medium text-stone-500">Ozet / Amac</th>
                    <th className="px-3 py-2 font-medium text-stone-500">Dergi</th>
                    <th className="px-3 py-2 font-medium text-stone-500">Atif</th>
                    <th className="px-3 py-2 font-medium text-stone-500">Bant</th>
                  </tr>
                </thead>
                <tbody>
                  {papers.map((p) => (
                    <tr key={p.paper_id} className="border-b border-stone-50 hover:bg-stone-50/60">
                      <td className="max-w-[200px] px-3 py-2.5">
                        <p className="truncate font-medium text-stone-700">{p.title}</p>
                        {p.year && <p className="text-stone-400">({p.year})</p>}
                      </td>
                      <td className="max-w-[240px] px-3 py-2.5 text-stone-500">
                        <p className="line-clamp-2">{p.abstract_excerpt ?? "—"}</p>
                      </td>
                      <td className="max-w-[130px] truncate px-3 py-2.5 text-stone-500">
                        {p.journal ?? "—"}
                      </td>
                      <td className="px-3 py-2.5 text-stone-600">{p.n_cited.toLocaleString()}</td>
                      <td className="px-3 py-2.5">
                        <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${BAND_COLORS[p.decision_band] ?? "bg-stone-100 text-stone-600"}`}>
                          {p.decision_band}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {!isLoading && !isError && papers.length === 0 && (
            <p className="py-8 text-center text-sm text-stone-400">Sonuç bulunamadı.</p>
          )}
        </DataVizCard>
      )}

      {/* TAB 2 — Veri Seti Bağlantıları */}
      {activeTab === "dataset" && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {datasets.map((ds) => (
            <div
              key={ds.name}
              className="flex flex-col items-center rounded-2xl border border-stone-200 bg-white p-6 text-center transition-shadow hover:shadow-md"
              style={{ boxShadow: "0 1px 3px rgba(0,0,0,0.06)" }}
            >
              <div
                className="mb-3 flex h-14 w-14 items-center justify-center rounded-xl text-xl font-bold text-white"
                style={{ background: ds.color }}
              >
                {ds.initial}
              </div>
              <h4 className="font-display text-sm font-semibold text-stone-800">{ds.name}</h4>
              <p className="mt-1 text-[11px] text-stone-400">Veri seti arama platformu</p>
              <button
                className="mt-4 inline-flex items-center gap-1.5 rounded-lg px-4 py-2 text-xs font-medium text-white transition-colors hover:opacity-90"
                style={{ background: "#E8A157" }}
              >
                Ara: {ds.topic}
                <ExternalLink className="h-3 w-3" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* TAB 3 — Etik Kurul Rehberi */}
      {activeTab === "ethics" && (
        <div className="rounded-2xl border border-stone-200 bg-white p-6" style={{ boxShadow: "0 1px 3px rgba(0,0,0,0.06)" }}>
          <h3 className="font-display mb-4 text-base font-semibold text-stone-800">
            Etik Kurul Basvuru Kontrol Listesi
          </h3>
          <div className="space-y-3">
            {ethicsChecklist.map((item) => (
              <label
                key={item.id}
                className={`flex cursor-pointer items-start gap-3 rounded-xl border p-4 transition-colors ${
                  checkedItems.has(item.id)
                    ? "border-amber-200 bg-amber-50/50"
                    : "border-stone-100 bg-stone-50/50 hover:bg-stone-50"
                }`}
              >
                <div
                  className={`mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-md border transition-colors ${
                    checkedItems.has(item.id) ? "border-amber-400 bg-amber-500 text-white" : "border-stone-300 bg-white"
                  }`}
                  onClick={() => toggleCheck(item.id)}
                >
                  {checkedItems.has(item.id) && <Check className="h-3 w-3" />}
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-stone-700">{item.label}</p>
                  <p className="mt-0.5 flex items-center gap-1 text-[11px] text-stone-400">
                    <FileText className="h-3 w-3" />
                    Gerekli belge: {item.doc}
                  </p>
                </div>
              </label>
            ))}
          </div>
          <div className="mt-6 border-t border-stone-100 pt-4">
            <button
              className="inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-medium text-white transition-colors hover:opacity-90"
              style={{ background: "#E8A157" }}
            >
              <Download className="h-4 w-4" />
              Etik basvuru formu sablonu indir
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
