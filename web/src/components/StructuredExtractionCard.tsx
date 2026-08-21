"use client";

import { useState, useMemo } from "react";
import {
  X,
  Table,
  Target,
  Beaker,
  BarChart3,
  CheckCircle2,
  Database,
  Search,
  Filter,
  ChevronDown,
  ChevronUp,
  ArrowUpDown,
  Info,
  ArrowRight,
  Download,
  ChevronRight,
} from "lucide-react";
import { DataVizCardFrame } from "./DataVizCardFrame";

// ============================================================
// Types
// ============================================================
type RoleKey = "objective" | "method" | "result" | "conclusion" | "sample";
type SortBy = "relevance" | "year" | "confidence";
type SortDir = "asc" | "desc";

interface RoleMeta {
  label: string;
  icon: typeof Target;
  color: string;
}

interface Extraction {
  text: string | null;
  confidence: number;
}

interface Paper {
  id: string;
  title: string;
  authors: string;
  year: number;
  journal: string;
  method: string;
  extractions: Record<RoleKey, Extraction>;
}

const ROLE_CONFIG: Record<RoleKey, RoleMeta> = {
  objective: { label: "Amaç", icon: Target, color: "#4F46E5" },
  method: { label: "Yöntem", icon: Beaker, color: "#7C3AED" },
  result: { label: "Ana Bulgu", icon: BarChart3, color: "#D97706" },
  conclusion: { label: "Sonuç", icon: CheckCircle2, color: "#10B981" },
  sample: { label: "Veri / Örneklem", icon: Database, color: "#0EA5E9" },
};

const ROLE_KEYS: RoleKey[] = ["objective", "method", "result", "conclusion", "sample"];

