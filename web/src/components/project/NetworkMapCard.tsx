"use client";

import { useState, useRef, useEffect, useMemo, type ReactNode } from "react";
import {
  Compass,
  Maximize2,
  ExternalLink,
  Download,
  X,
  Layers,
  Sparkles,
  Network,
  Eye,
  EyeOff,
  Info,
  Filter,
  ChevronDown,
  ChevronUp,
  type LucideIcon,
} from "lucide-react";
import { BRAND } from "@/lib/brand";
import * as d3 from "d3";

// ============================================================
// SHARED — DataViz Card Frame (D24-D29 ortak kabugu)
// ============================================================

type ZoneId = "discovery" | "curation" | "gapatlas" | "authoring" | "defense";

const ZONE_CONFIG: Record<ZoneId, { label: string; color: string; bg: string; icon: LucideIcon }> = {
  discovery: { label: "Kesif", color: "#D97706", bg: "#FEF3C7", icon: Compass },
  curation: { label: "Suzme & Inceleme", color: "#D97706", bg: "#FEF3C7", icon: Layers },
  gapatlas: { label: "Literatur Boslugu", color: "#0E4F4A", bg: "#F0FDFA", icon: Layers },
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
          ? `0 4px 20px -4px ${z.color}20, 0 1px 2px rgba(0,0,0,0.04)`
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
          <button
            onClick={onFullscreen}
            title="Tam ekran"
            className="flex h-8 w-8 items-center justify-center rounded-lg text-stone-500 transition-colors hover:bg-stone-100 hover:text-stone-700"
          >
            <Maximize2 className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={onOpenNew}
            title="Yeni sekmede ac"
            className="flex h-8 w-8 items-center justify-center rounded-lg text-stone-500 transition-colors hover:bg-stone-100 hover:text-stone-700"
          >
            <ExternalLink className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={onExport}
            title="Disa aktar"
            className="flex h-8 w-8 items-center justify-center rounded-lg text-stone-500 transition-colors hover:bg-stone-100 hover:text-stone-700"
          >
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
// MOCK DATA — ARM Network (terms x methods co-occurrence)
// ============================================================

interface ClusterDef {
  id: number;
  name: string;
  color: string;
}

interface NetNode {
  id: string;
  label: string;
  type: "method" | "topic";
  cluster: number;
  freq: number;
}

interface SimNode extends NetNode {
  x: number;
  y: number;
  vx: number;
  vy: number;
  fx: number | null;
  fy: number | null;
}

interface NetLink {
  source: string;
  target: string;
  lift: number;
  confidence: number;
  npmi: number;
}

interface NetworkData {
  nodes: NetNode[];
  links: NetLink[];
  clusters: ClusterDef[];
}

function generateNetworkData(): NetworkData {
  const clusters: ClusterDef[] = [
    { id: 0, name: "Yontem ailesi", color: "#4F46E5" },
    { id: 1, name: "Egitim baglami", color: "#D97706" },
    { id: 2, name: "Kalite & degerlendirme", color: "#0E4F4A" },
    { id: 3, name: "Paydas & politika", color: "#7C3AED" },
  ];

  const nodes: NetNode[] = [
    { id: "AHP", label: "AHP", type: "method", cluster: 0, freq: 287 },
    { id: "TOPSIS", label: "TOPSIS", type: "method", cluster: 0, freq: 264 },
    { id: "VIKOR", label: "VIKOR", type: "method", cluster: 0, freq: 142 },
    { id: "PROMETHEE", label: "PROMETHEE", type: "method", cluster: 0, freq: 98 },
    { id: "ELECTRE", label: "ELECTRE", type: "method", cluster: 0, freq: 76 },
    { id: "ENTROPY", label: "ENTROPY", type: "method", cluster: 0, freq: 124 },
    { id: "Fuzzy_AHP", label: "Bulanik AHP", type: "method", cluster: 0, freq: 156 },
    { id: "DEMATEL", label: "DEMATEL", type: "method", cluster: 0, freq: 89 },
    { id: "higher_ed", label: "Yuksekogretim", type: "topic", cluster: 1, freq: 312 },
    { id: "K12", label: "K-12", type: "topic", cluster: 1, freq: 145 },
    { id: "vocational", label: "Mesleki egitim", type: "topic", cluster: 1, freq: 87 },
    { id: "online_ed", label: "Online egitim", type: "topic", cluster: 1, freq: 198 },
    { id: "curriculum", label: "Mufredat", type: "topic", cluster: 1, freq: 134 },
    { id: "STEM", label: "STEM", type: "topic", cluster: 1, freq: 167 },
    { id: "teacher_training", label: "Ogretmen egitimi", type: "topic", cluster: 1, freq: 102 },
    { id: "accreditation", label: "Akreditasyon", type: "topic", cluster: 2, freq: 234 },
    { id: "quality_assurance", label: "Kalite guvencesi", type: "topic", cluster: 2, freq: 189 },
    { id: "assessment", label: "Degerlendirme", type: "topic", cluster: 2, freq: 256 },
    { id: "ranking", label: "Siralama", type: "topic", cluster: 2, freq: 78 },
    { id: "benchmarking", label: "Kiyaslama", type: "topic", cluster: 2, freq: 92 },
    { id: "indicators", label: "Gostergeler", type: "topic", cluster: 2, freq: 145 },
    { id: "stakeholder", label: "Paydas analizi", type: "topic", cluster: 3, freq: 178 },
    { id: "policy", label: "Politika", type: "topic", cluster: 3, freq: 134 },
    { id: "governance", label: "Yonetisim", type: "topic", cluster: 3, freq: 89 },
    { id: "Turkey", label: "Turkiye", type: "topic", cluster: 3, freq: 156 },
    { id: "case_study", label: "Vaka calismasi", type: "topic", cluster: 3, freq: 198 },
  ];

  const links: NetLink[] = [
    { source: "AHP", target: "TOPSIS", lift: 4.2, confidence: 0.78, npmi: 0.62 },
    { source: "AHP", target: "Fuzzy_AHP", lift: 5.1, confidence: 0.82, npmi: 0.71 },
    { source: "TOPSIS", target: "VIKOR", lift: 3.4, confidence: 0.65, npmi: 0.54 },
    { source: "AHP", target: "DEMATEL", lift: 2.8, confidence: 0.58, npmi: 0.45 },
    { source: "TOPSIS", target: "ENTROPY", lift: 3.6, confidence: 0.71, npmi: 0.58 },
    { source: "VIKOR", target: "PROMETHEE", lift: 2.2, confidence: 0.48, npmi: 0.38 },
    { source: "ELECTRE", target: "PROMETHEE", lift: 2.9, confidence: 0.55, npmi: 0.46 },
    { source: "Fuzzy_AHP", target: "DEMATEL", lift: 2.4, confidence: 0.52, npmi: 0.41 },
    { source: "higher_ed", target: "curriculum", lift: 3.1, confidence: 0.68, npmi: 0.51 },
    { source: "higher_ed", target: "online_ed", lift: 2.7, confidence: 0.62, npmi: 0.44 },
    { source: "K12", target: "STEM", lift: 4.5, confidence: 0.79, npmi: 0.66 },
    { source: "STEM", target: "curriculum", lift: 3.2, confidence: 0.66, npmi: 0.52 },
    { source: "online_ed", target: "K12", lift: 2.4, confidence: 0.51, npmi: 0.39 },
    { source: "vocational", target: "curriculum", lift: 2.6, confidence: 0.54, npmi: 0.42 },
    { source: "teacher_training", target: "K12", lift: 3.8, confidence: 0.72, npmi: 0.58 },
    { source: "teacher_training", target: "STEM", lift: 2.3, confidence: 0.49, npmi: 0.37 },
    { source: "accreditation", target: "quality_assurance", lift: 5.4, confidence: 0.84, npmi: 0.74 },
    { source: "accreditation", target: "assessment", lift: 3.9, confidence: 0.72, npmi: 0.61 },
    { source: "quality_assurance", target: "indicators", lift: 4.1, confidence: 0.76, npmi: 0.64 },
    { source: "ranking", target: "benchmarking", lift: 4.7, confidence: 0.81, npmi: 0.69 },
    { source: "indicators", target: "assessment", lift: 3.3, confidence: 0.67, npmi: 0.53 },
    { source: "benchmarking", target: "indicators", lift: 2.9, confidence: 0.59, npmi: 0.47 },
    { source: "stakeholder", target: "policy", lift: 3.6, confidence: 0.69, npmi: 0.56 },
    { source: "policy", target: "governance", lift: 4.2, confidence: 0.78, npmi: 0.63 },
    { source: "Turkey", target: "case_study", lift: 3.1, confidence: 0.64, npmi: 0.49 },
    { source: "stakeholder", target: "governance", lift: 2.7, confidence: 0.56, npmi: 0.43 },
    { source: "AHP", target: "accreditation", lift: 3.8, confidence: 0.69, npmi: 0.57 },
    { source: "TOPSIS", target: "ranking", lift: 4.4, confidence: 0.76, npmi: 0.64 },
    { source: "AHP", target: "higher_ed", lift: 3.2, confidence: 0.65, npmi: 0.51 },
    { source: "TOPSIS", target: "quality_assurance", lift: 2.8, confidence: 0.58, npmi: 0.45 },
    { source: "Fuzzy_AHP", target: "assessment", lift: 3.5, confidence: 0.68, npmi: 0.55 },
    { source: "VIKOR", target: "indicators", lift: 2.6, confidence: 0.54, npmi: 0.42 },
    { source: "ENTROPY", target: "indicators", lift: 2.9, confidence: 0.59, npmi: 0.47 },
    { source: "AHP", target: "stakeholder", lift: 2.4, confidence: 0.51, npmi: 0.38 },
    { source: "Turkey", target: "higher_ed", lift: 3.7, confidence: 0.71, npmi: 0.58 },
    { source: "case_study", target: "accreditation", lift: 2.5, confidence: 0.53, npmi: 0.40 },
    { source: "DEMATEL", target: "stakeholder", lift: 2.2, confidence: 0.47, npmi: 0.36 },
    { source: "policy", target: "accreditation", lift: 3.1, confidence: 0.63, npmi: 0.50 },
    { source: "governance", target: "quality_assurance", lift: 2.8, confidence: 0.58, npmi: 0.45 },
  ];

  return { nodes, links, clusters };
}

// ============================================================
// NETWORK GRAPH (D25)
// ============================================================

type LabelMode = "all" | "large" | "none";
type TypeFilter = "all" | "method" | "topic";

function NetworkGraph({
  minLift,
  showLabels,
  typeFilter,
  hoveredId,
  setHoveredId,
  selected,
  setSelected,
  data,
}: {
  minLift: number;
  showLabels: LabelMode;
  typeFilter: TypeFilter;
  hoveredId: string | null;
  setHoveredId: (id: string | null) => void;
  selected: string | null;
  setSelected: (id: string | null) => void;
  data: NetworkData;
}) {
  const svgRef = useRef<SVGSVGElement>(null);
  const gRef = useRef<SVGGElement>(null);
  const [width, setWidth] = useState(800);
  const height = 560;

  const visibleNodes = useMemo(() => {
    if (typeFilter === "all") return data.nodes;
    return data.nodes.filter((n) => n.type === typeFilter);
  }, [data.nodes, typeFilter]);

  const visibleLinks = useMemo(() => {
    const visibleIds = new Set(visibleNodes.map((n) => n.id));
    return data.links.filter((l) => {
      const s = typeof l.source === "object" ? (l.source as SimNode).id : l.source;
      const t = typeof l.target === "object" ? (l.target as SimNode).id : l.target;
      return l.lift >= minLift && visibleIds.has(s) && visibleIds.has(t);
    });
  }, [data.links, minLift, visibleNodes]);

  // Resize observer
  useEffect(() => {
    if (!svgRef.current) return;
    const el = svgRef.current;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) setWidth(entry.contentRect.width);
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  // D3 simulation
  useEffect(() => {
    if (!svgRef.current || !gRef.current || width === 0) return;

    const svg = d3.select(svgRef.current);
    const g = d3.select(gRef.current);

    const nodes: SimNode[] = visibleNodes.map((d) => ({ ...d, x: 0, y: 0, vx: 0, vy: 0, fx: null, fy: null }));
    const links = visibleLinks.map((d) => ({ ...d }));

    const clusterCenters = data.clusters.reduce<Record<number, { x: number; y: number }>>((acc, c, i) => {
      const angle = (i / data.clusters.length) * 2 * Math.PI - Math.PI / 2;
      acc[c.id] = {
        x: width / 2 + Math.cos(angle) * Math.min(width, height) * 0.22,
        y: height / 2 + Math.sin(angle) * Math.min(width, height) * 0.22,
      };
      return acc;
    }, {});

    const sim = d3
      .forceSimulation(nodes)
      .force(
        "link",
        d3
          .forceLink(links)
          .id((d) => (d as SimNode).id)
          .distance((d) => 60 + (5 - (d as unknown as NetLink).lift) * 12)
          .strength((d) => (d as unknown as NetLink).lift / 8),
      )
      .force("charge", d3.forceManyBody().strength(-200))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force(
        "collision",
        d3.forceCollide<SimNode>().radius((d) => 6 + Math.sqrt(d.freq) * 0.7 + 4),
      )
      .force("cluster", (alpha: number) => {
        nodes.forEach((d) => {
          const c = clusterCenters[d.cluster];
          if (!c) return;
          d.vx += (c.x - d.x) * alpha * 0.3;
          d.vy += (c.y - d.y) * alpha * 0.3;
        });
      });

    g.selectAll("*").remove();

    const hullG = g.append("g").attr("class", "hulls").style("pointer-events", "none");

    const link = g
      .append("g")
      .attr("class", "edges")
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke", (d) => {
        const sNode = nodes.find((n) => n.id === (typeof d.source === "object" ? (d.source as SimNode).id : d.source));
        const tNode = nodes.find((n) => n.id === (typeof d.target === "object" ? (d.target as SimNode).id : d.target));
        if (sNode && tNode && sNode.cluster === tNode.cluster) {
          return data.clusters[sNode.cluster]?.color ?? "#A8A29E";
        }
        return "#A8A29E";
      })
      .attr("stroke-width", (d) => 0.6 + (d.lift / 5) * 2.4)
      .attr("stroke-opacity", (d) => 0.25 + d.confidence * 0.5);

    const node = g
      .append("g")
      .attr("class", "nodes")
      .selectAll<SVGGElement, SimNode>("g")
      .data(nodes)
      .join("g")
      .attr("class", "node-group")
      .style("cursor", "pointer")
      .call(
        d3
          .drag<SVGGElement, SimNode>()
          .on("start", (event, d) => {
            if (!event.active) sim.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on("drag", (event, d) => {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on("end", (event, d) => {
            if (!event.active) sim.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          }),
      );

    // Halo
    node
      .append("circle")
      .attr("class", "halo")
      .attr("r", (d) => 6 + Math.sqrt(d.freq) * 0.7 + 6)
      .attr("fill", (d) => data.clusters[d.cluster]?.color ?? "#A8A29E")
      .attr("opacity", 0);

    // Main circle
    node
      .append("circle")
      .attr("class", "main")
      .attr("r", (d) => 6 + Math.sqrt(d.freq) * 0.7)
      .attr("fill", (d) => data.clusters[d.cluster]?.color ?? "#A8A29E")
      .attr("fill-opacity", (d) => (d.type === "method" ? 1 : 0.85))
      .attr("stroke", "#FFFFFF")
      .attr("stroke-width", 2);

    // Method inner ring
    node
      .filter((d) => d.type === "method")
      .append("circle")
      .attr("r", (d) => 6 + Math.sqrt(d.freq) * 0.7 - 3)
      .attr("fill", "none")
      .attr("stroke", "#FFFFFF")
      .attr("stroke-width", 1)
      .attr("opacity", 0.6);

    // Labels
    node
      .append("text")
      .text((d) => d.label)
      .attr("text-anchor", "middle")
      .attr("dy", (d) => -(6 + Math.sqrt(d.freq) * 0.7 + 6))
      .attr("font-family", (d) => (d.type === "method" ? "JetBrains Mono, monospace" : "Inter, sans-serif"))
      .attr("font-size", (d) => 9 + Math.min(3, Math.sqrt(d.freq) / 8))
      .attr("font-weight", (d) => (d.type === "method" ? 600 : 500))
      .attr("fill", "#1C1917")
      .attr("pointer-events", "none")
      .style("user-select", "none")
      .style("opacity", (d) => {
        if (showLabels === "all") return 1;
        if (showLabels === "large") return d.freq > 130 ? 1 : 0;
        return 0;
      });

    node.on("mouseenter", (_event, d) => setHoveredId(d.id));
    node.on("mouseleave", () => setHoveredId(null));
    node.on("click", (_event, d) => setSelected(d.id === selected ? null : d.id));

    sim.on("tick", () => {
      link
        .attr("x1", (d) => (d.source as unknown as SimNode).x)
        .attr("y1", (d) => (d.source as unknown as SimNode).y)
        .attr("x2", (d) => (d.target as unknown as SimNode).x)
        .attr("y2", (d) => (d.target as unknown as SimNode).y);
      node.attr("transform", (d) => `translate(${d.x},${d.y})`);

      hullG.selectAll("path").remove();
      data.clusters.forEach((c) => {
        const clusterNodes = nodes.filter((n) => n.cluster === c.id);
        if (clusterNodes.length < 3) return;
        const points: [number, number][] = clusterNodes.map((n) => [n.x, n.y]);
        const hull = d3.polygonHull(points);
        if (hull) {
          const cx = d3.mean(hull, (p) => p[0]) ?? 0;
          const cy = d3.mean(hull, (p) => p[1]) ?? 0;
          const expanded = hull.map(([x, y]) => {
            const dx = x - cx;
            const dy = y - cy;
            const len = Math.sqrt(dx * dx + dy * dy) || 1;
            const pad = 28;
            return [x + (dx / len) * pad, y + (dy / len) * pad];
          });
          hullG
            .append("path")
            .attr("d", `M${expanded.join("L")}Z`)
            .attr("fill", c.color)
            .attr("fill-opacity", 0.06)
            .attr("stroke", c.color)
            .attr("stroke-opacity", 0.18)
            .attr("stroke-width", 1)
            .attr("stroke-dasharray", "3,4");
        }
      });
    });

    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.4, 3])
      .on("zoom", (event) => {
        g.attr("transform", event.transform.toString());
      });
    svg.call(zoom);

    return () => {
      sim.stop();
      svg.on(".zoom", null);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [width, height, visibleNodes, visibleLinks, showLabels, data.clusters]);

  // Highlight hovered/selected
  useEffect(() => {
    if (!gRef.current) return;
    const g = d3.select(gRef.current);
    const focusId = hoveredId ?? selected;

    if (focusId) {
      const connected = new Set([focusId]);
      data.links.forEach((l) => {
        const sId = typeof l.source === "object" ? (l.source as SimNode).id : l.source;
        const tId = typeof l.target === "object" ? (l.target as SimNode).id : l.target;
        if (l.lift < minLift) return;
        if (sId === focusId) connected.add(tId);
        if (tId === focusId) connected.add(sId);
      });

      g.selectAll<SVGGElement, SimNode>(".node-group").each(function (d) {
        const isFocus = d.id === focusId;
        const isConnected = connected.has(d.id);
        d3.select(this).select(".main").style("opacity", isConnected ? 1 : 0.2);
        d3.select(this).select(".halo").style("opacity", isFocus ? 0.35 : 0);
        d3.select(this).select("text").style("opacity", isConnected ? 1 : 0.15);
      });

      g.selectAll<SVGLineElement, NetLink>(".edges line").style("opacity", function (d) {
        const sId = typeof d.source === "object" ? (d.source as SimNode).id : d.source;
        const tId = typeof d.target === "object" ? (d.target as SimNode).id : d.target;
        return sId === focusId || tId === focusId ? 0.85 : 0.08;
      });
    } else {
      g.selectAll<SVGGElement, SimNode>(".node-group .main").style("opacity", 1);
      g.selectAll(".node-group .halo").style("opacity", 0);
      g.selectAll<SVGTextElement, SimNode>(".node-group text").style("opacity", (d) => {
        if (showLabels === "all") return 1;
        if (showLabels === "large") return d.freq > 130 ? 1 : 0;
        return 0;
      });
      g.selectAll(".edges line").style("opacity", null);
    }
  }, [hoveredId, selected, minLift, data.links, showLabels]);

  return (
    <svg ref={svgRef} width="100%" height={height} style={{ display: "block", background: "#FAFAF9" }}>
      <defs>
        <pattern id="netgrid" width="20" height="20" patternUnits="userSpaceOnUse">
          <circle cx="10" cy="10" r="0.6" fill="#E7E5E4" />
        </pattern>
      </defs>
      <rect width="100%" height={height} fill="url(#netgrid)" opacity="0.5" />
      <g ref={gRef} />
    </svg>
  );
}

// ============================================================
// HOVER TOOLTIP
// ============================================================

function NodeTooltip({ node, data, minLift }: { node: NetNode | null; data: NetworkData; minLift: number }) {
  if (!node) return null;
  const cluster = data.clusters[node.cluster];
  if (!cluster) return null;

  const connections = data.links
    .filter((l) => {
      const sId = typeof l.source === "object" ? (l.source as SimNode).id : l.source;
      const tId = typeof l.target === "object" ? (l.target as SimNode).id : l.target;
      return (sId === node.id || tId === node.id) && l.lift >= minLift;
    })
    .map((l) => {
      const sId = typeof l.source === "object" ? (l.source as SimNode).id : l.source;
      const tId = typeof l.target === "object" ? (l.target as SimNode).id : l.target;
      const otherId = sId === node.id ? tId : sId;
      return { other: data.nodes.find((n) => n.id === otherId), lift: l.lift, conf: l.confidence };
    })
    .filter((c) => c.other != null)
    .sort((a, b) => b.lift - a.lift)
    .slice(0, 3);

  return (
    <div
      className="pointer-events-none absolute right-4 top-4 z-10 max-w-[280px] rounded-xl border border-stone-200 bg-white p-4 shadow-lg"
      style={{ animation: "fadeIn 0.15s ease-out" }}
    >
      <div className="mb-2 flex flex-wrap items-center gap-1.5">
        <span
          className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-semibold"
          style={{ background: `${cluster.color}15`, color: cluster.color }}
        >
          <span className="h-1.5 w-1.5 rounded-full" style={{ background: cluster.color }} />
          {cluster.name}
        </span>
        <span
          className="rounded border px-1.5 py-0.5 text-[10px] font-medium"
          style={{
            background: node.type === "method" ? "#EEF2FF" : "#FFF7ED",
            color: node.type === "method" ? "#4F46E5" : "#D97706",
            borderColor: node.type === "method" ? "#E0E7FF" : "#FED7AA",
          }}
        >
          {node.type === "method" ? "Yontem" : "Konu"}
        </span>
      </div>
      <h4 className="font-display mb-1 text-base font-semibold italic leading-snug text-stone-900">{node.label}</h4>
      <div className="mb-3 text-xs text-stone-500">
        Siklik: <span className="font-mono font-semibold text-stone-700">{node.freq}</span>
      </div>
      {connections.length > 0 && (
        <div className="border-t border-stone-100 pt-2.5">
          <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-stone-400">
            En guclu 3 baglanti
          </div>
          <div className="space-y-1">
            {connections.map((c) => (
              <div key={c.other!.id} className="flex items-center justify-between gap-2 text-xs">
                <span className="truncate text-stone-700">{c.other!.label}</span>
                <span className="flex-shrink-0 font-mono text-[10px] text-stone-500">
                  lift <span className="font-semibold text-stone-700">{c.lift.toFixed(1)}</span>
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================
// SELECTED NODE PANEL
// ============================================================

function SelectedNodePanel({
  nodeId,
  data,
  minLift,
  onClose,
}: {
  nodeId: string;
  data: NetworkData;
  minLift: number;
  onClose: () => void;
}) {
  const node = data.nodes.find((n) => n.id === nodeId);
  if (!node) return null;
  const cluster = data.clusters[node.cluster];
  if (!cluster) return null;

  const connections = data.links
    .filter((l) => {
      const sId = typeof l.source === "object" ? (l.source as SimNode).id : l.source;
      const tId = typeof l.target === "object" ? (l.target as SimNode).id : l.target;
      return (sId === node.id || tId === node.id) && l.lift >= minLift;
    })
    .map((l) => {
      const sId = typeof l.source === "object" ? (l.source as SimNode).id : l.source;
      const tId = typeof l.target === "object" ? (l.target as SimNode).id : l.target;
      const otherId = sId === node.id ? tId : sId;
      const other = data.nodes.find((n) => n.id === otherId);
      return { other, lift: l.lift, conf: l.confidence, npmi: l.npmi };
    })
    .filter((c) => c.other != null)
    .sort((a, b) => b.lift - a.lift);

  return (
    <div
      className="mt-4 rounded-2xl border border-stone-200 bg-white p-5"
      style={{ animation: "slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1)", boxShadow: "0 4px 16px -4px rgba(0,0,0,0.08)" }}
    >
      <div className="mb-4 flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span
              className="rounded-md px-2 py-0.5 text-[10px] font-semibold"
              style={{ background: `${cluster.color}15`, color: cluster.color }}
            >
              {cluster.name}
            </span>
            <span
              className="rounded-md border px-2 py-0.5 text-[10px] font-medium"
              style={{
                background: node.type === "method" ? "#EEF2FF" : "#FFF7ED",
                color: node.type === "method" ? "#4F46E5" : "#D97706",
                borderColor: node.type === "method" ? "#E0E7FF" : "#FED7AA",
              }}
            >
              {node.type === "method" ? "Yontem" : "Konu"}
            </span>
            <span className="font-mono text-[10px] uppercase tracking-widest text-stone-400">Secili</span>
          </div>
          <h3 className="font-display mb-1 text-xl font-semibold italic leading-tight text-stone-900">{node.label}</h3>
          <div className="text-sm text-stone-600">
            Siklik: <span className="font-mono font-semibold">{node.freq}</span> ·
            <span className="ml-1.5">{connections.length} aktif baglanti</span>
          </div>
        </div>
        <button
          onClick={onClose}
          className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg text-stone-400 transition-colors hover:bg-stone-100 hover:text-stone-700"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {connections.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-stone-200 bg-stone-50">
          <div className="grid grid-cols-12 gap-2 border-b border-stone-200 bg-white px-4 py-2 text-[10px] font-semibold uppercase tracking-widest text-stone-500">
            <div className="col-span-6">Bagli terim</div>
            <div className="col-span-2 text-right">Lift</div>
            <div className="col-span-2 text-right">Confidence</div>
            <div className="col-span-2 text-right">NPMI</div>
          </div>
          <div className="max-h-[200px] overflow-y-auto">
            {connections.map((c) => (
              <div
                key={c.other!.id}
                className="grid grid-cols-12 items-center gap-2 border-b border-stone-100 px-4 py-2 text-sm transition-colors last:border-0 hover:bg-white"
              >
                <div className="col-span-6 flex min-w-0 items-center gap-2">
                  <span
                    className="h-1.5 w-1.5 flex-shrink-0 rounded-full"
                    style={{ background: data.clusters[c.other!.cluster]?.color ?? "#A8A29E" }}
                  />
                  <span className="truncate text-stone-800">{c.other!.label}</span>
                </div>
                <div className="col-span-2 text-right font-mono text-xs">
                  <span
                    className={`font-semibold ${c.lift >= 4 ? "text-emerald-700" : c.lift >= 2.5 ? "text-amber-700" : "text-stone-600"}`}
                  >
                    {c.lift.toFixed(2)}
                  </span>
                </div>
                <div className="col-span-2 text-right font-mono text-xs text-stone-600">{c.conf.toFixed(2)}</div>
                <div className="col-span-2 text-right font-mono text-xs text-stone-600">{c.npmi.toFixed(2)}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================
// MAIN — Network Map Card (D25)
// ============================================================

export function NetworkMapCard() {
  const [minLift, setMinLift] = useState(2.0);
  const [showLabels, setShowLabels] = useState<LabelMode>("large");
  const [typeFilter, setTypeFilter] = useState<TypeFilter>("all");
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [controlsOpen, setControlsOpen] = useState(true);

  const data = useMemo(() => generateNetworkData(), []);
  const hoveredNode = hoveredId ? data.nodes.find((n) => n.id === hoveredId) ?? null : null;

  const filteredLinkCount = data.links.filter((l) => l.lift >= minLift).length;

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-4 md:p-6">
      <style>{`
        @keyframes fadeIn { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes slideUp { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
        input[type="range"]::-webkit-slider-thumb {
          appearance: none;
          width: 14px; height: 14px;
          border-radius: 50%;
          background: #FFFFFF;
          border: 2px solid #4F46E5;
          cursor: pointer;
          box-shadow: 0 1px 3px rgba(0,0,0,0.15);
        }
        input[type="range"]::-moz-range-thumb {
          width: 14px; height: 14px;
          border-radius: 50%;
          background: #FFFFFF;
          border: 2px solid #4F46E5;
          cursor: pointer;
        }
      `}</style>

      <DataVizCardFrame
        zone="discovery"
        customIcon={Network}
        title="Terim ag haritasi — Birlikte gecis"
        subtitle="ARM (Association Rule Mining) ile cikarilmis yontem x konu iliskileri"
        sourceBadge="ARM N08 — lift & confidence"
        onFullscreen={() => {}}
        onExport={() => {}}
        onOpenNew={() => {}}
        legend={
          <>
            <div className="flex flex-wrap items-center gap-2">
              {data.clusters.map((c) => (
                <div key={c.id} className="flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-full" style={{ background: c.color }} />
                  <span className="text-xs text-stone-600">{c.name}</span>
                </div>
              ))}
            </div>
            <div className="ml-2 hidden items-center gap-1.5 lg:flex">
              <Info className="h-3 w-3 text-stone-400" />
              <span className="text-[11px] italic text-stone-500">Dugum boyutu = siklik · Kenar kalinligi = lift</span>
            </div>
          </>
        }
        controls={
          <span className="text-[11px] text-stone-500">
            <span className="font-mono font-semibold text-stone-700">{filteredLinkCount}</span> aktif baglanti
          </span>
        }
      >
        {/* Controls panel */}
        <div
          className="absolute left-4 top-4 z-10 rounded-xl border border-stone-200 bg-white/95 shadow-sm backdrop-blur-sm"
          style={{ minWidth: "240px" }}
        >
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
          {/* Lift slider */}
          <div>
            <div className="mb-1.5 flex items-center justify-between">
              <label className="flex items-center gap-1 text-[11px] font-semibold text-stone-700">
                <Filter className="h-3 w-3 text-stone-400" />
                Min. lift skoru
              </label>
              <span className="font-mono text-[11px] font-semibold text-indigo-600">{minLift.toFixed(1)}</span>
            </div>
            <input
              type="range"
              min="1.0"
              max="5.0"
              step="0.1"
              value={minLift}
              onChange={(e) => setMinLift(parseFloat(e.target.value))}
              className="h-1.5 w-full cursor-pointer appearance-none rounded-full bg-stone-200"
              style={{
                background: `linear-gradient(to right, #4F46E5 0%, #7C3AED ${((minLift - 1) / 4) * 100}%, #E7E5E4 ${((minLift - 1) / 4) * 100}%, #E7E5E4 100%)`,
              }}
            />
            <div className="mt-1 flex justify-between font-mono text-[9px] text-stone-400">
              <span>1.0</span>
              <span>2.5</span>
              <span>5.0</span>
            </div>
          </div>

          {/* Type filter */}
          <div>
            <label className="mb-1.5 block text-[11px] font-semibold text-stone-700">Terim tipi</label>
            <div className="flex gap-1">
              {(
                [
                  { id: "all", label: "Tumu" },
                  { id: "method", label: "Yontem" },
                  { id: "topic", label: "Konu" },
                ] as const
              ).map((t) => (
                <button
                  key={t.id}
                  onClick={() => setTypeFilter(t.id)}
                  className="flex-1 rounded-md border py-1 text-[10px] font-medium transition-all"
                  style={{
                    background: typeFilter === t.id ? "#EEF2FF" : "white",
                    color: typeFilter === t.id ? "#4F46E5" : "#57534E",
                    borderColor: typeFilter === t.id ? "#C7D2FE" : "#E7E5E4",
                  }}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          {/* Label toggle */}
          <div>
            <label className="mb-1.5 block text-[11px] font-semibold text-stone-700">Etiketler</label>
            <div className="flex gap-1">
              {(
                [
                  { id: "all", label: "Tumu", icon: Eye },
                  { id: "large", label: "Buyuk", icon: Eye },
                  { id: "none", label: "Yok", icon: EyeOff },
                ] as const
              ).map((t) => {
                const TIcon = t.icon;
                return (
                  <button
                    key={t.id}
                    onClick={() => setShowLabels(t.id)}
                    className="flex flex-1 items-center justify-center gap-1 rounded-md border py-1 text-[10px] font-medium transition-all"
                    style={{
                      background: showLabels === t.id ? "#EEF2FF" : "white",
                      color: showLabels === t.id ? "#4F46E5" : "#57534E",
                      borderColor: showLabels === t.id ? "#C7D2FE" : "#E7E5E4",
                    }}
                  >
                    <TIcon className="h-2.5 w-2.5" />
                    {t.label}
                  </button>
                );
              })}
            </div>
          </div>
        </div>}
        </div>

        {/* Hover tooltip */}
        <NodeTooltip node={hoveredNode} data={data} minLift={minLift} />

        {/* Graph */}
        <NetworkGraph
          minLift={minLift}
          showLabels={showLabels}
          typeFilter={typeFilter}
          hoveredId={hoveredId}
          setHoveredId={setHoveredId}
          selected={selectedId}
          setSelected={setSelectedId}
          data={data}
        />

        {/* Bottom hint */}
        <div className="absolute bottom-3 right-4 z-10 rounded-md bg-white/80 px-2 py-1 text-[11px] italic text-stone-400 backdrop-blur-sm">
          Dugume tiklayin — baglanti tablosu acilir · Surukleyip yerlestirebilirsiniz
        </div>
      </DataVizCardFrame>

      {/* Selected node detail panel */}
      {selectedId && <SelectedNodePanel nodeId={selectedId} data={data} minLift={minLift} onClose={() => setSelectedId(null)} />}

      {/* Differentiator note */}
      <div className="rounded-2xl border border-stone-200 bg-white p-5" style={{ borderLeft: "3px solid #4F46E5" }}>
        <div className="mb-2 text-xs font-semibold uppercase tracking-widest text-indigo-600">VOSViewer'dan farkimiz</div>
        <ul className="space-y-1.5 text-sm text-stone-700">
          <li className="flex items-start gap-2">
            <span className="mt-1 text-indigo-500">·</span>
            <span>
              <span className="font-medium">Web-yerel:</span> VOSViewer masaustu uygulamasidir, dosya import-export gerektirir; biz akisin icine yerlestik.
            </span>
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-1 text-indigo-500">·</span>
            <span>
              <span className="font-medium">Uc skor birden:</span> sadece co-occurrence sayisi degil — lift, confidence ve NPMI uclusu guclu/yaniltici baglari ayirir.
            </span>
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-1 text-indigo-500">·</span>
            <span>
              <span className="font-medium">Sicak akademik dil:</span> kutuphane fisi estetigi, Lora italic basliklar; soguk dashboard degil bir okuma odasi.
            </span>
          </li>
        </ul>
      </div>
    </div>
  );
}
