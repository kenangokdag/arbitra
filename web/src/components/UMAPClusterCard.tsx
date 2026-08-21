"use client";

import { useState, useRef, useEffect, useMemo, useCallback } from "react";
import {
  X,
  Layers,
  Sparkles,
  Map,
  Crosshair,
  Quote,
  Calendar,
  TrendingUp,
  MapPin,
  Target,
} from "lucide-react";
import * as d3 from "d3";
import { DataVizCardFrame } from "./DataVizCardFrame";

// ============================================================
// Types
// ============================================================
interface Theme {
  id: number;
  name: string;
  short: string;
  color: string;
  center: [number, number];
}

interface UMAPPoint {
  id: string;
  x: number;
  y: number;
  theme: number;
  year: number;
  citations: number;
}

interface UserTopic {
  x: number;
  y: number;
  label: string;
  description: string;
}

interface UMAPData {
  points: UMAPPoint[];
  userTopic: UserTopic;
  themes: Theme[];
}

type ColorBy = "theme" | "year" | "citation";

// ============================================================
// Mock data
// ============================================================
const THEMES: Theme[] = [
  { id: 0, name: "MCDM Yöntemleri", short: "MCDM Yöntemleri", color: "#4F46E5", center: [-3.5, 2.5] },
  { id: 1, name: "Akreditasyon", short: "Akreditasyon", color: "#7C3AED", center: [2.5, 3.0] },
  { id: 2, name: "Yükseköğretim", short: "Yükseköğretim", color: "#D97706", center: [4.5, -1.0] },
  { id: 3, name: "Kalite Göstergeleri", short: "Kalite", color: "#0E4F4A", center: [-2.5, -3.5] },
  { id: 4, name: "Paydaş Analizi", short: "Paydaş Analizi", color: "#0EA5E9", center: [2.5, -3.5] },
  { id: 5, name: "Politika & Yönetişim", short: "Politika", color: "#DC2626", center: [-4.5, -0.5] },
];

function generateUMAPData(): UMAPData {
  let seed = 42;
  const rand = () => {
    seed = (seed * 9301 + 49297) % 233280;
    return seed / 233280;
  };
  const gauss = () => {
    const u = 1 - rand();
    const v = rand();
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
  };

  const points: UMAPPoint[] = [];
  let id = 0;

  THEMES.forEach((theme, ti) => {
    const count = 35 + Math.floor(rand() * 15);
    for (let i = 0; i < count; i++) {
      const spread = 0.85;
      const x = theme.center[0] + gauss() * spread;
      const y = theme.center[1] + gauss() * spread;
      const yearBase = ti < 2 ? 2022 : ti < 4 ? 2021 : 2020;
      const year = yearBase + Math.floor(rand() * 5);
      const citations = Math.floor(Math.exp(rand() * 5)) + 1;
      points.push({
        id: `p${id++}`,
        x,
        y,
        theme: ti,
        year: Math.min(year, 2025),
        citations: Math.min(citations, 380),
      });
    }
  });

  const userTopic: UserTopic = {
    x: -0.5,
    y: 2.8,
    label: "Senin konun",
    description: "MCDM × Akreditasyon kesişimi",
  };

  return { points, userTopic, themes: THEMES };
}

// ============================================================
// UMAP Scatter (D3)
// ============================================================
interface UMAPScatterProps {
  data: UMAPData;
  colorBy: ColorBy;
  opacity: number;
  focusUser: number;
  hoveredId: string | null;
  setHoveredId: (id: string | null) => void;
  selectedId: string | null;
  setSelectedId: (id: string | null) => void;
}

