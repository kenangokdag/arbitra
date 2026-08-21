"use client";

import { useState, useRef, useMemo, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { BRAND } from "@/lib/brand";
import {
  Compass,
  Maximize2,
  ExternalLink,
  Download,
  X,
  Layers,
  Sparkles,
  Map,
  Filter,
  Target,
  TrendingUp,
  TrendingDown,
  Minus,
  Search,
  Zap,
  ChevronDown,
  ChevronUp,
  type LucideIcon,
} from "lucide-react";
import * as d3 from "d3";

// ============================================================
// SHARED — DataViz Card Frame
// ============================================================

type ZoneId = "discovery" | "curation" | "gapatlas" | "authoring" | "defense";

const ZONE_CONFIG: Record<ZoneId, { label: string; color: string; bg: string; icon: LucideIcon }> = {
  discovery: { label: "Kesif", color: "#D97706", bg: "#FEF3C7", icon: Compass },
  curation: { label: "Suzme & Inceleme", color: "#D97706", bg: "#FEF3C7", icon: Layers },
  gapatlas: { label: "Literatur Boslugu", color: "#0E4F4A", bg: "#F0FDFA", icon: Map },
  authoring: { label: "Yazim & Hazirlik", color: "#D97706", bg: "#FEF3C7", icon: Layers },
  defense: { label: "Savunma", color: "#C9A961", bg: "#FEF7E0", icon: Layers },
};

function DataVizCardFrame({
  zone = "curation",
  title,
  subtitle,
  sourceBadge,
  uniqueBadge = false,
  children,
  legend,
  controls,
  onFullscreen,
  onExport,
  onOpenNew,
  prominent = false,
  customIcon,
}: {
  zone?: ZoneId;
  title: string;
  subtitle?: string;
  sourceBadge?: string;
  uniqueBadge?: boolean;
  children: ReactNode;
  legend?: ReactNode;
  controls?: ReactNode;
  onFullscreen?: () => void;
  onExport?: () => void;
  onOpenNew?: () => void;
  prominent?: boolean;
  customIcon?: LucideIcon;
}) {
  const z = ZONE_CONFIG[zone];
  const ZIcon = customIcon ?? z.icon;

  return (
    <div
      className="relative overflow-hidden rounded-2xl bg-white transition-all"
      style={{
        border: prominent ? `2px solid ${z.color}40` : "1px solid #E7E5E4",
        boxShadow: prominent
          ? `0 4px 24px -4px ${z.color}30, 0 1px 2px rgba(0,0,0,0.04)`
          : "0 1px 2px rgba(0,0,0,0.02)",
      }}
    >
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-stone-100 px-5 py-4 md:px-6">
        <div className="flex min-w-0 flex-1 items-start gap-3">
          <div
            className="mt-0.5 flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg"
            style={{ background: `${z.color}15`, color: z.color }}
          >
            <ZIcon className="h-4 w-4" strokeWidth={2} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="font-display text-lg font-semibold italic leading-tight text-stone-900 md:text-xl">
                {title}
              </h3>
              {uniqueBadge && (
                <span
                  className="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold"
                  style={{ background: `${z.color}15`, color: z.color, borderColor: `${z.color}40` }}
                >
                  <Sparkles className="h-2.5 w-2.5" strokeWidth={2.5} />
                  Sadece {BRAND}&#39;da
                </span>
              )}
            </div>
            {subtitle && <p className="mt-0.5 text-xs leading-relaxed text-stone-500">{subtitle}</p>}
            {sourceBadge && (
              <span
                className={`mt-2 inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 font-mono text-[11px] ${prominent ? "font-semibold" : ""}`}
                style={{
                  background: prominent ? `${z.color}15` : "#F5F5F4",
                  color: prominent ? z.color : "#57534E",
                  border: `1px solid ${prominent ? `${z.color}30` : "#E7E5E4"}`,
                }}
              >
                <span className="h-1 w-1 rounded-full" style={{ background: prominent ? z.color : "#A8A29E" }} />
                {sourceBadge}
              </span>
            )}
          </div>
        </div>
        <div className="flex flex-shrink-0 items-center gap-1">
          <button onClick={onFullscreen} title="Tam ekran" className="flex h-8 w-8 items-center justify-center rounded-lg text-stone-500 transition-colors hover:bg-stone-100 hover:text-stone-700">
            <Maximize2 className="h-3.5 w-3.5" />
          </button>
          <button onClick={onOpenNew} title="Yeni sekmede ac" className="flex h-8 w-8 items-center justify-center rounded-lg text-stone-500 transition-colors hover:bg-stone-100 hover:text-stone-700">
            <ExternalLink className="h-3.5 w-3.5" />
          </button>
          <button onClick={onExport} title="Disa aktar" className="flex h-8 w-8 items-center justify-center rounded-lg text-stone-500 transition-colors hover:bg-stone-100 hover:text-stone-700">
            <Download className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
      <div className="relative bg-stone-50/40">{children}</div>
      {(legend || controls) && (
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-stone-100 bg-white px-5 py-3 md:px-6">
          {legend && <div className="flex flex-wrap items-center gap-4">{legend}</div>}
          {controls && <div className="flex flex-wrap items-center gap-2">{controls}</div>}
        </div>
      )}
    </div>
  );
}

// ============================================================
// API TYPES
// ============================================================

interface MethodDef {
  id: string;
  label: string;
  family: string;
}

interface TopicDef {
  id: string;
  label: string;
  group: string;
}

interface GapCell {
  methodId: string;
  topicId: string;
  methodIdx: number;
  topicIdx: number;
  paperCount: number;
  gapScore: number;          // 0–100 scale for display
  trend: "up" | "down" | "stable";
  isGold: boolean;
}

interface GapHeatmapApiResponse {
  methods: MethodDef[];
  topics: TopicDef[];
  cells: {
    method_id: string;
    topic_id: string;
    n_papers: number;
    gap_score: number;   // 0–1 from API
    depth_norm: number;
    is_gold: boolean;
  }[];
  total_cells: number;
  matrix_id: string;
}

async function fetchGapHeatmap(): Promise<GapHeatmapApiResponse> {
  return apiFetch<GapHeatmapApiResponse>("/api/gap-heatmap?top_methods=14&top_topics=18");
}

function apiToGapCells(
  apiCells: GapHeatmapApiResponse["cells"],
  methods: MethodDef[],
  topics: TopicDef[],
): GapCell[] {
  const methodIdx = Object.fromEntries(methods.map((m, i) => [m.id, i]));
  const topicIdx = Object.fromEntries(topics.map((t, i) => [t.id, i]));
  return apiCells
    .filter((c) => methodIdx[c.method_id] !== undefined && topicIdx[c.topic_id] !== undefined)
    .map((c) => ({
      methodId: c.method_id,
      topicId: c.topic_id,
      methodIdx: methodIdx[c.method_id]!,
      topicIdx: topicIdx[c.topic_id]!,
      paperCount: c.n_papers,
      gapScore: Math.round(c.gap_score * 100),  // 0-1 → 0-100
      trend: "stable" as const,
      isGold: c.is_gold,
    }));
}

// ============================================================
// HEATMAP CELL COLOR
// ============================================================

type ColorMode = "gap" | "count" | "trend";

const colorScale = d3
  .scaleLinear<string>()
  .domain([0, 0.5, 1])
  .range(["#134E4A", "#E7E5E4", "#F59E0B"])
  .interpolate(d3.interpolateRgb);

function getCellColor(cell: GapCell, mode: ColorMode): string {
  if (cell.gapScore < 0) return "#F5F5F4";

  let value: number;
  if (mode === "gap") value = cell.gapScore / 100;
  else if (mode === "count") value = 1 - Math.min(1, cell.paperCount / 100);
  else {
    if (cell.trend === "up") value = 0.85;
    else if (cell.trend === "stable") value = 0.5;
    else value = 0.15;
  }

  return colorScale(value) ?? "#E7E5E4";
}

// ============================================================
// HEATMAP GRID
// ============================================================

function HeatmapGrid({
  data,
  methods,
  topics,
  mode,
  onCellHover,
  onCellClick,
  hoveredCell,
  selectedCell,
  showOnlyGaps,
  query,
  profileFilter,
}: {
  data: GapCell[];
  methods: MethodDef[];
  topics: TopicDef[];
  mode: ColorMode;
  onCellHover: (cell: GapCell | null) => void;
  onCellClick: (cell: GapCell) => void;
  hoveredCell: GapCell | null;
  selectedCell: GapCell | null;
  showOnlyGaps: boolean;
  query: string;
  profileFilter: boolean;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cellSize = 38;
  const cellGap = 3;
  const labelLeft = 170;
  const labelTop = 130;

  const matchesQuery = (str: string) => {
    if (!query) return true;
    return str.toLowerCase().includes(query.toLowerCase());
  };

  const isCellVisible = (cell: GapCell) => {
    if (showOnlyGaps && cell.gapScore < 50) return false;
    const m = methods[cell.methodIdx];
    const t = topics[cell.topicIdx];
    if (!m || !t) return false;
    if (query && !matchesQuery(m.label) && !matchesQuery(t.label) && !matchesQuery(m.family) && !matchesQuery(t.group)) return false;
    if (profileFilter) {
      const userMethods = ["Network/Pairwise", "Reference-based", "Fuzzy"];
      const userTopics = ["Egitim", "Kalite", "Diger"];
      if (!userMethods.includes(m.family) || !userTopics.includes(t.group)) return false;
    }
    return true;
  };

  const totalWidth = labelLeft + topics.length * cellSize + 30;
  const totalHeight = labelTop + methods.length * cellSize + 30;

  // Topic group bands
  const topicGroups: { name: string; start: number; end: number }[] = [];
  let currentTG: { name: string; start: number; end: number } | null = null;
  topics.forEach((t, i) => {
    if (!currentTG || currentTG.name !== t.group) {
      if (currentTG) topicGroups.push(currentTG);
      currentTG = { name: t.group, start: i, end: i };
    } else {
      currentTG.end = i;
    }
  });
  if (currentTG) topicGroups.push(currentTG);

  // Method family bands
  const methodGroups: { name: string; start: number; end: number }[] = [];
  let currentMG: { name: string; start: number; end: number } | null = null;
  methods.forEach((m, i) => {
    if (!currentMG || currentMG.name !== m.family) {
      if (currentMG) methodGroups.push(currentMG);
      currentMG = { name: m.family, start: i, end: i };
    } else {
      currentMG.end = i;
    }
  });
  if (currentMG) methodGroups.push(currentMG);

  return (
    <div ref={containerRef} className="overflow-auto" style={{ maxHeight: "640px" }}>
      <svg width={totalWidth} height={totalHeight} style={{ display: "block", background: "#FFFFFF" }}>
        <defs>
          <pattern id="empty-cell-pattern" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <line x1="0" y1="0" x2="0" y2="6" stroke="#E7E5E4" strokeWidth="1.5" />
          </pattern>
        </defs>

        {/* Topic group bands */}
        {topicGroups.map((g, i) => (
          <g key={`tg-${i}`}>
            <rect
              x={labelLeft + g.start * cellSize}
              y={labelTop - 118}
              width={(g.end - g.start + 1) * cellSize - cellGap}
              height={22}
              fill="#F0FDFA"
              stroke="#0E4F4A"
              strokeOpacity="0.25"
              strokeWidth="1"
              rx="4"
            />
            <text
              x={labelLeft + g.start * cellSize + ((g.end - g.start + 1) * cellSize - cellGap) / 2}
              y={labelTop - 102}
              textAnchor="middle"
              fontSize="11"
              fontWeight="700"
              fill="#0E4F4A"
              fontFamily="Inter, sans-serif"
              style={{ textTransform: "uppercase", letterSpacing: "0.06em" }}
            >
              {g.name}
            </text>
          </g>
        ))}

        {/* Topic labels */}
        {topics.map((t, i) => (
          <g key={t.id} transform={`translate(${labelLeft + i * cellSize + (cellSize - cellGap) / 2}, ${labelTop - 12})`}>
            <text
              transform="rotate(-40)"
              textAnchor="end"
              fontSize="13"
              fontWeight={query && matchesQuery(t.label) ? 700 : 500}
              fill={query && matchesQuery(t.label) ? "#0E4F4A" : "#1C1917"}
              fontFamily="Inter, sans-serif"
            >
              {t.label}
            </text>
          </g>
        ))}

        {/* Method family bands */}
        {methodGroups.map((g, i) => {
          const bandHeight = (g.end - g.start + 1) * cellSize - cellGap;
          const cy = labelTop + g.start * cellSize + bandHeight / 2;
          const displayName = g.name.length > 14 ? g.name.slice(0, 13) + "..." : g.name;
          return (
            <g key={`mg-${i}`}>
              <rect
                x={6}
                y={labelTop + g.start * cellSize}
                width={26}
                height={bandHeight}
                fill="#F0FDFA"
                stroke="#0E4F4A"
                strokeOpacity="0.25"
                strokeWidth="1"
                rx="4"
              />
              <text
                x={19}
                y={cy}
                textAnchor="middle"
                fontSize="10"
                fontWeight="700"
                fill="#0E4F4A"
                fontFamily="Inter, sans-serif"
                transform={`rotate(-90, 19, ${cy})`}
                style={{ textTransform: "uppercase", letterSpacing: "0.06em" }}
              >
                {displayName}
              </text>
            </g>
          );
        })}

        {/* Method labels */}
        {methods.map((m, i) => (
          <text
            key={m.id}
            x={labelLeft - 12}
            y={labelTop + i * cellSize + (cellSize - cellGap) / 2 + 4}
            textAnchor="end"
            fontSize="13"
            fontWeight={query && matchesQuery(m.label) ? 700 : 500}
            fill={query && matchesQuery(m.label) ? "#0E4F4A" : "#1C1917"}
            fontFamily="Inter, sans-serif"
          >
            {m.label}
          </text>
        ))}

        {/* Cells */}
        {data.map((cell) => {
          const visible = isCellVisible(cell);
          const isEmpty = cell.gapScore < 0;
          const x = labelLeft + cell.topicIdx * cellSize;
          const y = labelTop + cell.methodIdx * cellSize;
          const isHover = hoveredCell?.methodId === cell.methodId && hoveredCell?.topicId === cell.topicId;
          const isSelected = selectedCell?.methodId === cell.methodId && selectedCell?.topicId === cell.topicId;
          const fill = isEmpty ? "url(#empty-cell-pattern)" : getCellColor(cell, mode);

          return (
            <g key={`${cell.methodId}-${cell.topicId}`}>
              <rect
                x={x}
                y={y}
                width={cellSize - cellGap}
                height={cellSize - cellGap}
                fill={fill}
                fillOpacity={visible ? 1 : 0.12}
                stroke={isSelected ? "#0E4F4A" : isHover ? "#1C1917" : "#FFFFFF"}
                strokeWidth={isSelected ? 3 : isHover ? 2.5 : 1.5}
                rx={5}
                style={{
                  cursor: visible && !isEmpty ? "pointer" : "default",
                  transition: "stroke 0.15s, stroke-width 0.15s, fill-opacity 0.2s",
                }}
                onMouseEnter={() => visible && !isEmpty && onCellHover(cell)}
                onMouseLeave={() => onCellHover(null)}
                onClick={() => visible && !isEmpty && onCellClick(cell)}
              />
              {cell.isGold && visible && (
                <text
                  x={x + (cellSize - cellGap) / 2}
                  y={y + (cellSize - cellGap) / 2 + 5}
                  textAnchor="middle"
                  fontSize="14"
                  fontWeight="700"
                  fill="#1C1917"
                  pointerEvents="none"
                  style={{ filter: "drop-shadow(0 1px 1px rgba(255,255,255,0.9))" }}
                >
                  &#9670;
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}

// ============================================================
// HOVER TOOLTIP
// ============================================================

function CellTooltip({ cell, methods, topics }: { cell: GapCell | null; methods: MethodDef[]; topics: TopicDef[] }) {
  if (!cell) return null;
  const method = methods[cell.methodIdx];
  const topic = topics[cell.topicIdx];
  if (!method || !topic) return null;
  const TrendIcon = cell.trend === "up" ? TrendingUp : cell.trend === "down" ? TrendingDown : Minus;
  const trendColor = cell.trend === "up" ? "#10B981" : cell.trend === "down" ? "#DC2626" : "#94A3B8";
  const trendLabel = cell.trend === "up" ? "Yukseliyor" : cell.trend === "down" ? "Dusuyor" : "Sabit";

  let interpretation: { label: string; color: string; bg: string };
  if (cell.gapScore >= 75) interpretation = { label: "Altin firsat", color: "#D97706", bg: "#FEF3C7" };
  else if (cell.gapScore >= 50) interpretation = { label: "Az calisilmis", color: "#0E4F4A", bg: "#F0FDFA" };
  else if (cell.gapScore >= 25) interpretation = { label: "Orta yogunluk", color: "#57534E", bg: "#F5F5F4" };
  else interpretation = { label: "Doygun", color: "#DC2626", bg: "#FEE2E2" };

  return (
    <div
      className="pointer-events-none absolute right-4 top-4 z-10 max-w-[280px] rounded-xl border border-stone-200 bg-white p-4 shadow-lg"
      style={{ animation: "fadeIn 0.15s ease-out" }}
    >
      <div className="mb-2 flex flex-wrap items-center gap-1.5">
        <span className="rounded px-1.5 py-0.5 text-[10px] font-semibold" style={{ background: interpretation.bg, color: interpretation.color }}>
          {cell.isGold && <span className="mr-1">&#9670;</span>}
          {interpretation.label}
        </span>
      </div>
      <h4 className="font-display mb-1 text-base font-semibold italic leading-snug text-stone-900">
        {method.label} <span className="text-stone-400">&times;</span> {topic.label}
      </h4>
      <div className="mb-3 text-[10px] text-stone-500">
        {method.family} · {topic.group}
      </div>

      <div className="grid grid-cols-2 gap-2 border-t border-stone-100 pt-2">
        <div>
          <div className="mb-0.5 text-[10px] text-stone-500">Bosluk skoru</div>
          <div className="font-display text-xl font-semibold italic" style={{ color: interpretation.color }}>
            {Math.round(cell.gapScore)}
            <span className="font-mono text-sm text-stone-400">/100</span>
          </div>
        </div>
        <div>
          <div className="mb-0.5 text-[10px] text-stone-500">Yayin sayisi</div>
          <div className="font-display text-xl font-semibold italic text-stone-800">{cell.paperCount}</div>
        </div>
      </div>

      <div className="mt-2 flex items-center gap-1.5 border-t border-stone-100 pt-2">
        <TrendIcon className="h-3 w-3" style={{ color: trendColor }} strokeWidth={2.5} />
        <span className="text-[11px] font-medium" style={{ color: trendColor }}>{trendLabel}</span>
        <span className="ml-1 text-[10px] text-stone-400">5 yillik trend</span>
      </div>
    </div>
  );
}

// ============================================================
// SELECTED CELL PANEL
// ============================================================

function SelectedCellPanel({ cell, onClose, methods, topics }: { cell: GapCell; onClose: () => void; methods: MethodDef[]; topics: TopicDef[] }) {
  const method = methods[cell.methodIdx] ?? { id: cell.methodId, label: cell.methodId, family: "" };
  const topic = topics[cell.topicIdx] ?? { id: cell.topicId, label: cell.topicId, group: "" };
  const TrendIcon = cell.trend === "up" ? TrendingUp : cell.trend === "down" ? TrendingDown : Minus;
  const trendColor = cell.trend === "up" ? "#10B981" : cell.trend === "down" ? "#DC2626" : "#94A3B8";

  let interpretation: { label: string; color: string; bg: string; advice: string };
  if (cell.gapScore >= 75)
    interpretation = {
      label: "Altin firsat",
      color: "#D97706",
      bg: "#FEF3C7",
      advice: "Bu kesisimde cok az calisma var ve trend yukseliyor. Tezinizin bu bolgede konumlanmasi guclu bir ozgunluk iddiasi verir.",
    };
  else if (cell.gapScore >= 50)
    interpretation = {
      label: "Az calisilmis",
      color: "#0E4F4A",
      bg: "#F0FDFA",
      advice: "Az sayida calisma mevcut. Bu kesisim potansiyel tasiyor — komsu hucreleri inceleyerek arastirma sorunuzu netlestirin.",
    };
  else if (cell.gapScore >= 25)
    interpretation = {
      label: "Orta yogunluk",
      color: "#57534E",
      bg: "#F5F5F4",
      advice: "Yeterli birikim var ama doygun degil. Kiyaslamali bir calisma ile katki sunulabilir.",
    };
  else
    interpretation = {
      label: "Doygun bolge",
      color: "#DC2626",
      bg: "#FEE2E2",
      advice: "Bu kesisim yogun calisilmis. Yeni katki sunmak icin yontemsel inovasyon veya farkli bir alt-baglam gerekir.",
    };

  return (
    <div
      className="mt-4 rounded-2xl border border-stone-200 bg-white p-5"
      style={{ animation: "slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1)", boxShadow: "0 4px 16px -4px rgba(0,0,0,0.08)" }}
    >
      <div className="mb-4 flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span className="rounded-md px-2 py-0.5 text-[10px] font-semibold" style={{ background: interpretation.bg, color: interpretation.color }}>
              {cell.isGold && <span className="mr-1">&#9670;</span>}
              {interpretation.label}
            </span>
            <span className="font-mono text-[10px] uppercase tracking-widest text-stone-400">Secili kesisim</span>
          </div>
          <h3 className="font-display mb-1 text-xl font-semibold italic leading-tight text-stone-900">
            {method.label} <span className="text-stone-400">&times;</span> {topic.label}
          </h3>
          <div className="text-sm text-stone-600">
            <span className="text-stone-400">Yontem ailesi:</span> {method.family} ·
            <span className="ml-1.5 text-stone-400">Konu grubu:</span> {topic.group}
          </div>
        </div>
        <button onClick={onClose} className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg text-stone-400 transition-colors hover:bg-stone-100 hover:text-stone-700">
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Three-stat row */}
      <div className="mb-4 grid grid-cols-3 gap-3">
        <div className="rounded-xl border border-stone-200 bg-stone-50 p-3">
          <div className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-stone-500">Bosluk skoru</div>
          <div className="flex items-baseline gap-1">
            <span className="font-display text-2xl font-semibold italic" style={{ color: interpretation.color }}>
              {Math.round(cell.gapScore)}
            </span>
            <span className="font-mono text-sm text-stone-400">/100</span>
          </div>
          <div className="mt-2 h-1 overflow-hidden rounded-full bg-stone-200">
            <div className="h-full rounded-full" style={{ width: `${cell.gapScore}%`, background: interpretation.color }} />
          </div>
        </div>
        <div className="rounded-xl border border-stone-200 bg-stone-50 p-3">
          <div className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-stone-500">Yayin sayisi</div>
          <div className="font-display text-2xl font-semibold italic text-stone-800">{cell.paperCount}</div>
          <div className="mt-1 text-[10px] text-stone-400">son 10 yil</div>
        </div>
        <div className="rounded-xl border border-stone-200 bg-stone-50 p-3">
          <div className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-stone-500">5-yil trend</div>
          <div className="flex items-center gap-1.5">
            <TrendIcon className="h-5 w-5" style={{ color: trendColor }} strokeWidth={2.5} />
            <span className="font-display text-lg font-semibold italic" style={{ color: trendColor }}>
              {cell.trend === "up" ? "Yukselen" : cell.trend === "down" ? "Dusen" : "Sabit"}
            </span>
          </div>
        </div>
      </div>

      {/* Adviser interpretation */}
      <div
        className="mb-4 flex items-start gap-2.5 rounded-xl p-3.5"
        style={{ background: interpretation.bg, borderLeft: `3px solid ${interpretation.color}` }}
      >
        <Sparkles className="mt-0.5 h-4 w-4 flex-shrink-0" style={{ color: interpretation.color }} />
        <div className="font-display text-sm italic leading-relaxed" style={{ color: interpretation.color }}>
          &ldquo;{interpretation.advice}&rdquo;
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <button
          className="rounded-lg px-3 py-1.5 text-xs font-medium text-white transition-all hover:scale-[1.02]"
          style={{ background: "linear-gradient(135deg, #0E4F4A 0%, #134E4A 100%)" }}
        >
          Bosluk profilini gor
        </button>
        <button className="rounded-lg border border-stone-200 px-3 py-1.5 text-xs font-medium text-stone-700 transition-colors hover:bg-stone-50">
          Komsu hucreleri incele
        </button>
        <button className="rounded-lg border border-stone-200 px-3 py-1.5 text-xs font-medium text-stone-700 transition-colors hover:bg-stone-50">
          Bu kesisimde paper'lari listele
        </button>
      </div>
    </div>
  );
}

// ============================================================
// MAIN — Gap Heatmap Card (D27)
// ============================================================

export function GapHeatmapCard() {
  const [mode, setMode] = useState<ColorMode>("gap");
  const [showOnlyGaps, setShowOnlyGaps] = useState(false);
  const [profileFilter, setProfileFilter] = useState(false);
  const [query, setQuery] = useState("");
  const [hoveredCell, setHoveredCell] = useState<GapCell | null>(null);
  const [selectedCell, setSelectedCell] = useState<GapCell | null>(null);
  const [controlsOpen, setControlsOpen] = useState(true);

  const { data: apiData, isLoading, isError } = useQuery({
    queryKey: ["gap-heatmap"],
    queryFn: fetchGapHeatmap,
    staleTime: 3600_000,
  });

  const methods: MethodDef[] = apiData?.methods ?? [];
  const topics: TopicDef[] = apiData?.topics ?? [];

  const data = useMemo(
    () => (apiData ? apiToGapCells(apiData.cells, methods, topics) : []),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [apiData],
  );

  const matchesQuery = (str: string) => {
    if (!query) return true;
    return str.toLowerCase().includes(query.toLowerCase());
  };

  const visibleData = useMemo(() => {
    return data.filter((cell) => {
      if (showOnlyGaps && cell.gapScore < 50) return false;
      const m = methods[cell.methodIdx];
      const t = topics[cell.topicIdx];
      if (!m || !t) return false;
      if (query && !matchesQuery(m.label) && !matchesQuery(t.label) && !matchesQuery(m.family) && !matchesQuery(t.group)) return false;
      if (profileFilter) {
        const userMethods = ["Network/Pairwise", "Reference-based", "Fuzzy"];
        const userTopics = ["Egitim", "Kalite", "Diger"];
        if (!userMethods.includes(m.family) || !userTopics.includes(t.group)) return false;
      }
      return true;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, showOnlyGaps, query, profileFilter]);

  const stats = useMemo(() => {
    const total = visibleData.length;
    const empty = visibleData.filter((c) => c.gapScore < 0).length;
    const gold = visibleData.filter((c) => c.gapScore >= 75 && c.gapScore < 100).length;
    const sparse = visibleData.filter((c) => c.gapScore >= 50 && c.gapScore < 75).length;
    const moderate = visibleData.filter((c) => c.gapScore >= 25 && c.gapScore < 50).length;
    const crowded = visibleData.filter((c) => c.gapScore >= 0 && c.gapScore < 25).length;
    return { total, empty, gold, sparse, moderate, crowded };
  }, [visibleData]);

  if (isLoading) {
    return (
      <div className="flex h-96 items-center justify-center rounded-2xl border border-stone-200 bg-white">
        <div className="space-y-2 text-center">
          <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-teal-700 border-t-transparent" />
          <p className="text-sm text-stone-500">Bosluk matrisi yukleniyor...</p>
        </div>
      </div>
    );
  }

  if (isError || !apiData) {
    return (
      <div className="flex h-48 items-center justify-center rounded-2xl border border-red-100 bg-red-50">
        <p className="text-sm text-red-600">Bosluk matrisi yuklenemedi. Lutfen sayfayi yenileyin.</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-4 md:p-6">
      <style>{`
        @keyframes fadeIn { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes slideUp { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
      `}</style>

      <DataVizCardFrame
        zone="gapatlas"
        customIcon={Map}
        title="Yontem x Konu bosluk matrisi"
        subtitle={`${methods.length} yontem x ${topics.length} konu kesiti · Tam matris: 504.000 hucre`}
        sourceBadge="504K hucre · Literatur Bosluk Matrisi"
        uniqueBadge
        prominent
        onFullscreen={() => {}}
        onExport={() => {}}
        onOpenNew={() => {}}
        legend={
          mode === "gap" ? (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs text-stone-600">Doygun</span>
              <div className="h-3 w-32 rounded" style={{ background: "linear-gradient(90deg, #134E4A, #5B7B7A, #B8B5A8, #E2BB6F, #F59E0B)" }} />
              <span className="text-xs text-stone-600">Bosluk</span>
              <span className="ml-3 inline-flex items-center gap-1 text-xs" style={{ color: "#B45309" }}>
                <span className="text-base font-bold leading-none">&#9670;</span>
                <span className="font-medium">Altin firsat</span>
              </span>
              <span className="ml-2 inline-flex items-center gap-1 text-xs text-stone-500">
                <span
                  className="h-3 w-3 rounded-sm border border-stone-200"
                  style={{ backgroundImage: "repeating-linear-gradient(45deg, #E7E5E4 0, #E7E5E4 1.5px, #FFFFFF 1.5px, #FFFFFF 6px)" }}
                />
                Veri yok
              </span>
            </div>
          ) : mode === "count" ? (
            <div className="flex items-center gap-2">
              <span className="text-xs text-stone-600">Cok yayin</span>
              <div className="h-3 w-32 rounded" style={{ background: "linear-gradient(90deg, #134E4A, #5B7B7A, #B8B5A8, #E2BB6F, #F59E0B)" }} />
              <span className="text-xs text-stone-600">Az yayin</span>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <span className="text-xs text-stone-600">Dusen trend</span>
              <div className="h-3 w-32 rounded" style={{ background: "linear-gradient(90deg, #134E4A, #5B7B7A, #B8B5A8, #E2BB6F, #F59E0B)" }} />
              <span className="text-xs text-stone-600">Yukselen</span>
            </div>
          )
        }
        controls={
          <div className="flex items-center gap-3 text-[11px]">
            <span className="text-stone-500">
              <span className="font-mono font-semibold text-emerald-700">{stats.gold}</span> altin
              <span className="mx-1 text-stone-300">·</span>
              <span className="font-mono font-semibold" style={{ color: "#0E4F4A" }}>{stats.sparse}</span> az calisilmis
              <span className="mx-1 text-stone-300">·</span>
              <span className="font-mono font-semibold text-red-600">{stats.crowded}</span> doygun
            </span>
          </div>
        }
      >
        {/* Controls panel */}
        <div className="absolute left-4 top-4 z-10 rounded-xl border border-stone-200 bg-white/95 shadow-sm backdrop-blur-sm" style={{ minWidth: "220px" }}>
          <button
            onClick={() => setControlsOpen(!controlsOpen)}
            className="flex w-full items-center justify-between px-3 py-2 text-[11px] font-semibold text-stone-700"
          >
            <span className="flex items-center gap-1.5">
              <Filter className="h-3 w-3 text-stone-400" />
              Kontroller
            </span>
            {controlsOpen ? <ChevronUp className="h-3 w-3 text-stone-400" /> : <ChevronDown className="h-3 w-3 text-stone-400" />}
          </button>
          {controlsOpen && <div className="space-y-3 border-t border-stone-100 p-3">
          {/* Mode toggle */}
          <div>
            <label className="mb-1.5 block text-[11px] font-semibold text-stone-700">Renklendirme</label>
            <div className="flex gap-1">
              {([
                { id: "gap" as const, label: "Bosluk", icon: Target },
                { id: "count" as const, label: "Sayi", icon: Layers },
                { id: "trend" as const, label: "Trend", icon: TrendingUp },
              ]).map((opt) => {
                const OIcon = opt.icon;
                return (
                  <button
                    key={opt.id}
                    onClick={() => setMode(opt.id)}
                    className="flex flex-1 items-center justify-center gap-1 rounded-md border py-1.5 text-[10px] font-medium transition-all"
                    style={{
                      background: mode === opt.id ? "#F0FDFA" : "white",
                      color: mode === opt.id ? "#0E4F4A" : "#57534E",
                      borderColor: mode === opt.id ? "#A7F3D0" : "#E7E5E4",
                    }}
                  >
                    <OIcon className="h-2.5 w-2.5" />
                    {opt.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Search */}
          <div>
            <label className="mb-1.5 block text-[11px] font-semibold text-stone-700">Ara</label>
            <div className="relative">
              <Search className="pointer-events-none absolute left-2 top-1/2 h-3 w-3 -translate-y-1/2 text-stone-400" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="AHP, Akreditasyon..."
                className="w-full rounded-md border border-stone-200 bg-white py-1.5 pl-7 pr-2 text-[11px] text-stone-800 placeholder-stone-400 focus:border-teal-400 focus:outline-none"
              />
            </div>
          </div>

          {/* Toggles */}
          <div className="space-y-1.5">
            <label className="flex cursor-pointer items-center gap-2 text-[11px] text-stone-700">
              <input
                type="checkbox"
                checked={showOnlyGaps}
                onChange={(e) => setShowOnlyGaps(e.target.checked)}
                className="h-3.5 w-3.5 rounded accent-teal-700"
              />
              Sadece bosluklari goster
            </label>
            <label className="flex cursor-pointer items-center gap-2 text-[11px] text-stone-700">
              <input
                type="checkbox"
                checked={profileFilter}
                onChange={(e) => setProfileFilter(e.target.checked)}
                className="h-3.5 w-3.5 rounded accent-teal-700"
              />
              Profilime yakin
            </label>
          </div>

          {/* Stats */}
          <div className="border-t border-stone-100 pt-2">
            <div className="mb-1 text-[10px] text-stone-500">
              <span className="font-mono font-semibold text-stone-700">{stats.total}</span> hucre gorunuyor
            </div>
            <div className="flex items-center gap-1.5 text-[10px]">
              <span className="inline-flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full" style={{ background: "#F59E0B" }} />
                <span className="text-stone-600">Bosluk</span>
              </span>
              <span className="text-stone-300">·</span>
              <span className="inline-flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full" style={{ background: "#134E4A" }} />
                <span className="text-stone-600">Doygun</span>
              </span>
            </div>
          </div>
        </div>}
        </div>

        {/* Hover tooltip */}
        <CellTooltip cell={hoveredCell} methods={methods} topics={topics} />

        {/* Heatmap */}
        <div className="px-4 py-4">
          <HeatmapGrid
            data={data}
            methods={methods}
            topics={topics}
            mode={mode}
            showOnlyGaps={showOnlyGaps}
            query={query}
            profileFilter={profileFilter}
            onCellHover={setHoveredCell}
            onCellClick={(c) =>
              setSelectedCell(
                selectedCell?.methodId === c.methodId && selectedCell?.topicId === c.topicId ? null : c,
              )
            }
            hoveredCell={hoveredCell}
            selectedCell={selectedCell}
          />
        </div>

        {/* Adviser banner */}
        <div
          className="absolute bottom-4 right-4 z-10 flex max-w-[320px] items-start gap-2 rounded-lg bg-white/95 px-3 py-2.5 shadow-sm backdrop-blur-sm"
          style={{ borderLeft: "3px solid #0E4F4A" }}
        >
          <Sparkles className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" style={{ color: "#0E4F4A" }} />
          <div className="font-display text-[11px] italic leading-relaxed text-stone-700">
            &ldquo;{stats.gold} altin firsat isaretledim — &#9670; sembolu olan hucrelere bak.&rdquo;
          </div>
        </div>
      </DataVizCardFrame>

      {/* Selected cell panel */}
      {selectedCell && <SelectedCellPanel cell={selectedCell} onClose={() => setSelectedCell(null)} methods={methods} topics={topics} />}

      {/* Differentiator note */}
      <div
        className="relative overflow-hidden rounded-2xl p-5"
        style={{
          background: "linear-gradient(135deg, #F0FDFA 0%, #FFFFFF 100%)",
          border: "1px solid #A7F3D0",
          borderLeft: "3px solid #0E4F4A",
        }}
      >
        <div className="absolute right-0 top-0 h-32 w-32 rounded-full opacity-10 blur-3xl" style={{ background: "linear-gradient(135deg, #0E4F4A, #134E4A)" }} />
        <div className="relative">
          <div className="mb-2 flex items-center gap-2">
            <Zap className="h-4 w-4" style={{ color: "#0E4F4A" }} />
            <div className="text-xs font-semibold uppercase tracking-widest" style={{ color: "#0E4F4A" }}>
              {BRAND}&#39;in imza ozelligi
            </div>
          </div>
          <h3 className="font-display mb-3 text-lg font-semibold italic text-stone-900">
            Bu gorsellestirmeyi <span className="not-italic">hicbir rakip</span> sunmuyor
          </h3>
          <ul className="space-y-1.5 text-sm text-stone-700">
            <li className="flex items-start gap-2">
              <span className="mt-1 text-teal-700">·</span>
              <span>
                <span className="font-medium">SciSpace, Consensus, Elicit, Litmaps:</span> hicbiri yontem &times; konu bosluk matrisi sunmuyor. Hepsi sadece &ldquo;ilgili paper'lari&rdquo; gosteriyor.
              </span>
            </li>
            <li className="flex items-start gap-2">
              <span className="mt-1 text-teal-700">·</span>
              <span>
                <span className="font-medium">504.000 hucre:</span> tam matris — on-hesapli bosluk skoru, paper sayimi ve 5-yillik trend yonu her hucrede.
              </span>
            </li>
            <li className="flex items-start gap-2">
              <span className="mt-1 text-teal-700">·</span>
              <span>
                <span className="font-medium">Hazine haritasi gibi:</span> yesil/sari = altin firsat, mor = doygun bolge. Tezinizi nereye yerlestireceginize tek bakista karar verin.
              </span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