// ============================================================
// Mock data
// ============================================================
const PAPERS: Paper[] = [
  {
    id: "TR.04.123.0214.0.0.C.M.M.tr.R.1",
    title: "Yükseköğretim Akreditasyonunda AHP-TOPSIS Hibrit Yaklaşımı",
    authors: "Yılmaz, A., Kara, B., ve 3 diğer",
    year: 2024,
    journal: "Studies in Higher Education",
    method: "Nicel",
    extractions: {
      objective: {
        text: "Türk yükseköğretim akreditasyon süreçlerinde çok kriterli karar verme yöntemlerinin uygulanabilirliğini incelemek ve mevcut kriter ağırlıklandırma sisteminin yetersizliklerini ortaya koymak.",
        confidence: 0.91,
      },
      method: {
        text: "12 kurumdan 247 paydaşla yarı-yapılandırılmış görüşme + AHP-TOPSIS hibrit modelleme. Ağırlıklar uzman panelinden, alternatifler kurum verilerinden alındı.",
        confidence: 0.88,
      },
      result: {
        text: "Geleneksel kriterler paydaş perspektiflerini sistematik olarak yetersiz ağırlıklandırmaktadır (p<0.001, ŋ²=0.34). Önerilen yeniden-kalibrasyon eğitim çıktılarıyla %42 daha güçlü korelasyon göstermektedir.",
        confidence: 0.85,
      },
      conclusion: {
        text: "Akreditasyon politikaları paydaş çeşitliliğini ölçen göstergelerle güncellenmelidir; bu özellikle gelişmekte olan ekonomilerde kritik öneme sahiptir.",
        confidence: 0.79,
      },
      sample: {
        text: "n=247 paydaş (yönetici 89, öğretim üyesi 102, öğrenci 56) · 12 üniversite · 7 coğrafi bölge",
        confidence: 0.94,
      },
    },
  },
  {
    id: "EU.04.221.0102.0.0.A.M.E.en.A.1",
    title: "AHP-TOPSIS Hybrid Approach for University Quality Assessment",
    authors: "Demir, M., Şahin, K., ve 2 diğer",
    year: 2023,
    journal: "European Journal of Education",
    method: "Meta-analiz",
    extractions: {
      objective: {
        text: "AHP ve TOPSIS yöntemlerinin birleşik bir çerçevede üniversite kalitesini değerlendirmedeki etkinliğini test etmek.",
        confidence: 0.93,
      },
      method: {
        text: "Avrupa ve Türkiye'den 12 kurumdan veri kullanılarak hibrit AHP-TOPSIS modeli; meta-analiz ile 47 önceki çalışma sonuçları sentezlendi.",
        confidence: 0.9,
      },
      result: {
        text: "Hibrit yaklaşım tek-yöntem uygulamalarına göre %18 daha yüksek sıralama tutarlılığı sağladı (Spearman ρ=0.84).",
        confidence: 0.86,
      },
      conclusion: {
        text: "Hibrit MCDM yöntemleri kalite değerlendirmesinde standart hale gelmelidir; ancak ağırlıklandırma şeffaflığı korunmalıdır.",
        confidence: 0.81,
      },
      sample: {
        text: "12 üniversite + 47 meta-analiz çalışması · 5 yıl (2018-2023)",
        confidence: 0.92,
      },
    },
  },
  {
    id: "TR.05.118.0214.0.0.B.M.Q.tr.R.1",
    title: "Stakeholder Perspectives on Accreditation Criteria",
    authors: "Aydın, F., Çelik, R.",
    year: 2024,
    journal: "Quality in Higher Education",
    method: "Nitel",
    extractions: {
      objective: {
        text: "Akreditasyon kriterlerinin paydaş gözüyle hangi boyutlarda eksik veya çelişkili olduğunu anlamak.",
        confidence: 0.89,
      },
      method: {
        text: "34 paydaşla derinlemesine yarı-yapılandırılmış görüşme · tematik analiz · NVivo 12 kullanımı.",
        confidence: 0.92,
      },
      result: { text: null, confidence: 0 },
      conclusion: {
        text: "Paydaş perspektifleri arasındaki çelişkiler tek bir 'doğru' kriter setinin imkansızlığına işaret eder; çoğulcu modeller önerilir.",
        confidence: 0.74,
      },
      sample: {
        text: "n=34 paydaş · 8 kurum · 3 paydaş kategorisi (yönetici, akademik, öğrenci)",
        confidence: 0.95,
      },
    },
  },
  {
    id: "EU.06.118.0102.0.0.A.M.E.en.A.1",
    title: "ENTROPY-VIKOR for Educational Quality Indicators",
    authors: "Öztürk, S., Polat, H., ve 4 diğer",
    year: 2023,
    journal: "Computers & Education",
    method: "Nicel",
    extractions: {
      objective: {
        text: "K-12 ve yükseköğretim kalite göstergelerini ENTROPY-VIKOR hibrit yöntemiyle önceliklendirmek.",
        confidence: 0.94,
      },
      method: {
        text: "ENTROPY ile objektif ağırlıklandırma + VIKOR ile sıralama. Veri: ulusal eğitim istatistik veritabanları (2018-2023).",
        confidence: 0.91,
      },
      result: {
        text: "Öğretmen-öğrenci oranı ve dijital altyapı göstergeleri en yüksek belirleyici ağırlığa sahip; finansman göstergeleri orta düzeyde.",
        confidence: 0.87,
      },
      conclusion: {
        text: "ENTROPY-VIKOR kombinasyonu öznellik içermeyen sıralama için güçlü bir yaklaşımdır.",
        confidence: 0.83,
      },
      sample: {
        text: "5 yıllık ulusal istatistik · 81 il · 24 gösterge",
        confidence: 0.96,
      },
    },
  },
  {
    id: "EU.04.221.0214.0.0.A.M.A.en.A.1",
    title: "Fuzzy AHP in Higher Education Quality: A Systematic Review",
    authors: "Chen, L., Patel, R.",
    year: 2022,
    journal: "Applied Soft Computing",
    method: "Sistematik derleme",
    extractions: {
      objective: {
        text: "Bulanık AHP'nin yükseköğretim kalite uygulamalarındaki kullanımını sistematik olarak haritalamak.",
        confidence: 0.92,
      },
      method: {
        text: "PRISMA protokolü · 142 çalışma tarandı, 38'i derinlemesine analiz edildi · 2010-2022 aralığı.",
        confidence: 0.94,
      },
      result: {
        text: "Bulanık AHP uygulamalarının %68'i tek bir kurum bağlamında kalmış, çapraz-kurum karşılaştırması yapılmamıştır.",
        confidence: 0.88,
      },
      conclusion: {
        text: "Çapraz-kurum genelleştirilebilirlik bulanık MCDM literatürünün en kritik açığıdır.",
        confidence: 0.85,
      },
      sample: {
        text: "142 derleme + 38 derinlemesine · 13 yıl",
        confidence: 0.93,
      },
    },
  },
  {
    id: "TR.05.118.0214.0.0.C.M.A.tr.R.1",
    title: "Türkiye'de Yükseköğretim Politika Etkinliği: PROMETHEE Analizi",
    authors: "Müller, K., Schmidt, A.",
    year: 2023,
    journal: "Higher Education Policy",
    method: "Nicel",
    extractions: {
      objective: {
        text: "2010-2023 dönemi yükseköğretim politikalarının PROMETHEE ile etkinlik değerlendirmesini yapmak.",
        confidence: 0.9,
      },
      method: {
        text: "PROMETHEE II tam sıralama yöntemi · 8 politika alternatifi · 12 değerlendirme kriteri.",
        confidence: 0.89,
      },
      result: {
        text: "Erişim politikaları en yüksek etkinlik puanını aldı (φ=+0.42), kalite politikaları orta düzeyde, finansman politikaları düşük (φ=-0.28).",
        confidence: 0.84,
      },
      conclusion: {
        text: "Politikaların etkinliği ölçülebilir ancak çoklu hedeflerin tartılması siyasi tercih gerektirir.",
        confidence: 0.76,
      },
      sample: {
        text: "8 politika · 12 kriter · 13 yıllık zaman serisi",
        confidence: 0.91,
      },
    },
  },
  {
    id: "EU.06.221.0102.0.0.A.M.E.en.A.1",
    title: "Multi-Criteria Methods in Online Education Quality",
    authors: "García, C., Rossi, G.",
    year: 2024,
    journal: "Distance Education",
    method: "Karma yöntem",
    extractions: {
      objective: {
        text: "Online eğitim kalitesinin çok boyutlu değerlendirilmesinde MCDM yöntemlerinin uygulanabilirliğini test etmek.",
        confidence: 0.91,
      },
      method: { text: null, confidence: 0 },
      result: {
        text: "Pedagojik tasarım kriteri en güçlü ayırt edici güce sahip; teknolojik altyapı ikincil öneme sahip.",
        confidence: 0.82,
      },
      conclusion: {
        text: "MCDM online eğitim kalitesinde standart aracı olabilir, fakat öğrenci deneyimi göstergeleri ön planda olmalı.",
        confidence: 0.78,
      },
      sample: {
        text: "n=156 online program · 4 ülke",
        confidence: 0.93,
      },
    },
  },
  {
    id: "TR.04.118.0214.0.0.B.M.M.tr.R.1",
    title: "Akreditasyon Süreçlerinde DEMATEL Yaklaşımı",
    authors: "Kara, B., Ahmad, F., Aksoy, S.",
    year: 2024,
    journal: "Higher Education Quarterly",
    method: "Nicel",
    extractions: {
      objective: {
        text: "Akreditasyon kriterleri arasındaki neden-sonuç ilişkilerini DEMATEL ile haritalamak.",
        confidence: 0.93,
      },
      method: {
        text: "DEMATEL · 18 uzman değerlendirmesi · ilişki matrisi normalizasyonu.",
        confidence: 0.9,
      },
      result: {
        text: "Yönetişim kalitesi diğer 6 kriterin nedeni olarak konumlanırken, mezun başarısı sonuç tarafında yer aldı.",
        confidence: 0.86,
      },
      conclusion: {
        text: "Akreditasyon kriterleri eşit ağırlıklı değil; bazıları neden, bazıları sonuç. Bu ayrım politika tasarımında kritik.",
        confidence: 0.81,
      },
      sample: {
        text: "18 uzman · 9 kriter · ilişki matrisi 9×9",
        confidence: 0.92,
      },
    },
  },
];