function UMAPScatter({
  data,
  colorBy,
  opacity,
  focusUser,
  hoveredId,
  setHoveredId,
  selectedId,
  setSelectedId,
}: UMAPScatterProps) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const gRef = useRef<SVGGElement | null>(null);
  const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null);
  const selectedIdRef = useRef(selectedId);
  const opacityRef = useRef(opacity);
  const [width, setWidth] = useState(800);
  const height = 620;

  // Keep refs in sync so D3 callbacks read latest values without re-running effect
  useEffect(() => {
    selectedIdRef.current = selectedId;
  }, [selectedId]);
  useEffect(() => {
    opacityRef.current = opacity;
  }, [opacity]);

  useEffect(() => {
    if (!svgRef.current) return;
    const el = svgRef.current;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) setWidth(entry.contentRect.width);
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const { xScale, yScale, sizeScale } = useMemo(() => {
    const allX = data.points.map((p) => p.x).concat([data.userTopic.x]);
    const allY = data.points.map((p) => p.y).concat([data.userTopic.y]);
    const padding = 60;
    const xExtent = d3.extent(allX) as [number, number];
    const yExtent = d3.extent(allY) as [number, number];
    const xPad = (xExtent[1] - xExtent[0]) * 0.08;
    const yPad = (yExtent[1] - yExtent[0]) * 0.08;
    const xScale = d3
      .scaleLinear()
      .domain([xExtent[0] - xPad, xExtent[1] + xPad])
      .range([padding, width - padding]);
    const yScale = d3
      .scaleLinear()
      .domain([yExtent[0] - yPad, yExtent[1] + yPad])
      .range([height - padding, padding]);
    const sizeScale = d3.scaleSqrt().domain([1, 380]).range([4, 12]);
    return { xScale, yScale, sizeScale };
  }, [width, height, data]);

  const yearColorScale = useMemo(
    () => d3.scaleSequential(d3.interpolateViridis).domain([2025, 2018]),
    [],
  );

  const citationColorScale = useMemo(
    () => d3.scaleSequential(d3.interpolateInferno).domain([0, 5]),
    [],
  );

  const getPointColor = useCallback(
    (p: UMAPPoint): string => {
      if (colorBy === "theme") return data.themes[p.theme]?.color ?? "#A8A29E";
      if (colorBy === "year") return yearColorScale(p.year);
      if (colorBy === "citation")
        return citationColorScale(Math.log(p.citations + 1));
      return "#A8A29E";
    },
    [colorBy, data.themes, yearColorScale, citationColorScale],
  );

  useEffect(() => {
    if (!svgRef.current || !gRef.current) return;

    const svg = d3.select(svgRef.current);
    const g = d3.select(gRef.current);
    g.selectAll("*").remove();

    // Hulls
    const hullG = g.append("g").attr("class", "hulls").style("pointer-events", "none");
    data.themes.forEach((theme) => {
      const themePoints = data.points.filter((p) => p.theme === theme.id);
      if (themePoints.length < 3) return;
      const projected: [number, number][] = themePoints.map((p) => [xScale(p.x), yScale(p.y)]);
      const hull = d3.polygonHull(projected);
      if (hull) {
        const cx = d3.mean(hull, (p) => p[0]) ?? 0;
        const cy = d3.mean(hull, (p) => p[1]) ?? 0;
        const expanded: [number, number][] = hull.map(([x, y]) => {
          const dx = x - cx;
          const dy = y - cy;
          const len = Math.sqrt(dx * dx + dy * dy) || 1;
          const pad = 30;
          return [x + (dx / len) * pad, y + (dy / len) * pad];
        });
        const lineGen = d3
          .line<[number, number]>()
          .x((d) => d[0])
          .y((d) => d[1])
          .curve(d3.curveCatmullRomClosed.alpha(0.5));
        hullG
          .append("path")
          .attr("d", lineGen(expanded))
          .attr("fill", theme.color)
          .attr("fill-opacity", 0.07)
          .attr("stroke", theme.color)
          .attr("stroke-opacity", 0.22)
          .attr("stroke-width", 1)
          .attr("stroke-dasharray", "4,4");
      }
    });

    // Cluster labels
    const labelG = g.append("g").attr("class", "labels").style("pointer-events", "none");
    data.themes.forEach((theme) => {
      const cx = xScale(theme.center[0]);
      const cy = yScale(theme.center[1]) - 60;
      const labelGroup = labelG.append("g").attr("transform", `translate(${cx},${cy})`);

      const tempText = labelGroup
        .append("text")
        .text(theme.short)
        .attr("font-family", "var(--font-sans)")
        .attr("font-size", "13px")
        .attr("font-weight", 700)
        .attr("opacity", 0);
      const tempNode = tempText.node();
      if (!tempNode) return;
      const bbox = tempNode.getBBox();
      tempText.remove();

      labelGroup
        .append("rect")
        .attr("x", -bbox.width / 2 - 10)
        .attr("y", -bbox.height / 2 - 4)
        .attr("width", bbox.width + 20)
        .attr("height", bbox.height + 8)
        .attr("rx", 14)
        .attr("fill", "#FFFFFF")
        .attr("stroke", theme.color)
        .attr("stroke-width", 1.5)
        .attr("filter", "drop-shadow(0 2px 4px rgba(0,0,0,0.08))");

      labelGroup
        .append("circle")
        .attr("cx", -bbox.width / 2 - 1)
        .attr("cy", 0)
        .attr("r", 3.5)
        .attr("fill", theme.color);

      labelGroup
        .append("text")
        .text(theme.short)
        .attr("text-anchor", "middle")
        .attr("dy", "0.35em")
        .attr("dx", 6)
        .attr("font-family", "var(--font-sans)")
        .attr("font-size", "13px")
        .attr("font-weight", 700)
        .attr("fill", theme.color);
    });

    // Points
    g.append("g")
      .attr("class", "points")
      .selectAll<SVGCircleElement, UMAPPoint>("circle")
      .data(data.points)
      .join("circle")
      .attr("cx", (d) => xScale(d.x))
      .attr("cy", (d) => yScale(d.y))
      .attr("r", (d) => sizeScale(d.citations))
      .attr("fill", (d) => getPointColor(d))
      .attr("fill-opacity", opacityRef.current)
      .attr("stroke", "#FFFFFF")
      .attr("stroke-width", 1.5)
      .style("cursor", "pointer")
      .on("mouseenter", (_event, d) => setHoveredId(d.id))
      .on("mouseleave", () => setHoveredId(null))
      .on("click", (_event, d) =>
        setSelectedId(d.id === selectedIdRef.current ? null : d.id),
      );

    // User topic crosshair
    const userG = g
      .append("g")
      .attr("class", "user-marker")
      .attr(
        "transform",
        `translate(${xScale(data.userTopic.x)},${yScale(data.userTopic.y)})`,
      )
      .style("pointer-events", "none");

    [20, 14].forEach((r, i) => {
      const ring = userG
        .append("circle")
        .attr("r", r)
        .attr("fill", "none")
        .attr("stroke", "#D97706")
        .attr("stroke-width", 1.5)
        .attr("opacity", 0.35);
      ring
        .append("animate")
        .attr("attributeName", "r")
        .attr("from", r)
        .attr("to", r + 6)
        .attr("dur", "2.4s")
        .attr("begin", `${i * 0.6}s`)
        .attr("repeatCount", "indefinite");
    });

    userG.append("line").attr("x1", -14).attr("y1", 0).attr("x2", -5).attr("y2", 0).attr("stroke", "#D97706").attr("stroke-width", 2);
    userG.append("line").attr("x1", 5).attr("y1", 0).attr("x2", 14).attr("y2", 0).attr("stroke", "#D97706").attr("stroke-width", 2);
    userG.append("line").attr("x1", 0).attr("y1", -14).attr("x2", 0).attr("y2", -5).attr("stroke", "#D97706").attr("stroke-width", 2);
    userG.append("line").attr("x1", 0).attr("y1", 5).attr("x2", 0).attr("y2", 14).attr("stroke", "#D97706").attr("stroke-width", 2);
    userG.append("circle").attr("r", 4).attr("fill", "#D97706").attr("stroke", "#FFFFFF").attr("stroke-width", 2);

    const userLabel = userG.append("g").attr("transform", "translate(20, -8)");
    userLabel
      .append("rect")
      .attr("x", 0)
      .attr("y", -10)
      .attr("width", 100)
      .attr("height", 32)
      .attr("rx", 6)
      .attr("fill", "#D97706")
      .attr("filter", "drop-shadow(0 2px 6px rgba(217, 119, 6, 0.3))");
    userLabel
      .append("text")
      .text("Senin konun")
      .attr("x", 50)
      .attr("y", 2)
      .attr("text-anchor", "middle")
      .attr("font-family", "var(--font-crimson, Lora, serif)")
      .attr("font-style", "italic")
      .attr("font-weight", 600)
      .attr("font-size", "11px")
      .attr("fill", "#FFFFFF");
    userLabel
      .append("text")
      .text("Tam burada")
      .attr("x", 50)
      .attr("y", 16)
      .attr("text-anchor", "middle")
      .attr("font-family", "var(--font-sans)")
      .attr("font-size", "9px")
      .attr("fill", "#FFFFFF")
      .attr("fill-opacity", 0.85);

    // Zoom
    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.5, 8])
      .on("zoom", (event) => {
        g.attr("transform", event.transform.toString());
        g.selectAll<SVGCircleElement, UMAPPoint>(".points circle").attr(
          "r",
          (d) => sizeScale(d.citations) / Math.sqrt(event.transform.k),
        );
      });
    svg.call(zoom);
    zoomRef.current = zoom;

    return () => {
      svg.on(".zoom", null);
      zoomRef.current = null;
    };
  }, [width, height, data, xScale, yScale, sizeScale, getPointColor, setHoveredId, setSelectedId]);

  // Focus user marker — separate effect, only re-runs when focusUser tick changes
  useEffect(() => {
    if (focusUser === 0 || !svgRef.current || !zoomRef.current) return;
    const svg = d3.select(svgRef.current);
    const ux = xScale(data.userTopic.x);
    const uy = yScale(data.userTopic.y);
    const targetK = 2.8;
    const tx = width / 2 - ux * targetK;
    const ty = height / 2 - uy * targetK;
    svg
      .transition()
      .duration(800)
      .ease(d3.easeCubicInOut)
      .call(
        zoomRef.current.transform,
        d3.zoomIdentity.translate(tx, ty).scale(targetK),
      );
  }, [focusUser, width, height, data.userTopic, xScale, yScale]);

  // Highlight hovered/selected
  useEffect(() => {
    if (!gRef.current) return;
    const g = d3.select(gRef.current);
    const focusId = hoveredId || selectedId;

    g.selectAll<SVGCircleElement, UMAPPoint>(".points circle").each(function (d) {
      const isFocus = d.id === focusId;
      d3.select(this)
        .attr("stroke", isFocus ? "#1C1917" : "#FFFFFF")
        .attr("stroke-width", isFocus ? 2.5 : 1.5)
        .attr("fill-opacity", focusId ? (isFocus ? 1 : opacity * 0.35) : opacity);
    });
  }, [hoveredId, selectedId, opacity]);

  return (
    <svg
      ref={svgRef}
      width="100%"
      height={height}
      style={{ display: "block", background: "#FAFAF9" }}
    >
      <defs>
        <pattern id="umap-grid" width="40" height="40" patternUnits="userSpaceOnUse">
          <path
            d="M 40 0 L 0 0 0 40"
            fill="none"
            stroke="#E7E5E4"
            strokeWidth="0.5"
            opacity="0.5"
          />
        </pattern>
      </defs>
      <rect width="100%" height={height} fill="url(#umap-grid)" />
      <g ref={gRef} />
    </svg>
  );
}

