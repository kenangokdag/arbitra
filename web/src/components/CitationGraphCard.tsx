"use client";

import { useState, useRef, useEffect, useMemo, useCallback } from "react";
import { Info, Quote, X } from "lucide-react";
import * as d3 from "d3";
import { DataVizCardFrame } from "./DataVizCardFrame";

// ============================================================
// Types
// ============================================================
interface GraphNode extends d3.SimulationNodeDatum {
  id: string;
  title: string;
  authors: string;
  year: number;
  citations: number;
  isFocal?: boolean;
  type?: "cocite" | "bibcouple";
}

interface GraphLink extends d3.SimulationLinkDatum<GraphNode> {
  type: "cocite" | "bibcouple";
  strength: number;
}

interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

// ============================================================
// Mock data — Citation network
// ============================================================
function generateGraphData(): GraphData {
  const center: GraphNode = {
    id: "p0",
    title: "MCDM in Higher Education Accreditation: A Turkish Case Study",
    authors: "Yılmaz, A. et al.",
    year: 2024,
    citations: 47,
    isFocal: true,
  };

  const neighbors: GraphNode[] = [
    { id: "p1", title: "AHP-TOPSIS Hybrid Approach for University Quality", authors: "Demir, M. et al.", year: 2023, citations: 124, type: "cocite" },
    { id: "p2", title: "Stakeholder Perspectives on Accreditation Criteria", authors: "Aydın, F.", year: 2024, citations: 18, type: "cocite" },
    { id: "p3", title: "ENTROPY-VIKOR for Educational Quality Indicators", authors: "Öztürk, S. et al.", year: 2023, citations: 89, type: "cocite" },
    { id: "p4", title: "Fuzzy AHP in Quality Assessment Frameworks", authors: "Chen, L. et al.", year: 2022, citations: 156, type: "bibcouple" },
    { id: "p5", title: "Multi-Criteria Methods: A Systematic Review", authors: "Wang, Y.", year: 2021, citations: 312, type: "bibcouple" },
    { id: "p6", title: "PROMETHEE in Higher Education", authors: "García, C. et al.", year: 2023, citations: 42, type: "bibcouple" },
    { id: "p7", title: "Quality Assurance in Turkish Universities", authors: "Kara, B.", year: 2022, citations: 67, type: "cocite" },
    { id: "p8", title: "Stakeholder Theory in Academic Accreditation", authors: "Müller, K.", year: 2020, citations: 198, type: "cocite" },
    { id: "p9", title: "TOPSIS Applications: A Bibliometric Study", authors: "Patel, R. et al.", year: 2024, citations: 28, type: "bibcouple" },
    { id: "p10", title: "Decision Support Systems in Education Policy", authors: "Schmidt, A.", year: 2023, citations: 91, type: "cocite" },
    { id: "p11", title: "Educational Quality Indicators: Cross-Cultural", authors: "Rossi, G.", year: 2022, citations: 73, type: "bibcouple" },
    { id: "p12", title: "Hybrid MCDM in Public Sector Evaluation", authors: "Ahmad, F. et al.", year: 2023, citations: 54, type: "bibcouple" },
    { id: "p13", title: "AHP Applications: A Citation Network Analysis", authors: "Liu, Y.", year: 2021, citations: 287, type: "cocite" },
    { id: "p14", title: "Turkish Higher Education Reform: A Critical Review", authors: "Çelik, R.", year: 2024, citations: 19, type: "cocite" },
    { id: "p15", title: "Validity in Educational Assessment Models", authors: "Polat, H.", year: 2022, citations: 38, type: "bibcouple" },
    { id: "p16", title: "Quality Frameworks: A Comparative Study", authors: "Şahin, K.", year: 2023, citations: 45, type: "cocite" },
    { id: "p17", title: "Stakeholder Engagement in Quality Processes", authors: "Aksoy, S.", year: 2024, citations: 12, type: "cocite" },
    { id: "p18", title: "MCDM Applications: A Decade of Progress", authors: "Nakamura, K.", year: 2021, citations: 204, type: "bibcouple" },
  ];

  const edges: GraphLink[] = neighbors.map((n) => ({
    source: "p0",
    target: n.id,
    type: n.type!,
    strength: n.type === "cocite" ? 0.6 + Math.random() * 0.4 : 0.4 + Math.random() * 0.5,
  }));

  const crossEdges: GraphLink[] = [
    { source: "p1", target: "p3", type: "cocite", strength: 0.7 },
    { source: "p4", target: "p5", type: "bibcouple", strength: 0.8 },
    { source: "p1", target: "p4", type: "cocite", strength: 0.5 },
    { source: "p7", target: "p14", type: "cocite", strength: 0.6 },
    { source: "p2", target: "p8", type: "cocite", strength: 0.7 },
    { source: "p5", target: "p13", type: "bibcouple", strength: 0.65 },
    { source: "p9", target: "p18", type: "bibcouple", strength: 0.55 },
    { source: "p10", target: "p16", type: "cocite", strength: 0.5 },
    { source: "p3", target: "p11", type: "bibcouple", strength: 0.6 },
    { source: "p12", target: "p4", type: "bibcouple", strength: 0.7 },
  ];

  return {
    nodes: [center, ...neighbors],
    links: [...edges, ...crossEdges],
  };
}