// ============================================================
// Confidence badge
// ============================================================
function ConfidenceBadge({ value }: { value: number }) {
  if (!value || value === 0) return null;
  const pct = Math.round(value * 100);
  let color: string;
  let bg: string;
  let label: string;
  if (value >= 0.85) {
    color = "#047857";
    bg = "#ECFDF5";
    label = "Yüksek";
  } else if (value >= 0.7) {
    color = "#B45309";
    bg = "#FEF3C7";
    label = "Orta";
  } else {
    color = "#7C2D12";
    bg = "#FEE2E2";
    label = "Düşük";
  }

  return (
    <span
      className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-mono-pmid font-semibold"
      style={{ background: bg, color }}
      title={`${label} güven · SciBERT classification confidence`}
    >
      %{pct}
    </span>
  );
}

// ============================================================
// Extraction cell
// ============================================================
function ExtractionCell({
  extraction,
  expanded,
  onToggle,
}: {
  extraction: Extraction | undefined;
  expanded: boolean;
  onToggle: () => void;
}) {
  if (!extraction || !extraction.text) {
    return (
      <div className="flex items-center justify-center h-full min-h-[60px] text-stone-300 text-sm italic">
        — yok
      </div>
    );
  }

  const text = extraction.text;
  const isLong = text.length > 110;
  const truncated = isLong && !expanded ? text.slice(0, 110) + "…" : text;

  return (
    <div className="space-y-1.5">
      <p className="font-crimson text-[13px] text-stone-800 leading-snug">
        {truncated}
      </p>
      <div className="flex items-center justify-between">
        <ConfidenceBadge value={extraction.confidence} />
        {isLong && (
          <button
            onClick={onToggle}
            className="text-[10px] font-medium text-indigo-600 hover:underline flex items-center gap-0.5"
          >
            {expanded ? (
              <>
                <ChevronUp className="w-2.5 h-2.5" />
                Kısalt
              </>
            ) : (
              <>
                <ChevronDown className="w-2.5 h-2.5" />
                Tamamı
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
}

// ============================================================
// Paper row
// ============================================================
function PaperRow({
  paper,
  expandedCells,
  toggleCell,
  onSelect,
  isSelected,
}: {
  paper: Paper;
  expandedCells: Set<string>;
  toggleCell: (key: string) => void;
  onSelect: (id: string) => void;
  isSelected: boolean;
}) {
  return (
    <div
      className={`grid border-b border-stone-100 transition-colors ${
        isSelected ? "bg-indigo-50/30" : "hover:bg-stone-50/60"
      }`}
      style={{ gridTemplateColumns: "260px repeat(5, minmax(190px, 1fr))" }}
    >
      <div
        className="p-3 border-r border-stone-100 cursor-pointer sticky left-0 z-[1]"
        style={{ background: isSelected ? "#EEF2FFCC" : "#FFFFFF" }}
        onClick={() => onSelect(paper.id)}
      >
        <div className="flex items-start gap-2">
          <button
            type="button"
            className="mt-0.5 w-4 h-4 rounded-sm border-2 flex items-center justify-center flex-shrink-0 transition-colors"
            style={{
              borderColor: isSelected ? "#4F46E5" : "#D6D3D1",
              background: isSelected ? "#4F46E5" : "white",
            }}
            aria-label={isSelected ? "Seçimi kaldır" : "Seç"}
          >
            {isSelected && (
              <CheckCircle2
                className="w-2.5 h-2.5 text-white"
                strokeWidth={3}
              />
            )}
          </button>
          <div className="flex-1 min-w-0">
            <div
              className="text-[9px] font-mono-pmid text-stone-400 truncate mb-1"
              title={paper.id}
            >
              {paper.id}
            </div>
            <h4 className="font-crimson italic text-[13px] font-semibold text-stone-900 leading-snug mb-1.5 line-clamp-2">
              {paper.title}
            </h4>
            <div className="text-[11px] text-stone-600 truncate mb-1">
              {paper.authors}
            </div>
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-[10px] italic text-stone-500 truncate">
                {paper.journal}
              </span>
              <span className="text-[10px] font-mono-pmid text-stone-400">
                {paper.year}
              </span>
              <span className="px-1.5 py-0.5 rounded text-[9px] font-medium bg-indigo-50 text-indigo-700 border border-indigo-100">
                {paper.method}
              </span>
            </div>
          </div>
        </div>
      </div>

      {ROLE_KEYS.map((roleKey) => (
        <div
          key={roleKey}
          className="p-3 border-r border-stone-100 last:border-r-0"
        >
          <ExtractionCell
            extraction={paper.extractions[roleKey]}
            expanded={expandedCells.has(`${paper.id}:${roleKey}`)}
            onToggle={() => toggleCell(`${paper.id}:${roleKey}`)}
          />
        </div>
      ))}
    </div>
  );
}

// ============================================================
// Selection panel
// ============================================================
function SelectionPanel({
  selectedIds,
  onClear,
  onCompare,
}: {
  selectedIds: Set<string>;
  onClear: () => void;
  onCompare: () => void;
}) {
  if (selectedIds.size === 0) return null;
  return (
    <div
      className="bg-white rounded-2xl border border-stone-200 p-4 mt-4 flex items-center justify-between gap-4 flex-wrap animate-[slideUp_0.3s_cubic-bezier(0.16,1,0.3,1)]"
      style={{
        boxShadow: "0 4px 16px -4px rgba(0,0,0,0.08)",
        borderLeft: "3px solid #4F46E5",
      }}
    >
      <div className="flex items-center gap-3">
        <div
          className="w-10 h-10 rounded-xl flex items-center justify-center"
          style={{
            background: "linear-gradient(135deg, #EEF2FF 0%, #F5F3FF 100%)",
            color: "#4F46E5",
          }}
        >
          <CheckCircle2 className="w-5 h-5" strokeWidth={2} />
        </div>
        <div>
          <div className="font-crimson italic text-base font-semibold text-stone-900 leading-tight">
            {selectedIds.size} makale seçildi
          </div>
          <div className="text-xs text-stone-500">
            Yan yana karşılaştırma yapın veya toplu işlem uygulayın
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2 flex-wrap">
        <button
          onClick={onCompare}
          disabled={selectedIds.size < 2}
          className="px-3 py-1.5 rounded-lg text-xs font-medium text-white transition-all hover:scale-[1.02] disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:scale-100 flex items-center gap-1.5"
          style={{
            background: "linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)",
          }}
        >
          <ArrowRight className="w-3 h-3" />
          Karşılaştırma görünümü
        </button>
        <button className="px-3 py-1.5 rounded-lg text-xs font-medium text-stone-700 border border-stone-200 hover:bg-stone-50 transition-colors flex items-center gap-1.5">
          <Download className="w-3 h-3" />
          CSV / BibTeX
        </button>
        <button className="px-3 py-1.5 rounded-lg text-xs font-medium text-stone-700 border border-stone-200 hover:bg-stone-50 transition-colors">
          Listeme ekle
        </button>
        <button
          onClick={onClear}
          className="px-3 py-1.5 rounded-lg text-xs font-medium text-stone-500 hover:bg-stone-100 transition-colors"
        >
          Temizle
        </button>
      </div>
    </div>
  );
}

// ============================================================
// Main
// ============================================================
export default function StructuredExtractionCard() {
  const [query, setQuery] = useState("");
  const [methodFilter, setMethodFilter] = useState("all");
  const [yearFilter, setYearFilter] = useState("all");
  const [highConfidenceOnly, setHighConfidenceOnly] = useState(false);
  const [sortBy, setSortBy] = useState<SortBy>("relevance");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [expandedCells, setExpandedCells] = useState<Set<string>>(new Set());
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [filterOpen, setFilterOpen] = useState(true);

  const toggleCell = (key: string) => {
    setExpandedCells((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const togglePaperSelection = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const filteredPapers = useMemo(() => {
    let result = [...PAPERS];

    if (query) {
      const q = query.toLowerCase();
      result = result.filter((p) => {
        if (p.title.toLowerCase().includes(q)) return true;
        if (p.authors.toLowerCase().includes(q)) return true;
        return Object.values(p.extractions).some(
          (e) => e?.text && e.text.toLowerCase().includes(q),
        );
      });
    }

    if (methodFilter !== "all") {
      result = result.filter((p) => p.method === methodFilter);
    }

    if (yearFilter !== "all") {
      const cutoff = parseInt(yearFilter, 10);
      result = result.filter((p) => p.year >= cutoff);
    }

    if (highConfidenceOnly) {
      result = result.filter((p) => {
        const confidences = Object.values(p.extractions).map(
          (e) => e?.confidence ?? 0,
        );
        const avg =
          confidences.reduce((a, b) => a + b, 0) / confidences.length;
        return avg >= 0.8;
      });
    }

    if (sortBy === "year") {
      result.sort((a, b) =>
        sortDir === "desc" ? b.year - a.year : a.year - b.year,
      );
    } else if (sortBy === "confidence") {
      result.sort((a, b) => {
        const aAvg =
          Object.values(a.extractions).reduce(
            (s, e) => s + (e?.confidence ?? 0),
            0,
          ) / 5;
        const bAvg =
          Object.values(b.extractions).reduce(
            (s, e) => s + (e?.confidence ?? 0),
            0,
          ) / 5;
        return sortDir === "desc" ? bAvg - aAvg : aAvg - bAvg;
      });
    }

    return result;
  }, [query, methodFilter, yearFilter, highConfidenceOnly, sortBy, sortDir]);

  const totalExtractions = filteredPapers.reduce(
    (sum, p) =>
      sum + Object.values(p.extractions).filter((e) => e?.text).length,
    0,
  );

  const methods = useMemo(
    () => Array.from(new Set(PAPERS.map((p) => p.method))),
    [],
  );

  const activeFilterCount =
    (query ? 1 : 0) +
    (methodFilter !== "all" ? 1 : 0) +
    (yearFilter !== "all" ? 1 : 0) +
    (highConfidenceOnly ? 1 : 0);

  const clearAllFilters = () => {
    setQuery("");
    setMethodFilter("all");
    setYearFilter("all");
    setHighConfidenceOnly(false);
  };

  return (
    <>
      <DataVizCardFrame
        zone="curation"
        customIcon={Table}
        title="Yapısal çıkarım tablosu"
        subtitle="Paper × Rol matrisi · Her hücre SciBERT-sınıflandırılmış cümle özeti"
        sourceBadge="SciBERT 5-class · 193.65M cümle"
        onFullscreen={() => {}}
        onExport={() => {}}
        onOpenNew={() => {}}
        legend={
          <div className="flex items-center gap-3 flex-wrap">
            {ROLE_KEYS.map((key) => {
              const r = ROLE_CONFIG[key];
              const RIcon = r.icon;
              return (
                <div key={key} className="flex items-center gap-1.5">
                  <div
                    className="w-5 h-5 rounded flex items-center justify-center"
                    style={{ background: `${r.color}15`, color: r.color }}
                  >
                    <RIcon className="w-2.5 h-2.5" strokeWidth={2.5} />
                  </div>
                  <span className="text-xs text-stone-700 font-medium">
                    {r.label}
                  </span>
                </div>
              );
            })}
          </div>
        }
        controls={
          <div className="flex items-center gap-3 text-[11px]">
            <span className="text-stone-500">
              <span className="font-mono-pmid font-semibold text-stone-700">
                {filteredPapers.length}
              </span>{" "}
              paper ·
              <span className="font-mono-pmid font-semibold text-stone-700 ml-1">
                {totalExtractions}
              </span>{" "}
              hücre dolu
            </span>
          </div>
        }
      >
        {/* Filter bar */}
        <div className="border-b border-stone-200 bg-white">
          <div className="px-4 md:px-5 py-3 flex items-center justify-between gap-3 flex-wrap">
            <button
              onClick={() => setFilterOpen(!filterOpen)}
              className="flex items-center gap-2 text-sm font-semibold text-stone-700 hover:text-stone-900 transition-colors"
            >
              {filterOpen ? (
                <ChevronDown className="w-4 h-4" />
              ) : (
                <ChevronRight className="w-4 h-4" />
              )}
              <Filter className="w-3.5 h-3.5 text-stone-400" />
              Filtre &amp; arama
              {activeFilterCount > 0 && (
                <span
                  className="px-1.5 py-0.5 rounded-md text-[10px] font-mono-pmid font-bold text-white"
                  style={{ background: "#4F46E5" }}
                >
                  {activeFilterCount}
                </span>
              )}
            </button>

            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[11px] text-stone-500">Sırala:</span>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortBy)}
                className="text-[11px] border border-stone-200 rounded-md px-2 py-1 bg-white text-stone-700 focus:outline-none focus:border-indigo-400"
              >
                <option value="relevance">İlgililik</option>
                <option value="year">Yıl</option>
                <option value="confidence">Güven skoru</option>
              </select>
              <button
                onClick={() => setSortDir(sortDir === "desc" ? "asc" : "desc")}
                className="px-1.5 py-1 rounded-md border border-stone-200 text-stone-500 hover:bg-stone-50 transition-colors"
                title={sortDir === "desc" ? "Azalan" : "Artan"}
              >
                <ArrowUpDown className="w-3 h-3" />
              </button>
            </div>
          </div>

          {filterOpen && (
            <div className="px-4 md:px-5 pb-3 border-t border-stone-100">
              <div className="grid md:grid-cols-12 gap-2 pt-3">
                <div className="md:col-span-5">
                  <div className="relative">
                    <Search className="w-3.5 h-3.5 text-stone-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                    <input
                      type="text"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder="Çıkarımlarda ara: yöntem, sonuç, veri..."
                      className="w-full pl-9 pr-3 py-2 rounded-lg border border-stone-200 text-sm text-stone-800 placeholder-stone-400 focus:outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 bg-stone-50 focus:bg-white transition-all"
                    />
                    {query && (
                      <button
                        onClick={() => setQuery("")}
                        className="absolute right-2 top-1/2 -translate-y-1/2 w-5 h-5 rounded flex items-center justify-center text-stone-400 hover:bg-stone-100"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                </div>

                <div className="md:col-span-3">
                  <select
                    value={methodFilter}
                    onChange={(e) => setMethodFilter(e.target.value)}
                    className="w-full text-sm border border-stone-200 rounded-lg px-3 py-2 bg-stone-50 text-stone-700 focus:outline-none focus:border-indigo-400 focus:bg-white"
                  >
                    <option value="all">Tüm yöntemler</option>
                    {methods.map((m) => (
                      <option key={m} value={m}>
                        {m}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="md:col-span-2">
                  <select
                    value={yearFilter}
                    onChange={(e) => setYearFilter(e.target.value)}
                    className="w-full text-sm border border-stone-200 rounded-lg px-3 py-2 bg-stone-50 text-stone-700 focus:outline-none focus:border-indigo-400 focus:bg-white"
                  >
                    <option value="all">Tüm yıllar</option>
                    <option value="2024">2024+</option>
                    <option value="2023">2023+</option>
                    <option value="2022">2022+</option>
                  </select>
                </div>

                <div className="md:col-span-2 flex items-center">
                  <label className="flex items-center gap-2 cursor-pointer text-sm text-stone-700 px-3 py-2 rounded-lg border border-stone-200 bg-stone-50 hover:bg-white transition-colors w-full">
                    <input
                      type="checkbox"
                      checked={highConfidenceOnly}
                      onChange={(e) => setHighConfidenceOnly(e.target.checked)}
                      className="w-3.5 h-3.5 rounded accent-indigo-600"
                    />
                    <span className="text-xs">Yüksek güven</span>
                  </label>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Table */}
        <div className="overflow-x-auto bg-white">
          <div className="min-w-[1210px]">
            <div
              className="grid border-b border-stone-200 bg-stone-50 sticky top-0 z-10"
              style={{
                gridTemplateColumns: "260px repeat(5, minmax(190px, 1fr))",
              }}
            >
              <div className="p-3 border-r border-stone-200 text-[10px] font-semibold text-stone-500 uppercase tracking-widest sticky left-0 bg-stone-50 z-[2]">
                Paper
              </div>
              {ROLE_KEYS.map((key) => {
                const r = ROLE_CONFIG[key];
                const RIcon = r.icon;
                return (
                  <div
                    key={key}
                    className="p-3 border-r border-stone-200 last:border-r-0"
                  >
                    <div
                      className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-widest"
                      style={{ color: r.color }}
                    >
                      <RIcon className="w-3 h-3" strokeWidth={2.5} />
                      {r.label}
                    </div>
                  </div>
                );
              })}
            </div>

            {filteredPapers.length === 0 ? (
              <div className="p-16 text-center">
                <div className="w-14 h-14 mx-auto rounded-2xl flex items-center justify-center mb-4 bg-stone-100">
                  <Search className="w-6 h-6 text-stone-400" />
                </div>
                <h4 className="font-crimson italic text-lg font-semibold text-stone-700 mb-1">
                  Sonuç bulunamadı
                </h4>
                <p className="text-sm text-stone-500 mb-4">
                  Filtrelerinizi gevşetmeyi veya farklı bir arama terimi denemeyi
                  düşünün.
                </p>
                <button
                  onClick={clearAllFilters}
                  className="text-sm text-indigo-600 font-medium hover:underline"
                >
                  Tüm filtreleri temizle
                </button>
              </div>
            ) : (
              filteredPapers.map((paper) => (
                <PaperRow
                  key={paper.id}
                  paper={paper}
                  expandedCells={expandedCells}
                  toggleCell={toggleCell}
                  onSelect={togglePaperSelection}
                  isSelected={selectedIds.has(paper.id)}
                />
              ))
            )}
          </div>
        </div>

        <div className="px-5 py-3 border-t border-stone-100 bg-stone-50/50 flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2 text-[11px] text-stone-500 italic">
            <Info className="w-3 h-3" />
            <span>
              Her hücredeki cümle SciBERT 5-class sınıflandırma ile çıkarıldı ·
              Güven skoru = classification confidence
            </span>
          </div>
          <button className="text-[11px] text-indigo-600 font-medium hover:underline">
            Yöntem detayı
          </button>
        </div>
      </DataVizCardFrame>

      <SelectionPanel
        selectedIds={selectedIds}
        onClear={() => setSelectedIds(new Set())}
        onCompare={() => {}}
      />
    </>
  );
}