// ============================================================
// Hover tooltip
// ============================================================
function PointTooltip({
  point,
  data,
}: {
  point: UMAPPoint | null;
  data: UMAPData;
}) {
  if (!point) return null;
  const theme = data.themes[point.theme];
  if (!theme) return null;

  return (
    <div className="absolute top-4 right-4 bg-white rounded-xl shadow-lg border border-stone-200 p-4 max-w-[260px] z-10 pointer-events-none animate-[fadeIn_0.15s_ease-out]">
      <div className="flex items-center gap-1.5 mb-2 flex-wrap">
        <span
          className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold"
          style={{ background: `${theme.color}15`, color: theme.color }}
        >
          <span
            className="w-1.5 h-1.5 rounded-full"
            style={{ background: theme.color }}
          />
          {theme.name}
        </span>
      </div>
      <div className="text-[10px] font-mono-pmid text-stone-400 mb-1">
        PMID: {point.id}
      </div>
      <h4 className="font-crimson italic text-sm font-semibold text-stone-900 leading-snug mb-2">
        Paper {point.id} — örnek başlık
      </h4>
      <div className="grid grid-cols-2 gap-2 pt-2 border-t border-stone-100 text-xs">
        <div className="flex items-center gap-1.5 text-stone-600">
          <Calendar className="w-3 h-3 text-stone-400" />
          <span className="font-mono-pmid font-semibold text-stone-800">
            {point.year}
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-stone-600">
          <Quote className="w-3 h-3 text-stone-400" />
          <span className="font-mono-pmid font-semibold text-stone-800">
            {point.citations}
          </span>
          <span className="text-stone-500">atıf</span>
        </div>
      </div>
      <div className="mt-2 pt-2 border-t border-stone-100 text-[10px] font-mono-pmid text-stone-400">
        UMAP: ({point.x.toFixed(2)}, {point.y.toFixed(2)})
      </div>
    </div>
  );
}