// ============================================================
// Force-directed graph renderer
// ============================================================
function CitationGraph({
  filterType,
  onNodeClick,
  hoveredId,
  setHoveredId,
  setTransform,
}: {
  filterType: string;
  onNodeClick: (node: GraphNode) => void;
  hoveredId: string | null;
  setHoveredId: (id: string | null) => void;
  setTransform: (t: { k: number; x: number; y: number }) => void;
}) {
  const svgRef = useRef<SVGSVGElement>(null);
  const gRef = useRef<SVGGElement>(null);
  const [width, setWidth] = useState(800);
  const height = 540;
  const data = useMemo(() => generateGraphData(), []);

  const visibleLinks = useMemo(() => {
    if (filterType === "all") return data.links;
    return data.links.filter((l) => l.type === filterType);
  }, [data.links, filterType]);

  // Resize observer
  useEffect(() => {
    if (!svgRef.current) return;
    const el = svgRef.current;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setWidth(entry.contentRect.width);
      }
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  // D3 force simulation
  useEffect(() => {
    if (!svgRef.current || !gRef.current) return;

    const svg = d3.select(svgRef.current);
    const g = d3.select(gRef.current);

    const nodes: GraphNode[] = data.nodes.map((d) => ({ ...d }));
    const links: GraphLink[] = visibleLinks.map((d) => ({ ...d }));

    const sim = d3
      .forceSimulation(nodes)
      .force(
        "link",
        d3
          .forceLink<GraphNode, GraphLink>(links)
          .id((d) => d.id)
          .distance((d) => {
            const s = d.source as GraphNode;
            const t = d.target as GraphNode;
            return s.isFocal || t.isFocal ? 110 : 90;
          })
          .strength((d) => d.strength * 0.4),
      )
      .force(
        "charge",
        d3.forceManyBody<GraphNode>().strength((d) => (d.isFocal ? -800 : -240)),
      )
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force(
        "collision",
        d3
          .forceCollide<GraphNode>()
          .radius((d) => (d.isFocal ? 32 : 8 + Math.sqrt(d.citations) * 0.6)),
      );

    g.selectAll("*").remove();

    // Edges
    const link = g
      .append("g")
      .attr("class", "edges")
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke", (d) => (d.type === "cocite" ? "#D97706" : "#0E4F4A"))
      .attr("stroke-opacity", 0.45)
      .attr("stroke-width", (d) => 0.8 + d.strength * 2.5);

    // Nodes
    const node = g
      .append("g")
      .attr("class", "nodes")
      .selectAll<SVGGElement, GraphNode>("g")
      .data(nodes)
      .join("g")
      .attr("class", "node-group")
      .style("cursor", "pointer")
      .call(
        d3
          .drag<SVGGElement, GraphNode>()
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

    // Focal halo
    node
      .filter((d) => !!d.isFocal)
      .append("circle")
      .attr("r", 38)
      .attr("fill", "url(#focalGlow)")
      .attr("opacity", 0.6);

    // Node circles
    node
      .append("circle")
      .attr("r", (d) => (d.isFocal ? 22 : 5 + Math.sqrt(d.citations) * 0.7))
      .attr("fill", (d) => (d.isFocal ? "url(#focalGradient)" : "#FFFFFF"))
      .attr("stroke", (d) =>
        d.isFocal ? "#4F46E5" : d.type === "cocite" ? "#D97706" : "#0E4F4A",
      )
      .attr("stroke-width", (d) => (d.isFocal ? 2.5 : 1.8));

    // Labels
    node
      .append("text")
      .text((d) => {
        if (d.isFocal) return "FOKUS";
        const radius = 5 + Math.sqrt(d.citations) * 0.7;
        if (radius < 9) return "";
        const firstAuthor = (d.authors.split(",")[0] ?? "").split(".")[0] ?? "";
        return `${firstAuthor} ${d.year}`;
      })
      .attr("text-anchor", "middle")
      .attr("dy", (d) =>
        d.isFocal ? 4 : -(5 + Math.sqrt(d.citations) * 0.7 + 6),
      )
      .attr("font-family", (d) =>
        d.isFocal ? "var(--font-sans)" : "var(--font-geist-mono)",
      )
      .attr("font-size", (d) => (d.isFocal ? "10px" : "9px"))
      .attr("font-weight", (d) => (d.isFocal ? "700" : "500"))
      .attr("fill", (d) => (d.isFocal ? "#FFFFFF" : "#57534E"))
      .attr("pointer-events", "none")
      .style("user-select", "none");

    // Interactions
    node.on("mouseenter", (_event, d) => setHoveredId(d.id));
    node.on("mouseleave", () => setHoveredId(null));
    node.on("click", (_event, d) => onNodeClick(d));

    // Tick
    sim.on("tick", () => {
      link
        .attr("x1", (d) => (d.source as GraphNode).x ?? 0)
        .attr("y1", (d) => (d.source as GraphNode).y ?? 0)
        .attr("x2", (d) => (d.target as GraphNode).x ?? 0)
        .attr("y2", (d) => (d.target as GraphNode).y ?? 0);

      node.attr("transform", (d) => `translate(${d.x ?? 0},${d.y ?? 0})`);
    });

    // Zoom
    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.4, 3])
      .on("zoom", (event) => {
        g.attr("transform", event.transform.toString());
        setTransform({
          k: event.transform.k,
          x: event.transform.x,
          y: event.transform.y,
        });
      });
    svg.call(zoom);

    return () => {
      sim.stop();
    };
  }, [width, height, visibleLinks, data.nodes, onNodeClick, setHoveredId, setTransform]);

  // Highlight hovered node connections
  useEffect(() => {
    if (!gRef.current) return;
    const g = d3.select(gRef.current);

    if (hoveredId) {
      const connected = new Set([hoveredId]);
      data.links.forEach((l) => {
        const sId = typeof l.source === "object" ? (l.source as GraphNode).id : (l.source as string);
        const tId = typeof l.target === "object" ? (l.target as GraphNode).id : (l.target as string);
        if (sId === hoveredId) connected.add(tId);
        if (tId === hoveredId) connected.add(sId);
      });

      g.selectAll<SVGCircleElement, GraphNode>(
        ".node-group circle:not([fill='url(#focalGlow)'])",
      ).style("opacity", function () {
        const d = d3.select<SVGGElement, GraphNode>(
          this.parentNode as SVGGElement,
        ).datum();
        return connected.has(d.id) ? "1" : "0.25";
      });

      g.selectAll<SVGLineElement, GraphLink>(".edges line").style(
        "opacity",
        (d) => {
          const sId = typeof d.source === "object" ? (d.source as GraphNode).id : (d.source as string);
          const tId = typeof d.target === "object" ? (d.target as GraphNode).id : (d.target as string);
          return sId === hoveredId || tId === hoveredId ? "0.85" : "0.1";
        },
      );
    } else {
      g.selectAll(".node-group circle:not([fill='url(#focalGlow)'])").style(
        "opacity",
        "1",
      );
      g.selectAll(".edges line").style("opacity", "0.45");
    }
  }, [hoveredId, data.links]);

  return (
    <svg
      ref={svgRef}
      width="100%"
      height={height}
      style={{ display: "block", background: "#FAFAF9" }}
    >
      <defs>
        <radialGradient id="focalGlow">
          <stop offset="0%" stopColor="#7C3AED" stopOpacity={0.4} />
          <stop offset="100%" stopColor="#7C3AED" stopOpacity={0} />
        </radialGradient>
        <linearGradient id="focalGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#4F46E5" />
          <stop offset="100%" stopColor="#7C3AED" />
        </linearGradient>
        <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
          <circle cx="10" cy="10" r="0.6" fill="#E7E5E4" />
        </pattern>
      </defs>
      <rect width="100%" height={height} fill="url(#grid)" opacity={0.5} />
      <g ref={gRef} />
    </svg>
  );
}

// ============================================================
// Hover tooltip
// ============================================================
function NodeTooltip({ node }: { node: GraphNode | null }) {
  if (!node || node.isFocal) return null;

  return (
    <div className="absolute top-4 right-4 bg-white rounded-xl shadow-lg border border-stone-200 p-4 max-w-[280px] z-10 pointer-events-none animate-[fadeIn_0.15s_ease-out]">
      <div className="flex items-center gap-1.5 mb-2 flex-wrap">
        <span
          className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold"
          style={{
            background: node.type === "cocite" ? "#FEF3C7" : "#F0FDFA",
            color: node.type === "cocite" ? "#B45309" : "#0E4F4A",
          }}
        >
          <span
            className="w-1.5 h-1.5 rounded-full"
            style={{
              background: node.type === "cocite" ? "#D97706" : "#0E4F4A",
            }}
          />
          {node.type === "cocite" ? "Birlikte atıflanan" : "Bibliyografik bağlı"}
        </span>
      </div>
      <h4 className="font-crimson italic text-sm font-semibold text-stone-900 leading-snug mb-2">
        {node.title}
      </h4>
      <div className="text-xs text-stone-600 mb-2.5">
        {node.authors} · {node.year}
      </div>
      <div className="flex items-center gap-3 text-xs pt-2.5 border-t border-stone-100">
        <span className="inline-flex items-center gap-1 text-stone-700">
          <Quote className="w-3 h-3 text-stone-400" />
          <span className="font-mono-pmid font-semibold">{node.citations}</span>
          <span className="text-stone-500">atıf</span>
        </span>
      </div>
    </div>
  );
}