// ============================================================
// Selected point panel
// ============================================================
function SelectedPointPanel({
  pointId,
  data,
  onClose,
}: {
  pointId: string | null;
  data: UMAPData;
  onClose: () => void;
}) {
  if (!pointId) return null;
  const point = data.points.find((p) => p.id === pointId);
  if (!point) return null;
  const theme = data.themes[point.theme];
  if (!theme) return null;

  const dx = point.x - data.userTopic.x;
  const dy = point.y - data.userTopic.y;
  const distance = Math.sqrt(dx * dx + dy * dy);
  const proximityLabel =
    distance < 0.8 ? "Çok yakın" : distance < 2.0 ? "Komşu bölge" : "Uzak küme";
  const proximityColor =
    distance < 0.8 ? "#10B981" : distance < 2.0 ? "#D97706" : "#94A3B8";

  return (
    <div
      className="bg-white rounded-2xl border border-stone-200 p-5 mt-4 animate-[slideUp_0.3s_cubic-bezier(0.16,1,0.3,1)]"
      style={{ boxShadow: "0 4px 16px -4px rgba(0,0,0,0.08)" }}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <span
              className="px-2 py-0.5 rounded-md text-[10px] font-semibold"
              style={{ background: `${theme.color}15`, color: theme.color }}
            >
              {theme.name}
            </span>
            <span
              className="px-2 py-0.5 rounded-md text-[10px] font-semibold"
              style={{
                background: `${proximityColor}15`,
                color: proximityColor,
              }}
            >
              <MapPin
                className="w-2.5 h-2.5 inline mr-0.5"
                strokeWidth={2.5}
              />
              {proximityLabel}
            </span>
            <span className="text-[10px] font-mono-pmid text-stone-400 uppercase tracking-widest">
              Seçili
            </span>
          </div>
          <h3 className="font-crimson italic text-lg font-semibold text-stone-900 leading-tight mb-1.5">
            Paper {point.id} — örnek başlık
          </h3>
          <div className="text-sm text-stone-600 mb-4">
            <span className="font-mono-pmid">{point.year}</span> ·
            <span className="ml-1.5">{point.citations} atıf</span> ·
            <span className="ml-1.5">
              UMAP konumu (
              <span className="font-mono-pmid">{point.x.toFixed(2)}</span>,{" "}
              <span className="font-mono-pmid">{point.y.toFixed(2)}</span>)
            </span>
          </div>

          <div className="bg-stone-50 rounded-xl p-3 border border-stone-200 mb-4">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[11px] text-stone-500 flex items-center gap-1.5">
                <Crosshair className="w-3 h-3 text-amber-600" />
                Senin konuna uzaklık
              </span>
              <span className="text-[11px] font-mono-pmid font-semibold text-stone-700">
                {distance.toFixed(2)}
              </span>
            </div>
            <div className="h-1.5 bg-stone-200 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full"
                style={{
                  width: `${Math.min(100, (distance / 5) * 100)}%`,
                  background: `linear-gradient(90deg, ${proximityColor}, ${proximityColor}dd)`,
                }}
              />
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <button
              className="px-3 py-1.5 rounded-lg text-xs font-medium text-white transition-all hover:scale-[1.02]"
              style={{
                background: "linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)",
              }}
            >
              Detay sayfasına git
            </button>
            <button className="px-3 py-1.5 rounded-lg text-xs font-medium text-stone-700 border border-stone-200 hover:bg-stone-50 transition-colors">
              Listeme ekle
            </button>
            <button className="px-3 py-1.5 rounded-lg text-xs font-medium text-stone-700 border border-stone-200 hover:bg-stone-50 transition-colors">
              Bu temayı incele
            </button>
          </div>
        </div>
        <button
          onClick={onClose}
          className="w-8 h-8 rounded-lg flex items-center justify-center text-stone-400 hover:bg-stone-100 hover:text-stone-700 transition-colors flex-shrink-0"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

// ============================================================
// Main export
// ============================================================
export default function UMAPClusterCard() {
  const [colorBy, setColorBy] = useState<ColorBy>("theme");
  const [opacity, setOpacity] = useState(0.85);
  const [focusTrigger, setFocusTrigger] = useState(0);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const data = useMemo(() => generateUMAPData(), []);
  const hoveredPoint = hoveredId
    ? data.points.find((p) => p.id === hoveredId) ?? null
    : null;

  const colorOptions: { id: ColorBy; label: string; icon: typeof Layers }[] = [
    { id: "theme", label: "Tema", icon: Layers },
    { id: "year", label: "Yıl", icon: Calendar },
    { id: "citation", label: "Atıf", icon: TrendingUp },
  ];

  return (
    <>
      <DataVizCardFrame
        zone="discovery"
        customIcon={Map}
        title="UMAP tematik haritası"
        subtitle="BGE-M3 1024-d embedding → 2D projeksiyon · Anlamsal yakınlık = harita yakınlığı"
        sourceBadge="BGE-M3 24.87M paper · UMAP 2D"
        onFullscreen={() => {}}
        onExport={() => {}}
        onOpenNew={() => {}}
        legend={
          colorBy === "theme" ? (
            <div className="flex items-center gap-2 flex-wrap">
              {data.themes.map((t) => (
                <div key={t.id} className="flex items-center gap-1.5">
                  <span
                    className="w-2.5 h-2.5 rounded-full"
                    style={{ background: t.color }}
                  />
                  <span className="text-xs text-stone-600">{t.name}</span>
                </div>
              ))}
            </div>
          ) : colorBy === "year" ? (
            <div className="flex items-center gap-2">
              <span className="text-xs text-stone-600">2018</span>
              <div
                className="w-32 h-2 rounded-full"
                style={{
                  background:
                    "linear-gradient(90deg, #440154, #3b528b, #21908d, #5dc863, #fde725)",
                }}
              />
              <span className="text-xs text-stone-600">2025</span>
              <span className="text-[11px] text-stone-400 italic ml-2">
                Yeni → parlak
              </span>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <span className="text-xs text-stone-600">Az atıf</span>
              <div
                className="w-32 h-2 rounded-full"
                style={{
                  background:
                    "linear-gradient(90deg, #000004, #420a68, #932667, #dd513a, #fca50a, #fcffa4)",
                }}
              />
              <span className="text-xs text-stone-600">Çok atıf</span>
              <span className="text-[11px] text-stone-400 italic ml-2">
                Log ölçek
              </span>
            </div>
          )
        }
        controls={
          <div className="flex items-center gap-3">
            <span className="text-[11px] text-stone-500">
              <span className="font-mono-pmid font-semibold text-stone-700">
                {data.points.length}
              </span>{" "}
              görünen nokta ·
              <span className="text-stone-400 ml-1">
                24.87M&#39;den temsili örnek
              </span>
            </span>
            <button className="text-[11px] text-indigo-600 font-medium hover:underline">
              Tüm veriyi yükle
            </button>
          </div>
        }
      >
        {/* Top-left controls panel */}
        <div
          className="absolute top-4 left-4 z-10 bg-white/95 backdrop-blur-sm rounded-xl border border-stone-200 p-3 space-y-3 shadow-sm"
          style={{ minWidth: "240px" }}
        >
          <div>
            <label className="text-[11px] font-semibold text-stone-700 mb-1.5 block">
              Renklendir
            </label>
            <div className="flex gap-1">
              {colorOptions.map((opt) => {
                const OIcon = opt.icon;
                return (
                  <button
                    key={opt.id}
                    onClick={() => setColorBy(opt.id)}
                    className="flex-1 py-1.5 rounded-md text-[10px] font-medium border transition-all flex items-center justify-center gap-1"
                    style={{
                      background: colorBy === opt.id ? "#EEF2FF" : "white",
                      color: colorBy === opt.id ? "#4F46E5" : "#57534E",
                      borderColor: colorBy === opt.id ? "#C7D2FE" : "#E7E5E4",
                    }}
                  >
                    <OIcon className="w-2.5 h-2.5" />
                    {opt.label}
                  </button>
                );
              })}
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-[11px] font-semibold text-stone-700">
                Saydamlık
              </label>
              <span className="text-[11px] font-mono-pmid font-semibold text-indigo-600">
                %{Math.round(opacity * 100)}
              </span>
            </div>
            <input
              type="range"
              min="0.2"
              max="1.0"
              step="0.05"
              value={opacity}
              onChange={(e) => setOpacity(parseFloat(e.target.value))}
              className="w-full h-1.5 bg-stone-200 rounded-full appearance-none cursor-pointer"
              style={{
                background: `linear-gradient(to right, #4F46E5 0%, #7C3AED ${
                  ((opacity - 0.2) / 0.8) * 100
                }%, #E7E5E4 ${((opacity - 0.2) / 0.8) * 100}%, #E7E5E4 100%)`,
              }}
            />
          </div>

          <button
            onClick={() => setFocusTrigger((t) => t + 1)}
            className="w-full flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold text-white transition-all hover:scale-[1.02]"
            style={{
              background: "linear-gradient(135deg, #D97706 0%, #B45309 100%)",
              boxShadow: "0 2px 6px -1px rgba(217, 119, 6, 0.3)",
            }}
          >
            <Target className="w-3 h-3" strokeWidth={2.5} />
            Konumumu yakınlaştır
          </button>
        </div>

        <PointTooltip point={hoveredPoint} data={data} />

        <UMAPScatter
          data={data}
          colorBy={colorBy}
          opacity={opacity}
          focusUser={focusTrigger}
          hoveredId={hoveredId}
          setHoveredId={setHoveredId}
          selectedId={selectedId}
          setSelectedId={setSelectedId}
        />

        <div
          className="absolute bottom-3 left-4 z-10 max-w-[480px] flex items-start gap-2 bg-white/95 backdrop-blur-sm rounded-lg px-3 py-2.5 shadow-sm"
          style={{ borderLeft: "3px solid #D97706" }}
        >
          <Sparkles className="w-3.5 h-3.5 text-amber-600 flex-shrink-0 mt-0.5" />
          <div className="text-[11px] text-stone-700 leading-relaxed font-crimson italic">
            &ldquo;Konunun temadaki yerini UMAP üstünde işaretledim — markeri
            görüyor musun? MCDM ve Akreditasyon kümeleri arasında oturuyor,
            kavşak bir konu.&rdquo;
          </div>
        </div>

        <div className="absolute bottom-3 right-4 z-10 text-[11px] text-stone-400 italic bg-white/80 backdrop-blur-sm px-2 py-1 rounded-md">
          Tekerlek = zoom · Sürükle = pan
        </div>
      </DataVizCardFrame>

      {selectedId && (
        <SelectedPointPanel
          pointId={selectedId}
          data={data}
          onClose={() => setSelectedId(null)}
        />
      )}
    </>
  );
}