// ============================================================
// Selected node panel
// ============================================================
function SelectedNodePanel({
  node,
  onClose,
}: {
  node: GraphNode | null;
  onClose: () => void;
}) {
  if (!node || node.isFocal) return null;

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
              style={{
                background: node.type === "cocite" ? "#FEF3C7" : "#F0FDFA",
                color: node.type === "cocite" ? "#B45309" : "#0E4F4A",
              }}
            >
              {node.type === "cocite"
                ? "Birlikte atıflanan"
                : "Bibliyografik bağlı"}
            </span>
            <span className="text-[10px] font-mono-pmid text-stone-400 uppercase tracking-widest">
              Seçili
            </span>
          </div>
          <h3 className="font-crimson italic text-lg font-semibold text-stone-900 leading-tight mb-1.5">
            {node.title}
          </h3>
          <div className="text-sm text-stone-600 mb-3">
            {node.authors} · <span className="italic">{node.year}</span> ·{" "}
            <span className="font-mono-pmid">{node.citations} atıf</span>
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
              Bu makaleyi merkez yap
            </button>
            <button className="px-3 py-1.5 rounded-lg text-xs font-medium text-stone-700 border border-stone-200 hover:bg-stone-50 transition-colors">
              Listeme ekle
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
// Main export — D24 Citation Graph Card
// ============================================================
export default function CitationGraphCard() {
  const [filterType, setFilterType] = useState("all");
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [transform, setTransform] = useState({ k: 1, x: 0, y: 0 });
  const [maxNodes, setMaxNodes] = useState(50);

  const data = useMemo(() => generateGraphData(), []);
  const hoveredNode = hoveredId
    ? data.nodes.find((n) => n.id === hoveredId) ?? null
    : null;

  const handleNodeClick = useCallback((node: GraphNode) => {
    setSelected(node);
  }, []);

  const filterChips = [
    { id: "all", label: "Tümü", color: "#57534E", count: data.links.length },
    {
      id: "cocite",
      label: "Birlikte atıflanan",
      color: "#D97706",
      count: data.links.filter((l) => l.type === "cocite").length,
    },
    {
      id: "bibcouple",
      label: "Bibliyografik bağlı",
      color: "#0E4F4A",
      count: data.links.filter((l) => l.type === "bibcouple").length,
    },
  ];

  return (
    <>
      <DataVizCardFrame
        zone="curation"
        title="Atıf ağı — Bağlı çalışmalar"
        subtitle="Seçili makaleye birlikte atıflanan + bibliyografik bağlı komşular"
        sourceBadge="833M atıf kenarı"
        onFullscreen={() => {}}
        onExport={() => {}}
        onOpenNew={() => {}}
        legend={
          <>
            <div className="flex items-center gap-1.5">
              <span
                className="w-6 h-0.5 rounded"
                style={{ background: "#D97706" }}
              />
              <span className="text-xs text-stone-600">
                Birlikte atıflanan
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <span
                className="w-6 h-0.5 rounded"
                style={{ background: "#0E4F4A" }}
              />
              <span className="text-xs text-stone-600">
                Bibliyografik bağlı
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <span
                className="w-3 h-3 rounded-full"
                style={{
                  background: "linear-gradient(135deg, #4F46E5, #7C3AED)",
                }}
              />
              <span className="text-xs text-stone-600">Fokus makale</span>
            </div>
            <div className="hidden md:flex items-center gap-1.5">
              <Info className="w-3 h-3 text-stone-400" />
              <span className="text-[11px] text-stone-500 italic">
                Düğüm boyutu = atıf sayısı · Kenar kalınlığı = bağ gücü
              </span>
            </div>
          </>
        }
        controls={
          <div className="flex items-center gap-2">
            <span className="text-[11px] text-stone-500 hidden sm:inline">
              Yakınlık:
            </span>
            <span className="text-[11px] font-mono-pmid text-stone-700">
              ×{transform.k.toFixed(1)}
            </span>
          </div>
        }
      >
        {/* Filter chips */}
        <div className="absolute top-4 left-4 z-10 flex items-center gap-1.5 flex-wrap">
          {filterChips.map((chip) => (
            <button
              key={chip.id}
              onClick={() => setFilterType(chip.id)}
              className="px-3 py-1.5 rounded-full text-xs font-medium border transition-all flex items-center gap-1.5"
              style={{
                background:
                  filterType === chip.id ? `${chip.color}15` : "white",
                color: filterType === chip.id ? chip.color : "#57534E",
                borderColor:
                  filterType === chip.id ? `${chip.color}40` : "#E7E5E4",
                fontWeight: filterType === chip.id ? 600 : 500,
              }}
            >
              {filterType === chip.id && (
                <span
                  className="w-1.5 h-1.5 rounded-full"
                  style={{ background: chip.color }}
                />
              )}
              {chip.label}
              <span className="font-mono-pmid text-[10px] opacity-70">
                {chip.count}
              </span>
            </button>
          ))}
        </div>

        {/* Limit info */}
        <div className="absolute bottom-3 left-4 z-10 flex items-center gap-2 text-[11px] text-stone-500 bg-white/90 backdrop-blur-sm rounded-md px-2 py-1 border border-stone-200">
          <span>İlk {maxNodes} sonuç gösteriliyor</span>
          <button
            onClick={() => setMaxNodes((n) => n + 50)}
            className="text-indigo-600 font-medium hover:underline"
          >
            Daha fazla yükle
          </button>
        </div>

        {/* Hover tooltip */}
        <NodeTooltip node={hoveredNode} />

        {/* Graph */}
        <CitationGraph
          filterType={filterType}
          onNodeClick={handleNodeClick}
          hoveredId={hoveredId}
          setHoveredId={setHoveredId}
          setTransform={setTransform}
        />

        {/* Hint */}
        <div className="absolute bottom-3 right-4 z-10 text-[11px] text-stone-400 italic">
          Düğümleri sürükleyip yerleştirebilirsiniz · Mouse tekerleği ile
          yakınlaşın
        </div>
      </DataVizCardFrame>

      {/* Selected paper panel */}
      {selected && !selected.isFocal && (
        <SelectedNodePanel node={selected} onClose={() => setSelected(null)} />
      )}
    </>
  );
}
